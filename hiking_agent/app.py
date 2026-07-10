import os, time
import concurrent.futures
from datetime import datetime
import reverse_geocoder as rg
import streamlit as st
from groq import Groq
from streamlit_js_eval import get_geolocation
from location_eu import get_current_location
from weather import get_weather, get_todays_weather_summary
from parks_eu import get_parks, get_trails_for_parks

MODEL       = "llama-3.3-70b-versatile"
MAX_HISTORY = 20

st.set_page_config(
    page_title="Trail Finder",
    page_icon="🥾",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&family=DM+Mono:wght@400;500&display=swap');

:root {
  --bg:       #0f0f0f;
  --surface:  #161616;
  --border:   #242424;
  --muted:    #3a3a3a;
  --mid:      #6b6b6b;
  --text:     #e8e8e8;
  --white:    #f5f5f5;
  --green:    #4ade80;
  --green-d:  #16a34a;
  --green-bg: rgba(74,222,128,0.06);
  --mint-text: rgba(200,255,215,0.95);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, .stApp {
  background: var(--bg) !important;
  font-family: 'DM Sans', system-ui, sans-serif;
  color: var(--text);
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 680px !important; margin: 0 auto; }
section[data-testid="stSidebar"] { display: none; }

/* ── NAV ── */
.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28px 0 0;
  margin-bottom: 80px;
}
.nav-logo {
  font-family: 'DM Mono', monospace;
  font-size: 13px;
  color: var(--mint-text);
  letter-spacing: 0.5px;
}
.nav-links {
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  color: var(--mid);
  letter-spacing: 1px;
}

/* ── HERO ── */
.hero { padding: 0 0 72px; }

.hero-label {
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--mint-text);
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.hero-label::before {
  content: '';
  display: inline-block;
  width: 20px;
  height: 1px;
  background: var(--mint-text);
}

.hero-h1 {
  font-size: 42px;
  font-weight: 300;
  line-height: 1.1;
  color: var(--white);
  margin-bottom: 6px;
  letter-spacing: -1.5px;
}
.hero-h1 span {
  font-weight: 500;
  color: var(--white);
}

.hero-desc {
  font-size: 16px;
  font-weight: 300;
  line-height: 1.7;
  color: var(--mid);
  max-width: 440px;
  margin-bottom: 25px;
}

/* ── MAIN CTA BUTTON ── */
.stButton {
  display: flex !important;
  justify-content: center !important;
  width: 100% !important;
}
.stButton > button {
  background: linear-gradient(135deg, rgba(74,222,128,0.22) 0%, rgba(74,222,128,0.06) 100%) !important;
  color: rgba(200,255,215,0.95) !important;
  border: 1px solid rgba(150,255,180,0.3) !important;
  border-radius: 999px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 15px !important;
  font-weight: 500 !important;
  letter-spacing: 0.2px !important;
  padding: 16px 36px !important;
  backdrop-filter: blur(16px) !important;
  -webkit-backdrop-filter: blur(16px) !important;
  box-shadow:
    inset 0 1px 1px rgba(255,255,255,0.25),
    inset 0 -2px 4px rgba(0,0,0,0.15),
    0 8px 24px rgba(74,222,128,0.15),
    0 2px 8px rgba(0,0,0,0.3) !important;
  transition: all 0.25s ease !important;
  cursor: pointer !important;
  width: auto !important;
}
.stButton > button:hover {
  background: linear-gradient(135deg, rgba(74,222,128,0.3) 0%, rgba(74,222,128,0.1) 100%) !important;
  border-color: rgba(150,255,180,0.4) !important;
  box-shadow:
    inset 0 1px 1px rgba(255,255,255,0.3),
    inset 0 -2px 4px rgba(0,0,0,0.15),
    0 10px 32px rgba(74,222,128,0.2),
    0 4px 12px rgba(0,0,0,0.3) !important;
  transform: translateY(-1px) !important;
}

/* ── STEPS ROW ── */
.steps {
  display: flex;
  justify-content: space-between;
  margin-top: 28px;
  border-top: 1px solid var(--border);
  padding-top: 20px;
}
.step {
  flex: 1;
  text-align: center;
  padding: 0 4px;
}
.step-num {
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  color: var(--mint-text);
  margin-bottom: 8px;
}
.step-text {
  font-size: 13px;
  font-weight: 300;
  color: var(--mid);
  line-height: 1.5;
}

/* ── DIVIDER ── */
.divider {
  height: 1px;
  background: var(--border);
  margin: 40px 0;
}

/* ── STATUS BAR ── */
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 18px 22px;
  background: linear-gradient(135deg, rgba(74,222,128,0.05) 0%, rgba(74,222,128,0.01) 100%);
  border: 1px solid rgba(150,255,180,0.12);
  border-radius: 20px;
  backdrop-filter: blur(14px);
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.06);
  margin-bottom: 48px;
  gap: 8px;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}
