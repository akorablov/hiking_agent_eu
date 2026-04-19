import ollama
import requests
from weather import get_weather, get_todays_weather_summary
from parks_eu import get_parks, get_trails_for_parks
from location_eu import get_current_location

MODEL = "gpt-oss:120b-cloud"

# Maximum number of messages kept in the sliding context window.
# Oldest messages (after the system prompt) are dropped when exceeded.
MAX_HISTORY = 20


# ── Exceptions ────────────────────────────────────────────────────────────────

class OllamaNotRunningError(RuntimeError):
    """Raised when the Ollama daemon is not reachable."""

class OllamaModelNotFoundError(RuntimeError):
    """Raised when the requested model has not been pulled."""

class LocationError(RuntimeError):
    """Raised when IP geolocation fails."""

class WeatherError(RuntimeError):
    """Raised when the weather API returns no usable data."""


# ── Ollama pre-flight check ───────────────────────────────────────────────────

def check_ollama() -> None:
    """
    Verify that:
      1. The Ollama daemon is running and reachable.
      2. The configured MODEL has been pulled locally.

    Raises OllamaNotRunningError or OllamaModelNotFoundError with a clear
    human-readable message on failure.
    """
    try:
        available = ollama.list() # raises ConnectionError if daemon is down
    except Exception:
        raise OllamaNotRunningError(
            "Ollama is not running.\n"
            "  • macOS / Windows : open the Ollama app\n"
            "  • Linux            : run  ollama serve  in a terminal\n"
            "Then restart this script."
        )

    model_names = [m.model for m in available.models]
    # Normalise: ollama list may return "llama3:latest" for a pull of "llama3"
    base_names = [n.split(":")[0] for n in model_names]
    target_base = MODEL.split(":")[0]

    if MODEL not in model_names and target_base not in base_names:
        available_str = "\n  ".join(model_names) if model_names else "(none)"
        raise OllamaModelNotFoundError(
            f"Model '{MODEL}' is not available locally.\n"
            f"Pull it with:\n"
            f"  ollama pull {MODEL}\n\n"
            f"Models currently available:\n  {available_str}"
        )


# ── Memory helpers ────────────────────────────────────────────────────────────

def _trim_history(messages: list, max_messages: int = MAX_HISTORY) -> list:
    """
    Keep the conversation history within max_messages entries.
    The system prompt (index 0) is always preserved; only the oldest
    user/assistant pairs are dropped from the middle.
    """
    system  = [m for m in messages if m["role"] == "system"]
    dialogue = [m for m in messages if m["role"] != "system"]
    if len(dialogue) > max_messages:
        dialogue = dialogue[-max_messages:]
    return system + dialogue


def _build_memory_note(memory: list[str]) -> str:
    """Format pinned memory items as a block to append to the system prompt."""
    if not memory:
        return ""
    lines = "\n".join(f"  - {item}" for item in memory)
    return f"\n\nUser preferences and pinned facts to remember:\n{lines}"


# ── LLM query ────────────────────────────────────────────────────────────────

