<div align="center">

<img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Hiking%20boot/3D/hiking_boot_3d.png" width="96" alt="hiking boot"/>

# Hiking & Walking Finder
### AI-powered walk recommendations · Anywhere in the world · Zero cost

[![Python](https://img.shields.io/badge/Python-3.9+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-black?style=flat-square)](https://ollama.ai)
[![OpenStreetMap](https://img.shields.io/badge/OpenStreetMap-Overpass%20API-7ebc6f?style=flat-square&logo=openstreetmap&logoColor=white)](https://overpass-api.de)
[![Open-Meteo](https://img.shields.io/badge/Open--Meteo-weather-00aaff?style=flat-square)](https://open-meteo.com)

*Detects your location > checks today's weather > discovers every walkable green area nearby > recommends the best outing for the day.*

</div>

---

## ✨ What it does

Run one command. The agent handles everything:

| Step | What happens |
|------|-------------|
| 📍 **Locate** | Detects your city from your IP address - no GPS, no permissions |
| 🌤 **Weather** | Fetches a live forecast for your exact coordinates |
| 🤖 **Decide** | Asks the LLM *"is it a good day to go outside?"* - exits early if not |
| 🗺 **Discover** | Finds every walkable green area within 25 km via OpenStreetMap |
| 🥾 **Trails** | Fetches hiking routes for all areas in a single efficient request |
| 💬 **Recommend** | Returns top 2-3 picks with practical, local-guide-style reasons |
| 🔁 **Chat** | Answers follow-up questions with full conversation memory |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE OVERVIEW                               │
├─────────┬─────────┬──────────┬─────────┬─────────┬─────────┬──────────┤
│ STEP 1  │ STEP 2  │  STEP 3  │ STEP 4  │ STEP 5  │ STEP 6  │  STEP 7  │
│         │         │          │         │         │         │          │
│ Detect  │  Fetch  │  LLM ①   │  Query  │  Fetch  │  LLM ②  │  Chat    │
│Location │ Weather │ Go/No-Go │  Areas  │  Trails │  Picks  │  Loop    │
│ via IP  │  Open-  │  yes/no  │Overpass │  batch  │  + why  │  Q&A     │
│         │  Meteo  │          │   OSM   │  query  │         │          │
└─────────┴─────────┴──────────┴─────────┴─────────┴─────────┴──────────┘
                           │ if "no"
                           ▼
                     Agent exits early
                  (skips all API calls)
```

### Data sources - all free, no keys required

| Source | Provides | Cost |
|--------|----------|------|
| [geocoder](https://geocoder.readthedocs.io) | IP > lat/lon/city/country | Free · no key |
| [Open-Meteo](https://open-meteo.com) | Hourly weather forecast, global | Free · no key |
| [Overpass API](https://overpass-api.de) / OSM | Parks, reserves, forests, trails | Free · no key |
| [Ollama](https://ollama.ai) | Local LLM inference | Free · runs on your machine |

> **Total running cost: €0**

---

## 📁 Project structure

```
hiking-agent/
├── main_eu.py             # Entry point - run this
├── parks_eu.py            # Overpass queries, dedup, distance sorting, fallback
├── location_eu.py         # IP geolocation
├── weather.py             # Open-Meteo forecast + WMO weather code lookup
├── hiking_agent.ipynb     # Annotated walkthrough notebook with 11 live tests
└── README.md
```

---

## 🚀 Quick start

### 1 · Install Ollama

Ollama runs LLMs locally - no cloud account needed.

| Platform | Command / Installer |
|----------|-------------------|
| **macOS** | Download `.dmg` from [ollama.ai](https://ollama.ai) |
| **Linux** | `curl -fsSL https://ollama.com/install.sh \| sh` |
| **Windows** | Download `.exe` from [ollama.ai](https://ollama.ai) |

Verify the installation:

```bash
ollama --version
```

> Ollama starts as a background service automatically. If you ever need to start it manually: `ollama serve`

---

### 2 · Pull a model

```bash
ollama pull llama3
```

Choose based on your hardware:

| Model | Size | Notes |
|-------|------|-------|
| `phi3` | 2.3 GB | Best for low-spec laptops |
| `mistral` | 4.1 GB | Fast, good all-rounder |
| `llama3` | 4.7 GB | **Recommended starting point** |
| `llama3:70b` | 40 GB | Best quality - needs 48 GB+ RAM |

Check what you have installed:

```bash
ollama list
```

---

### 3 · Install Python dependencies

```bash
pip install geocoder requests ollama
```

> Requires **Python 3.9+**. Use a virtual environment if you prefer:
> `python -m venv venv && source venv/bin/activate` (Linux/macOS)
> or `venv\Scripts\activate` (Windows)

---

### 4 · Set your model

Open `main_eu.py` and update line 6:

```python
MODEL = "llama3"   # must match exactly what ollama list shows
```

---

### 5 · Run

```bash
python main_eu.py
```

**Example session:**

```
📍 Location detected: Prague, CZ (50.0880, 14.4208)
🌤 Today's forecast: Partly cloudy, average 13°C, max precip 0%.
✅ Weather approved - searching for nearby areas...

🌲 Found 6 nearest area(s):
     0.7 km  [Park]            Františkánská zahrada
     0.8 km  [Nature Reserve]  Letenský profil
     1.0 km  [Park]            Kampa
     1.1 km  [Park]            Vrchlického sady
     1.4 km  [Forest]          Divoká Šárka
     2.1 km  [Protected Area]  Prokopské údolí

--- Walking & Hiking Recommendations ---

1. Kampa (1.0 km) - A beautiful island park on the Vltava with riverside paths
   and views of Charles Bridge. Perfect 30-45 min stroll. Flat, paved, dog-friendly.

2. Divoká Šárka (1.4 km) - Prague's wildest green valley. Forested ravines,
   a natural swimming lake in summer. Allow 1-2 hours. Mostly easy terrain.

You > Which one is better for dogs?
Agent > Both are excellent for dogs, but Kampa edges it...
```

---

## ⚙️ Configuration

All settings live at the top of `main_eu.py` and `parks_eu.py`:

| Setting | Default | Effect |
|---------|---------|--------|
| `MODEL` | `llama3` | Ollama model name - must match `ollama list` |
| `MAX_PARKS` | `6` | Maximum number of areas returned |
| `SEARCH_RADIUS_KM` | `25` | How far to look for green areas (km) |
| `TRAIL_RADIUS_KM` | `10` | Trail search radius around each area centre (km) |
| `FALLBACK_RADIUS_KM` | `300` | Max distance for offline fallback parks (km) |
| `MAX_HISTORY` | `20` | Sliding window size for conversation memory |

---

## 🔍 How it works

### 📍 Location detection

`location_eu.py` resolves your public IP to a lat/lon coordinate using the `geocoder` library. Accuracy is typically 10-50 km - more than sufficient for a 25 km search radius. No GPS, no browser permissions, no personal data stored.

### 🌤 Weather

`weather.py` queries Open-Meteo for an hourly forecast at your exact coordinates and extracts the **08:00-17:00 daylight window**, summarising it into one sentence:

> *"Today's forecast: Partly cloudy, average 13°C, max precipitation probability 0%."*

This is passed verbatim to the LLM as the go/no-go input.

### 🗺 Area discovery

`parks_eu.py` queries the Overpass API with **deliberately broad OSM tags** - national parks, nature reserves, protected areas, named forests, regional parks, and local parks. Small and obscure local spots are included intentionally.

Results are then:
- **Sorted by real haversine distance** from your position
- **Deduplicated by proximity** - OSM sometimes tags the same physical place twice with slightly different names (e.g. `"Letenský profil"` and `"přírodní památka Letenský profil"`). Any two entries within 100 m of each other are collapsed into one, keeping the higher-priority type label and the shorter name

### 🛡 Resilience

| Layer | Mechanism |
|-------|-----------|
| **Mirror failover** | 3 public Overpass endpoints tried in sequence |
| **Retry logic** | Timeouts and 504s skip to the next mirror automatically |
| **Hardcoded fallback** | ~70 curated national parks across every continent, distance-filtered to your actual position |
| **Graceful degradation** | If trails fail, areas are still recommended; if weather fails, the agent exits cleanly with a message |

### 🥾 Trail fetching

Rather than one Overpass HTTP request per park (which caused cascading 429 rate-limit errors), all trails for all parks are fetched in **a single batched union query**. Each trail is then assigned to its nearest park centre.

### 🧠 Conversation memory

`main_eu.py` maintains memory at two levels:

- **Sliding window** - conversation history is trimmed to `MAX_HISTORY` messages so the LLM context window never overflows across long sessions
- **Pinned facts** - type `remember: I prefer flat walks` to pin a preference that survives history trimming and is injected into every subsequent prompt

---

## ⚠️ Limitations

| Area | Detail |
|------|--------|
| **IP geolocation** | City-level accuracy (~10-50 km). Rural users may get the nearest town as their position |
| **OSM coverage** | Western Europe and North America are very well mapped. Parts of Africa, Central Asia, and rural South America have sparser data |
| **Overpass availability** | Public mirrors are best-effort. The fallback list covers major parks on every continent but cannot replicate live OSM richness |
| **Trail difficulty** | Relies on the `sac_scale` OSM tag, which is not universally applied. `Unknown` difficulty means unrated in OSM, not dangerous |
| **Language** | Area and trail names are returned in the local OSM language (Czech, German, etc.) - the LLM handles translation in its response |

---

## 📄 License

Do whatever you like with it. Contributions welcome.

---

<div align="center">
<sub>Built with OpenStreetMap · Open-Meteo · Ollama · Python</sub>
</div>