.stat-label {
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--mid);
  white-space: nowrap;
}
.stat-value {
  font-size: 13px;
  font-weight: 400;
  color: var(--white);
  white-space: normal;
  word-break: break-word;
}
.stat-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: var(--green);
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

/* ── SECTION LABEL ── */
.sec-label {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--mid);
  margin-bottom: 16px;
}

/* ── PARK LIST ── */
.park-list { margin-bottom: 48px; }
.park-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
  gap: 12px;
}
.park-row:first-child { border-top: 1px solid var(--border); }
.park-name-col {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.park-num {
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  color: var(--muted);
  flex-shrink: 0;
  padding-top: 2px;
}
.park-name-block {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}
.park-name {
  font-size: 14px;
  font-weight: 400;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.park-type {
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  color: var(--mid);
  letter-spacing: 0.5px;
}
.park-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 5px;
  flex-shrink: 0;
}
.park-dist {
  font-family: 'DM Mono', monospace;
  font-size: 12px;
  color: var(--green);
  flex-shrink: 0;
  margin-left: 16px;
}

/* ── RECOMMENDATION ── */
.rec-block {
  background: linear-gradient(135deg, rgba(74,222,128,0.08) 0%, rgba(74,222,128,0.02) 100%);
  border: 1px solid rgba(150,255,180,0.15);
  border-radius: 20px;
  backdrop-filter: blur(14px);
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.06);
  padding: 28px 28px;
  margin-bottom: 48px;
  font-size: 16px;
  font-weight: 300;
  line-height: 1.8;
  color: var(--text);
}
.rec-block strong, .rec-block b {
  color: var(--white);
  font-weight: 500;
}

/* ── CHAT ── */
.chat-wrap { margin-bottom: 0; }
.chat-msg-user {
  text-align: right;
  margin: 16px 0;
}
.chat-msg-user > div {
  display: inline-block;
  background: linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.01) 100%);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 20px 20px 6px 20px;
  backdrop-filter: blur(12px);
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.06);
  padding: 12px 18px;
  font-size: 15px;
  color: var(--text);
  max-width: 85%;
  text-align: left;
}
.chat-msg-agent {
  margin: 16px 0;
}
.chat-msg-agent > div {
  display: inline-block;
  background: var(--green-bg);
  border: 1px solid rgba(74,222,128,0.12);
  border-radius: 16px 16px 16px 4px;
  padding: 12px 18px;
  font-size: 15px;
  color: var(--text);
  max-width: 85%;
  line-height: 1.65;
}
.reflect {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: var(--muted);
  margin: 4px 0 8px 2px;
  letter-spacing: 0.5px;
}

/* ── MEMORY PILLS ── */
.memory-wrap { margin: 12px 0 24px; display: flex; flex-wrap: wrap; gap: 6px; }
.mem-pill {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: rgba(200,255,215,0.85);
  background: linear-gradient(135deg, rgba(74,222,128,0.14) 0%, rgba(74,222,128,0.03) 100%);
  border: 1px solid rgba(150,255,180,0.2);
  border-radius: 999px;
  padding: 5px 14px;
  backdrop-filter: blur(10px);
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.12);
  letter-spacing: 0.3px;
}