def query_model(
    system_prompt: str,
    user_prompt: str,
    messages: list | None = None,
    memory: list[str] | None = None,
    retries: int = 2,
) -> tuple[str, list]:
    """
    Send a prompt to Ollama and return (response_text, updated_history).
    Error handling:
      - Retries up to `retries` times on transient connection errors.
      - Raises OllamaNotRunningError if the daemon goes away mid-session.
      - Raises OllamaModelNotFoundError if the model is missing.
      - Returns a safe fallback string on any other unexpected error so the follow-up loop can continue rather than crash.
    Memory:
      - Sliding window  : history trimmed to MAX_HISTORY messages.
      - Pinned memory   : short strings always injected into the system prompt.
    """
    if messages is None:
        messages = []

    full_system = (system_prompt or "") + _build_memory_note(memory or [])

    messages.append({"role": "user", "content": user_prompt})

    if full_system and not any(d.get("role") == "system" for d in messages):
        messages.insert(0, {"role": "system", "content": full_system})
    elif full_system:
        for m in messages:
            if m["role"] == "system":
                m["content"] = full_system
                break

    messages = _trim_history(messages)

    last_error = None
    for attempt in range(1, retries + 2):   # retries + 1 total attempts
        try:
            print("Asking model..." if attempt == 1 else f"Retrying (attempt {attempt})...")
            response = ollama.chat(model=MODEL, messages=messages)
            content  = response["message"]["content"].strip()
            messages.append({"role": "assistant", "content": content})
            return content, messages

        except ollama.ResponseError as e:
            # Model-level error (e.g. model not found)
            if "not found" in str(e).lower() or "pull" in str(e).lower():
                raise OllamaModelNotFoundError(
                    f"Model '{MODEL}' not found. Run:  ollama pull {MODEL}"
                ) from e
            last_error = e

        except (ConnectionError, ConnectionRefusedError, OSError) as e:
            raise OllamaNotRunningError(
                "Lost connection to Ollama mid-session.\n"
                "Check that the Ollama service is still running and try again."
            ) from e

        except Exception as e:
            last_error = e

    # All retries exhausted - return a graceful fallback so the loop survives
    print(f"⚠  Model call failed after {retries + 1} attempts: {last_error}")
    fallback = "I'm having trouble generating a response right now. Please try again."
    messages.append({"role": "assistant", "content": fallback})
    return fallback, messages


