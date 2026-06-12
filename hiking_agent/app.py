import os, time
import streamlit as st
from groq import Groq
from location_eu import get_current_location
from weather import get_weather, get_todays_weather_summary
from location_eu import get_current_location
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
  color: var(--green);
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
  color: var(--green);
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
  background: var(--green);
}

.hero-h1 {
  font-size: 42px;
  font-weight: 300;
  line-height: 1.1;
  color: var(--white);
  margin-bottom: 20px;
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
  margin-bottom: 40px;
}

/* ── MAIN CTA BUTTON ── */
.stButton > button {
  background: var(--green) !important;
  color: #0a0a0a !important;
  border: none !important;
  border-radius: 6px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 15px !important;
  font-weight: 500 !important;
  letter-spacing: 0.2px !important;
  padding: 14px 32px !important;
  transition: opacity 0.2s, transform 0.15s !important;
  cursor: pointer !important;
  width: auto !important;
}
.stButton > button:hover {
  opacity: 0.88 !important;
  transform: translateY(-1px) !important;
}

/* ── STEPS ROW ── */
.steps {
  display: flex;
  gap: 0;
  margin-top: 28px;
  border-top: 1px solid var(--border);
  padding-top: 20px;
}
.step {
  flex: 1;
  padding-right: 16px;
}
.step-num {
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  color: var(--green);
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
  gap: 32px;
  padding: 20px 24px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 48px;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-label {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--mid);
}
.stat-value {
  font-size: 14px;
  font-weight: 400;
  color: var(--white);
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
  align-items: baseline;
  justify-content: space-between;
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
}
.park-row:first-child { border-top: 1px solid var(--border); }
.park-name-col {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.park-num {
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  color: var(--muted);
  flex-shrink: 0;
}
.park-name {
  font-size: 15px;
  font-weight: 400;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.park-type {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: var(--mid);
  letter-spacing: 0.5px;
  margin-left: 6px;
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
  background: var(--green-bg);
  border: 1px solid rgba(74,222,128,0.15);
  border-radius: 8px;
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
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px 16px 4px 16px;
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
  color: var(--green);
  background: var(--green-bg);
  border: 1px solid rgba(74,222,128,0.2);
  border-radius: 20px;
  padding: 4px 12px;
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
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 15px !important;
}
.stChatInput textarea:focus {
  border-color: var(--green) !important;
  box-shadow: 0 0 0 3px rgba(74,222,128,0.1) !important;
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
  gap: 5px;
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--green);
  border: 1px solid rgba(74,222,128,0.3);
  border-radius: 4px;
  padding: 3px 10px;
  text-decoration: none;
  transition: background 0.15s, border-color 0.15s;
  white-space: nowrap;
  flex-shrink: 0;
}
.map-btn:hover {
  background: rgba(74,222,128,0.08);
  border-color: var(--green);
  color: var(--green);
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


# ── Groq ──────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_groq_client():
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        st.error("GROQ_API_KEY secret is missing. Add it in Space Settings → Secrets.")
        st.stop()
    return Groq(api_key=key)


# ── Memory ────────────────────────────────────────────────────────────────────
def _trim_history(messages, n=MAX_HISTORY):
    sys  = [m for m in messages if m["role"] == "system"]
    chat = [m for m in messages if m["role"] != "system"]
    return sys + (chat[-n:] if len(chat) > n else chat)

def _memory_note(memory):
    if not memory: return ""
    return "\n\nUser preferences:\n" + "\n".join(f"- {m}" for m in memory)


# ── LLM ───────────────────────────────────────────────────────────────────────
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


# ── Pipeline ──────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def run_pipeline(lat: float, lon: float):
    out = {}
    try:
        import reverse_geocoder as rg
        results = rg.search((lat, lon), verbose=False)
        city    = results[0].get("name", "Unknown")
        country = results[0].get("cc", "")
        out.update(lat=lat, lon=lon, city=city, country=country)
    except Exception:
        out.update(lat=lat, lon=lon, city="Your location", country="")

    try:
        wd = get_weather(lat, lon)
        if not wd: return {"error": "Weather API unavailable. Try again shortly."}
        out["weather_summary"] = get_todays_weather_summary(wd)
    except Exception as e:
        return {"error": str(e)}

    try:
        dec, _ = query_model(
            "Is the weather good for a walk or hike? Reply only yes or no.",
            out["weather_summary"])
        out["weather_ok"] = "no" not in dec.lower()
    except Exception:
        out["weather_ok"] = True

    if not out["weather_ok"]:
        out["recommendations"] = ""
        out["message_history"] = []
        return out

    try:
        parks = get_parks(lat, lon, radius_km=25)
        if not parks: return {**out, "error": f"No green areas found near {city} within 25 km."}
        out["parks"] = parks
    except Exception as e:
        return {**out, "error": str(e)}

    try:
        out["trails"] = get_trails_for_parks(parks, radius_km=10)
    except Exception:
        out["trails"] = {p["name"]: [] for p in parks}

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

    out["recommendations"] = ""
    out["message_history"] = []
    try:
        time_of_day = out.get("time_of_day", "day")
        weather_note = out.get("weather_note", out.get("weather_summary", ""))
        browser_lang = st.session_state.get("browser_lang", "en")
        recs, history = query_model(
            system_prompt=(
                f"You are a friendly local guide for {city}, {country}. "
                f"It is currently {time_of_day}. Weather today: {weather_note} "
                "Never discourage a walk based on weather — some people love walking in rain or wind. "
                "Recommend the 2-3 best nearby walks from the list. "
                "Favour the closest. For each: what kind of walk, how long, why it's good. "
                "If weather is challenging, briefly mention how it adds to the experience. "
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


# ════════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════════
for k, v in [("done", False), ("history", []), ("memory", []),
             ("chat", []), ("result", None), ("get_location", False)]:
    if k not in st.session_state:
        st.session_state[k] = v


# ════════════════════════════════════════════════════════════════════
# LAYOUT WRAPPER
# ════════════════════════════════════════════════════════════════════
st.markdown('<div style="padding: 0 24px;">', unsafe_allow_html=True)

# ── Nav ───────────────────────────────────────────────────────────
st.markdown("""
<div class="nav">
  <div class="nav-logo">trail·finder</div>
  <div class="nav-links">Free · Open Source · Worldwide</div>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════
# HERO
# ════════════════════════════════════════════════════════════════════
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

    from streamlit_js_eval import streamlit_js_eval, get_geolocation

    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        go = st.button("Find walks near me →", use_container_width=True)

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

    if st.session_state.get("get_location"):
        with st.spinner("📍 Waiting for location permission…"):
            loc = get_geolocation()
        if loc and "coords" in loc:
            lat = loc["coords"]["latitude"]
            lon = loc["coords"]["longitude"]
            st.session_state["get_location"] = False
            with st.spinner("Checking weather · Finding nearby walks…"):
                result = run_pipeline(lat, lon)
                st.session_state.result = result
            if "error" in result:
                st.error(result["error"])
            elif not result.get("recommendations"):
                st.warning("Could not generate recommendations — please try again.")
                for k in ["done","history","memory","chat","result","get_location"]:
                    st.session_state.pop(k, None)
                run_pipeline.clear()
                st.rerun()
            else:
                st.session_state.done    = True
                st.session_state.history = result.get("message_history", [])
                st.session_state.chat.append(("assistant", result["recommendations"]))
                st.rerun()
        else:
            st.info("Please allow location access in the browser popup and wait…")



# ════════════════════════════════════════════════════════════════════
# RESULTS
# ════════════════════════════════════════════════════════════════════
if st.session_state.get("done", False):
    r = st.session_state.result

    if not r or "error" in r:
        st.error(r.get("error", "Something went wrong — please try again.") if r else "No result.")
        if st.button("Try again", key="retry_error"):
            for k in ["done","history","memory","chat","result","get_location"]:
                st.session_state.pop(k, None)
            run_pipeline.clear()
            st.rerun()
        st.stop()

    if not r.get("recommendations"):
        st.warning("Could not generate recommendations — please try again.")
        if st.button("Try again", key="retry_norec"):
            for k in ["done","history","memory","chat","result","get_location"]:
                st.session_state.pop(k, None)
            run_pipeline.clear()
            st.rerun()
        st.stop()

    # ── Status bar ────────────────────────────────────────────────
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

    # ── Park list ─────────────────────────────────────────────────
    parks  = r.get("parks", [])
    trails = r.get("trails", {})

    rows = ""
    for i, p in enumerate(parks):
        t_count = len(trails.get(p["name"], []))
        t_str   = f"{t_count} trail{'s' if t_count!=1 else ''}" if t_count else "walkable"
        lat_p, lon_p = p.get("lat", 0), p.get("lon", 0)
        # Universal map link — opens Google Maps on Android/desktop, Apple Maps on iOS
        gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat_p},{lon_p}&travelmode=walking"
        rows += f"""
        <div class="park-row">
          <div class="park-name-col">
            <span class="park-num">0{i+1}</span>
            <span class="park-name">{p['name']}</span>
            <span class="park-type">{p['type']} · {t_str}</span>
          </div>
          <div style="display:flex;align-items:center;gap:12px;flex-shrink:0;">
            <span class="park-dist">{p['distance_km']} km</span>
            <a class="map-btn" href="{gmaps_url}" target="_blank">Take me there →</a>
          </div>
        </div>"""

    st.markdown(f"""
    <div class="sec-label">Nearby areas found</div>
    <div class="park-list">{rows}</div>
    """, unsafe_allow_html=True)

    # ── Recommendation ────────────────────────────────────────────
    st.markdown(f"""
    <div class="sec-label">Today's recommendation</div>
    <div class="rec-block">{r['recommendations'].replace(chr(10), '<br>')}</div>
    """, unsafe_allow_html=True)

    # ── Chat ──────────────────────────────────────────────────────
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
            for k in ["done", "history", "memory", "chat", "result"]:
                del st.session_state[k]
            run_pipeline.clear()
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)