/* ── CHAT HINT ── */
.chat-hint {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: var(--muted);
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

/* ── STREAMLIT CHAT INPUT ── */
.stChatInput textarea {
  background: linear-gradient(135deg, rgba(74,222,128,0.06) 0%, rgba(74,222,128,0.01) 100%) !important;
  border: 1px solid rgba(150,255,180,0.15) !important;
  border-radius: 20px !important;
  backdrop-filter: blur(12px) !important;
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 15px !important;
}
.stChatInput textarea:focus {
  border-color: rgba(150,255,180,0.35) !important;
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.08), 0 0 0 3px rgba(74,222,128,0.1) !important;
}
.stChatInput button {
  background: var(--green) !important;
  border-radius: 6px !important;
  color: #0a0a0a !important;
}

/* ── MAP BUTTON ── */
.map-btn {
  display: inline-flex;
  align-items: center;
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: rgba(200,255,215,0.7);
  background: linear-gradient(135deg, rgba(74,222,128,0.14) 0%, rgba(74,222,128,0.03) 100%);
  border: 1px solid rgba(150,255,180,0.2);
  border-radius: 999px;
  padding: 5px 14px;
  backdrop-filter: blur(10px);
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.15);
  text-decoration: none;
  transition: all 0.2s ease;
  white-space: nowrap;
  flex-shrink: 0;
}
.map-btn:hover {
  color: rgba(200,255,215,0.95);
  border-color: rgba(150,255,180,0.3);
  background: linear-gradient(135deg, rgba(74,222,128,0.2) 0%, rgba(74,222,128,0.06) 100%);
  text-decoration: none;
}

/* ── RESET LINK ── */
.reset-wrap {
  padding: 32px 0 64px;
  text-align: center;
}
.stButton.reset > button {
  background: transparent !important;
  border: 1px solid var(--border) !important;
  color: var(--mid) !important;
  font-size: 13px !important;
  padding: 10px 24px !important;
  border-radius: 6px !important;
}
.stButton.reset > button:hover {
  border-color: var(--muted) !important;
  color: var(--text) !important;
}

/* ── SPINNER ── */
.stSpinner > div { color: var(--green) !important; }

/* ── BAD WEATHER ── */
.weather-bad {
  padding: 32px 28px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin: 48px 0;
}
.weather-bad-title {
  font-size: 18px;
  font-weight: 500;
  color: var(--white);
  margin-bottom: 8px;
}
.weather-bad-desc {
  font-size: 15px;
  font-weight: 300;
  color: var(--mid);
  line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)


# ── Groq 
@st.cache_resource
def get_groq_client():
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        st.error("GROQ_API_KEY secret is missing. Add it in Space Settings > Secrets.")
        st.stop()
    return Groq(api_key=key)


# ── Memory 
def _trim_history(messages, n=MAX_HISTORY):
    sys  = [m for m in messages if m["role"] == "system"]
    chat = [m for m in messages if m["role"] != "system"]
    return sys + (chat[-n:] if len(chat) > n else chat)

def _memory_note(memory):
    if not memory: return ""
    return "\n\nUser preferences:\n" + "\n".join(f"- {m}" for m in memory)