def is_final_answer(messages: list) -> bool:
    """
    Reflection call - ask whether the last response fully answers the question.
    Returns False silently on any error so the loop is never interrupted.
    """
    try:
        reflection_messages = messages[:] + [{
            "role": "system",
            "content": (
                "Has the last assistant response fully answered the user's question? "
                "Reply only 'yes' or 'no'."
            )
        }]
        response = ollama.chat(model=MODEL, messages=reflection_messages)
        return "yes" in response["message"]["content"].strip().lower()
    except Exception:
        return False          # fail silently - this is cosmetic, not critical


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main():
    memory: list[str] = []

    # ── Pre-flight: Ollama ────────────────────────────────────────────────────
    try:
        check_ollama()
    except (OllamaNotRunningError, OllamaModelNotFoundError) as e:
        print(f"\n❌ {e}\n")
        return

    # ── 1. Location ───────────────────────────────────────────────────────────
    print("Detecting your location...")
    try:
        latitude, longitude, city, country = get_current_location()
        if not latitude:
            raise LocationError("IP geolocation returned no result.")
    except LocationError as e:
        print(f"❌ Location error: {e}")
        print("   Check your internet connection and try again.")
        return
    except Exception as e:
        print(f"❌ Unexpected location error: {e}")
        return

    print(f"Location detected: {city}, {country} ({latitude:.4f}, {longitude:.4f})")

    # ── 2. Weather ────────────────────────────────────────────────────────────
    print("Checking the weather near you...")
    try:
        weather_data = get_weather(latitude, longitude)
        if not weather_data:
            raise WeatherError("Open-Meteo returned no data.")
        weather_summary = get_todays_weather_summary(weather_data)
    except WeatherError as e:
        print(f"❌ Weather error: {e}")
        print("   Check your internet connection and try again.")
        return
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not reach the weather API: {e}")
        return
    except Exception as e:
        print(f"❌ Unexpected weather error: {e}")
        return

    print(f"Weather summary: {weather_summary}")

    # ── 3. Weather gate (LLM ①) ───────────────────────────────────────────────
    try:
        weather_decision, _ = query_model(
            system_prompt=(
                "You are an assistant that determines if the weather is good for a "
                "walk or hike. Respond with only 'yes' or 'no'."
            ),
            user_prompt=(
                f"Based on this forecast, is it a good day to go outside? {weather_summary}"
            ),
        )
    except (OllamaNotRunningError, OllamaModelNotFoundError) as e:
        print(f"\n❌ {e}\n")
        return

    print(f"Model weather decision: {weather_decision}")
    if "no" in weather_decision.lower():
        print("\nThe model determined the weather is not suitable for going outside today.")
        return

    # ── 4. Discover nearby areas ──────────────────────────────────────────────
    print("\nWeather looks good! Searching for green areas and walking spots near you...")
    try:
        parks = get_parks(latitude, longitude, radius_km=25)
    except Exception as e:
        print(f"❌ Could not fetch nearby areas: {e}")
        print("   Overpass API may be temporarily unavailable. Try again in a few minutes.")
        return

    if not parks:
        print(f"No walking areas found near {city} within 25 km.")
        print("Try increasing radius_km in parks_eu.py or check your location detection.")
        return

    # ── 5. Fetch trails ───────────────────────────────────────────────────────
    try:
        trails_by_park = get_trails_for_parks(parks, radius_km=10)
    except Exception as e:
        print(f"⚠  Could not fetch trails ({e}) - continuing without trail detail.")
        trails_by_park = {p["name"]: [] for p in parks}

    # ── 6. Build prompt ───────────────────────────────────────────────────────
    prompt_data = ""
    for park in parks:
        trails = trails_by_park.get(park["name"], [])
        prompt_data += (
            f"\n[{park['type']}] {park['name']} - {park['distance_km']} km from you"
        )
        if park.get("website"):
            prompt_data += f" - {park['website']}"
        prompt_data += "\n"
        if trails:
            for trail in trails:
                dist = f"{trail['distance_km']} km" if trail["distance_km"] else "unknown length"
                prompt_data += (
                    f"  - {trail['name']} | {trail['difficulty']} | {dist} | "
                    f"surface: {trail['surface']}\n"
                )
        else:
            prompt_data += "  - No marked trails found, but the area is walkable.\n"

    # ── 7. Recommendations (LLM ②) ────────────────────────────────────────────
    try:
        recommendations, message_history = query_model(
            system_prompt=(
                f"You are a friendly local guide for {city}, {country}. "
                "The user wants to go for a walk or hike close to home today - nothing too far. "
                "From the list of nearby green areas and trails below, recommend the top 2-3 options. "
                "Favour the closest ones unless a slightly further option is clearly better. "
                "For each pick give a short, practical reason: what kind of walk it is, "
                "how long it takes, what makes it worth visiting. "
                "If distance to the area is known, mention it."
            ),
            user_prompt=f"Here are the walkable green areas near {city}:\n{prompt_data}",
            memory=memory,
        )
    except (OllamaNotRunningError, OllamaModelNotFoundError) as e:
        print(f"\n❌ {e}\n")
        return

    print("\n--- Walking & Hiking Recommendations ---")
    print(recommendations)

    # ── 8. Follow-up Q&A loop ─────────────────────────────────────────────────
    print("\nTip: type  remember: <fact>  to pin something for the rest of the session.")
    print("     type  memory            to see what's pinned.")
    print("     type  exit              to quit.\n")

    while True:
        try:
            follow_up = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Enjoy your walk!")
            break

        if not follow_up:
            continue

        if follow_up.lower() == "exit":
            print("👋 Enjoy your walk!")
            break

        # Show pinned memory
        if follow_up.lower() == "memory":
            if memory:
                print("\n📌 Pinned memory:")
                for item in memory:
                    print(f"   • {item}")
            else:
                print("\n📌 Nothing pinned yet. Use  remember: <fact>  to pin something.")
            print()
            continue

        # Pin a new fact
        if follow_up.lower().startswith("remember:"):
            fact = follow_up[len("remember:"):].strip()
            if fact:
                memory.append(fact)
                print(f"\n📌 Pinned: \"{fact}\"\n")
            else:
                print("\n⚠  Usage: remember: I prefer easy trails\n")
            continue

        # Normal follow-up
        try:
            response, message_history = query_model(
                system_prompt="",
                user_prompt=follow_up,
                messages=message_history,
                memory=memory,
            )
            print(f"\nAgent: {response}\n")

            if is_final_answer(message_history):
                print("💭 [Agent reflects: answered completely]\n")
            else:
                print("💭 [Agent reflects: may need more context]\n")

        except OllamaNotRunningError as e:
            print(f"\n❌ {e}\n")
            break   # no point continuing if Ollama went away

        except OllamaModelNotFoundError as e:
            print(f"\n❌ {e}\n")
            break


if __name__ == "__main__":
    main()