# ── LLM ─
def query_model(system_prompt, user_prompt, messages=None, memory=None, retries=2):
    client = get_groq_client()
    if messages is None: messages = []
    full_sys = (system_prompt or "") + _memory_note(memory or [])
    messages.append({"role": "user", "content": user_prompt})
    if full_sys:
        if not any(m["role"] == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": full_sys})
        else:
            for m in messages:
                if m["role"] == "system": m["content"] = full_sys; break
    messages = _trim_history(messages)
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = client.chat.completions.create(
                model=MODEL, messages=messages, max_tokens=1024, temperature=0.7)
            content = r.choices[0].message.content.strip()
            messages.append({"role": "assistant", "content": content})
            return content, messages
        except Exception as e:
            last_err = e
            if attempt < retries: time.sleep(1.5 * (attempt + 1))
    fallback = "Having trouble responding right now - please try again."
    messages.append({"role": "assistant", "content": fallback})
    return fallback, messages

def is_final_answer(messages):
    try:
        client = get_groq_client()
        msgs = messages[:] + [{"role": "user",
            "content": "Did the last message fully answer the question? Reply only yes or no."}]
        r = client.chat.completions.create(model=MODEL, messages=msgs, max_tokens=5)
        return "yes" in r.choices[0].message.content.lower()
    except Exception:
        return False


# ── Individually cached, granular building blocks ──
# Each is cached on its own inputs so a cache-miss in one (e.g. browser_lang
# changing, which busts run_pipeline's cache) doesn't force refetching the rest.

@st.cache_data(show_spinner=False, ttl=3600)
def _cached_reverse_geocode(lat: float, lon: float):
    results = rg.search((lat, lon), verbose=False)
    return results[0].get("name", "Unknown"), results[0].get("cc", "")


@st.cache_data(show_spinner=False, ttl=600)
def _cached_weather_summary(lat: float, lon: float):
    wd = get_weather(lat, lon)
    return get_todays_weather_summary(wd)


@st.cache_data(show_spinner=False, ttl=600)
def _cached_parks(lat: float, lon: float, radius_km: int = 25):
    return get_parks(lat, lon, radius_km=radius_km)


@st.cache_data(show_spinner=False, ttl=600)
def _cached_trails(parks, radius_km: int = 10):
    return get_trails_for_parks(parks, radius_km=radius_km)


# ── Pipeline
# NOTE: browser_lang passed as argument - session_state not accessible
# inside @st.cache_data functions
@st.cache_data(show_spinner=False)
def run_pipeline(lat: float, lon: float, browser_lang: str = "en"):
    out = {"recommendations": "", "message_history": []}

    # 1-2-4. Reverse geocode, weather, and parks are all independent of each
    # other (each only needs lat/lon), so run them concurrently instead of
    # waiting on each network/lookup call in sequence.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        geo_future     = ex.submit(_cached_reverse_geocode, lat, lon)
        weather_future = ex.submit(_cached_weather_summary, lat, lon)
        parks_future   = ex.submit(_cached_parks, lat, lon, 25)

        try:
            city, country = geo_future.result()
        except Exception:
            city, country = "Your location", ""
        out.update(lat=lat, lon=lon, city=city, country=country)

        try:
            out["weather_summary"] = weather_future.result()
        except Exception as e:
            out["error"] = f"Weather error: {e}"
            return out

        try:
            parks = parks_future.result()
            if not parks:
                out["error"] = f"No green areas found near {city} within 25 km."
                return out
            out["parks"] = parks
        except Exception as e:
            out["error"] = str(e)
            return out

    # 3. Time of day
    hour = datetime.now().hour
    if hour < 12:   time_of_day = "morning"
    elif hour < 17: time_of_day = "afternoon"
    elif hour < 20: time_of_day = "evening"
    else:           time_of_day = "night"
    out["time_of_day"] = time_of_day

    # 5. Trails (depends on parks, so it has to run after that resolves)
    try:
        out["trails"] = _cached_trails(parks, 10)
    except Exception:
        out["trails"] = {p["name"]: [] for p in parks}

    # 6. Build prompt
    prompt_data = ""
    for p in parks:
        trails = out["trails"].get(p["name"], [])
        prompt_data += f"\n[{p['type']}] {p['name']} - {p['distance_km']} km\n"
        if trails:
            for t in trails:
                d = f"{t['distance_km']} km" if t["distance_km"] else "?"
                prompt_data += f"  • {t['name']} | {t['difficulty']} | {d}\n"
        else:
            prompt_data += "  • Walkable area, no marked trails in OSM.\n"
    out["prompt_data"] = prompt_data

    # 7. Generate recommendations
    try:
        weather_summary = out.get("weather_summary", "")
        recs, history = query_model(
            system_prompt=(
                f"You are a friendly local guide for {city}, {country}. "
                f"It is currently {time_of_day}. "
                f"Today's weather: {weather_summary} "
                "Never discourage a walk - some people love walking in any weather. "
                "Recommend the 2-3 best nearby walks from the list. "
                "Favour the closest. For each: what kind of walk, how long, why it's good. "
                f"IMPORTANT: Respond in the language with BCP-47 code '{browser_lang}'. "
                "If unsure of the language, respond in English. "
                "Be warm, specific, and concise."
            ),
            user_prompt=f"Green areas near {city}:\n{prompt_data}",
        )
        out["recommendations"] = recs
        out["message_history"] = history
    except Exception as e:
        out["error"] = str(e)

    return out



# SESSION STATE

for k, v in [("done", False), ("history", []), ("memory", []),
             ("chat", []), ("result", None), ("get_location", False),
             ("pipeline_running", False)]:
    if k not in st.session_state:
        st.session_state[k] = v



# LAYOUT WRAPPER

st.markdown('<div style="padding: 0 24px;">', unsafe_allow_html=True)

# Nav
st.markdown("""
<div class="nav">
  <div class="nav-logo">Trail finder</div>
  <div class="nav-links">Free | Open Source | Worldwide</div>
</div>
""", unsafe_allow_html=True)

# HERO

if not st.session_state.done:
    st.markdown("""
    <div class="hero">
      <div class="hero-label">AI-powered walk recommendations</div>
      <h1 class="hero-h1">Where should you walk <span>today?</span></h1>
      <p class="hero-desc">
        Discover the best places to enjoy near you.
      </p>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_b:
        go = st.button("Find walks near me", use_container_width=True)

    st.markdown("""
    <div class="steps">
      <div class="step">
        <div class="step-num">01</div>
        <div class="step-text">Allow<br>location</div>
      </div>
      <div class="step">
        <div class="step-num">02</div>
        <div class="step-text">Check today's<br>weather</div>
      </div>
      <div class="step">
        <div class="step-num">03</div>
        <div class="step-text">Find green areas<br>on OSM</div>
      </div>
      <div class="step">
        <div class="step-num">04</div>
        <div class="step-text">AI picks the<br>best options</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if go:
        st.session_state["get_location"] = True

    if st.session_state.get("get_location") and not st.session_state.get("pipeline_running"):
        loc = get_geolocation()
        if loc and "coords" in loc:
            # Immediately lock to prevent re-execution on next rerun
            st.session_state["get_location"]     = False
            st.session_state["pipeline_running"] = True
            lat = loc["coords"]["latitude"]
            lon = loc["coords"]["longitude"]
            browser_lang = st.session_state.get("browser_lang", "en")
            with st.spinner("Checking weather · Finding nearby walks…"):
                result = run_pipeline(lat, lon, browser_lang)
            st.session_state["pipeline_running"] = False
            st.session_state.result = result
            if "error" in result:
                st.error(result.get("error", "Something went wrong."))
            elif not result.get("recommendations"):
                st.warning("Could not generate recommendations — please try again.")
                for k in ["done","history","memory","chat","result","get_location","pipeline_running"]:
                    st.session_state.pop(k, None)
                run_pipeline.clear()
                st.rerun()
            else:
                st.session_state.done    = True
                st.session_state.history = result.get("message_history", [])
                st.session_state.chat.append(("assistant", result["recommendations"]))
                st.rerun()
        elif st.session_state.get("get_location"):
            st.info("Allow location access in the browser popup…")




# RESULTS
if st.session_state.get("done", False):
    r = st.session_state.result

    if not r or "error" in r:
        st.error(r.get("error", "Something went wrong - please try again.") if r else "No result.")
        if st.button("Try again", key="retry_error"):
            for k in ["done","history","memory","chat","result","get_location"]:
                st.session_state.pop(k, None)
            run_pipeline.clear()
            st.rerun()
        st.stop()

    if not r.get("recommendations"):
        st.warning("Could not generate recommendations - please try again.")
        if st.button("Try again", key="retry_norec"):
            for k in ["done","history","memory","chat","result","get_location"]:
                st.session_state.pop(k, None)
            run_pipeline.clear()
            st.rerun()
        st.stop()

    # ── Status bar
    st.markdown(f"""
    <div class="status-bar">
      <div class="stat">
        <div class="stat-label">Location</div>
        <div class="stat-value"><span class="stat-dot"></span>{r['city']}, {r['country']}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Coordinates</div>
        <div class="stat-value">{r['lat']:.3f}° {r['lon']:.3f}°</div>
      </div>
      <div class="stat">
        <div class="stat-label">Weather</div>
        <div class="stat-value">{r['weather_summary'].split(',')[0]}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Park list
    parks  = r.get("parks", [])
    trails = r.get("trails", {})

    rows = ""
    for i, p in enumerate(parks):
        t_count = len(trails.get(p["name"], []))
        t_str   = f"{t_count} trail{'s' if t_count!=1 else ''}" if t_count else "walkable"
        lat_p, lon_p = p.get("lat", 0), p.get("lon", 0)
        # Universal map link - opens Google Maps on Android/desktop, Apple Maps on iOS
        gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat_p},{lon_p}&travelmode=walking"
        rows += f"""
        <div class="park-row">
          <div class="park-name-col">
            <span class="park-num">0{i+1}</span>
            <div class="park-name-block">
              <span class="park-name">{p['name']}</span>
              <span class="park-type">{p['type']} · {t_str}</span>
            </div>
          </div>
          <div class="park-right">
            <span class="park-dist">{p['distance_km']} km</span>
            <a class="map-btn" href="{gmaps_url}" target="_blank">Route</a>
          </div>
        </div>"""

    st.markdown(f"""
    <div class="sec-label">Nearby areas found</div>
    <div class="park-list">{rows}</div>
    """, unsafe_allow_html=True)

    # ── Recommendation
    st.markdown(f"""
    <div class="sec-label">Today's recommendation</div>
    <div class="rec-block">{r['recommendations'].replace(chr(10), '<br>')}</div>
    """, unsafe_allow_html=True)

    # ── Chat
    st.markdown('<div class="sec-label">Ask a follow-up</div>', unsafe_allow_html=True)

    if st.session_state.memory:
        pills = "".join(f'<span class="mem-pill">📌 {m}</span>'
                        for m in st.session_state.memory)
        st.markdown(f'<div class="memory-wrap">{pills}</div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="chat-hint">type "remember: I prefer flat walks" to pin a preference</div>',
                unsafe_allow_html=True)

    # Chat history (skip index 0 - shown above as rec)
    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
    for i, (role, text) in enumerate(st.session_state.chat):
        if i == 0: continue
        cls = "chat-msg-user" if role == "user" else "chat-msg-agent"
        st.markdown(
            f'<div class="{cls}"><div>{text.replace(chr(10), "<br>")}</div></div>',
            unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Chat input
    user_input = st.chat_input("What would you like to know?")
    if user_input:
        s = user_input.strip()
        if s.lower().startswith("remember:"):
            fact = s[len("remember:"):].strip()
            if fact:
                st.session_state.memory.append(fact)
                st.session_state.chat.append(("assistant", f"📌 Noted: {fact}"))
            st.rerun()
        else:
            st.session_state.chat.append(("user", s))
            with st.spinner(""):
                try:
                    lang = st.session_state.get("browser_lang", "en")
                    resp, new_hist = query_model(
                        f"Always reply in the language with BCP-47 code '{lang}'.", s,
                        messages=st.session_state.history,
                        memory=st.session_state.memory,
                    )
                    st.session_state.history = new_hist
                    st.session_state.chat.append(("assistant", resp))
                except Exception as e:
                    st.session_state.chat.append(("assistant", f"Error: {e}"))
            st.rerun()

    # Reset
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Search again", use_container_width=True):
            for k in ["done","history","memory","chat","result","get_location"]:
                st.session_state.pop(k, None)
            run_pipeline.clear()
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)