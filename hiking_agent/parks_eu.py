import requests
import time
import math

OVERPASS_ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

MAX_PARKS = 6
FALLBACK_MAX_DISTANCE_KM = 300

# Global fallback - only used if ALL Overpass mirrors fail simultaneously.
# Covers major national parks on every continent, filtered by FALLBACK_MAX_DISTANCE_KM
# from the user's actual position, so only nearby ones are ever shown.
FALLBACK_PARKS = [
    # Czech Republic & immediate neighbours
    {"name": "Bohemian Switzerland NP",      "lat": 50.8833, "lon": 14.2333},
    {"name": "Krkonoše NP",                  "lat": 50.7333, "lon": 15.5833},
    {"name": "Šumava NP",                    "lat": 49.0333, "lon": 13.5000},
    {"name": "Podyjí NP",                    "lat": 48.8500, "lon": 15.8833},
    {"name": "Saxon Switzerland NP",         "lat": 50.9167, "lon": 14.1333},
    {"name": "Bavarian Forest NP",           "lat": 49.0333, "lon": 13.4333},
    {"name": "Tatra NP",                     "lat": 49.1667, "lon": 20.1167},
    {"name": "Slovak Paradise NP",           "lat": 48.9333, "lon": 20.4000},
    # Central & Western Europe
    {"name": "Berchtesgaden NP",             "lat": 47.6000, "lon": 12.9333},
    {"name": "Harz NP",                      "lat": 51.7167, "lon": 10.6167},
    {"name": "Black Forest NP",              "lat": 48.5667, "lon":  8.2000},
    {"name": "Hohe Tauern NP",               "lat": 47.1000, "lon": 12.7500},
    {"name": "Swiss NP",                     "lat": 46.6667, "lon": 10.1833},
    {"name": "Triglav NP",                   "lat": 46.3667, "lon": 13.8333},
    {"name": "Gran Paradiso NP",             "lat": 45.5167, "lon":  7.2167},
    {"name": "Vanoise NP",                   "lat": 45.3833, "lon":  6.9167},
    {"name": "Écrins NP",                    "lat": 44.9167, "lon":  6.3167},
    {"name": "Cévennes NP",                  "lat": 44.2333, "lon":  3.6833},
    {"name": "Pyrenees NP",                  "lat": 42.8333, "lon": -0.1167},
    # Iberia
    {"name": "Picos de Europa NP",           "lat": 43.1833, "lon": -4.8333},
    {"name": "Ordesa NP",                    "lat": 42.6500, "lon": -0.0333},
    {"name": "Sierra Nevada NP",             "lat": 37.0833, "lon": -3.3333},
    {"name": "Peneda-Gerês NP",              "lat": 41.7833, "lon": -8.1500},
    # UK & Ireland
    {"name": "Cairngorms NP",                "lat": 57.1000, "lon": -3.5833},
    {"name": "Loch Lomond NP",               "lat": 56.2333, "lon": -4.6167},
    {"name": "Lake District NP",             "lat": 54.4500, "lon": -3.0833},
    {"name": "Snowdonia NP",                 "lat": 53.0667, "lon": -3.9000},
    {"name": "Peak District NP",             "lat": 53.3667, "lon": -1.8000},
    # Scandinavia
    {"name": "Jotunheimen NP",               "lat": 61.6000, "lon":  8.5000},
    {"name": "Hardangervidda NP",            "lat": 60.1167, "lon":  7.5000},
    {"name": "Sarek NP",                     "lat": 67.1500, "lon": 17.7167},
    {"name": "Urho Kekkonen NP",             "lat": 68.3000, "lon": 27.5000},
    # Eastern Europe & Balkans
    {"name": "Białowieża NP",                "lat": 52.7000, "lon": 23.8667},
    {"name": "Bieszczady NP",                "lat": 49.1000, "lon": 22.5500},
    {"name": "Plitvice Lakes NP",            "lat": 44.8667, "lon": 15.6167},
    {"name": "Durmitor NP",                  "lat": 43.1333, "lon": 19.0167},
    {"name": "Rila NP",                      "lat": 42.2000, "lon": 23.5833},
    {"name": "Olympus NP",                   "lat": 40.0833, "lon": 22.3500},
    {"name": "Retezat NP",                   "lat": 45.3667, "lon": 22.9000},
    {"name": "Piatra Craiului NP",           "lat": 45.5000, "lon": 25.2167},
    # North America
    {"name": "Yellowstone NP",               "lat": 44.4280, "lon":-110.5885},
    {"name": "Grand Canyon NP",              "lat": 36.1069, "lon":-112.1129},
    {"name": "Yosemite NP",                  "lat": 37.8651, "lon":-119.5383},
    {"name": "Banff NP",                     "lat": 51.4968, "lon":-115.9281},
    {"name": "Olympic NP",                   "lat": 47.8021, "lon":-123.6044},
    {"name": "Acadia NP",                    "lat": 44.3386, "lon": -68.2733},
    {"name": "Great Smoky Mountains NP",     "lat": 35.6118, "lon": -83.4895},
    {"name": "Rocky Mountain NP",            "lat": 40.3428, "lon":-105.6836},
    {"name": "Zion NP",                      "lat": 37.2982, "lon":-113.0263},
    {"name": "Jasper NP",                    "lat": 52.8734, "lon":-117.9543},
    # Latin America
    {"name": "Torres del Paine NP",          "lat":-50.9423, "lon": -73.4068},
    {"name": "Iguazú NP",                    "lat":-25.6953, "lon": -54.4367},
    {"name": "Galápagos NP",                 "lat": -0.6500, "lon": -90.3500},
    {"name": "Tijuca NP",                    "lat":-22.9519, "lon": -43.2105},
    {"name": "Manuel Antonio NP",            "lat":  9.3922, "lon": -84.1378},
    # Africa
    {"name": "Serengeti NP",                 "lat": -2.3333, "lon":  34.8333},
    {"name": "Kruger NP",                    "lat":-23.9884, "lon":  31.5547},
    {"name": "Table Mountain NP",            "lat":-34.0000, "lon":  18.4167},
    {"name": "Bwindi Impenetrable NP",       "lat": -1.0333, "lon":  29.6500},
    {"name": "Kilimanjaro NP",               "lat": -3.0674, "lon":  37.3556},
    {"name": "Toubkal NP",                   "lat": 31.0600, "lon":  -7.9150},
    # Middle East
    {"name": "Dana Biosphere Reserve",       "lat": 30.6833, "lon":  35.6000},
    {"name": "Wadi Rum Protected Area",      "lat": 29.5833, "lon":  35.4167},
    # South & Southeast Asia
    {"name": "Jim Corbett NP",               "lat": 29.5300, "lon":  78.7700},
    {"name": "Ranthambore NP",               "lat": 26.0173, "lon":  76.5026},
    {"name": "Royal Chitwan NP",             "lat": 27.5000, "lon":  84.3333},
    {"name": "Khao Yai NP",                  "lat": 14.4386, "lon": 101.3697},
    {"name": "Gunung Gede Pangrango NP",     "lat": -6.7833, "lon": 107.0000},
    # East Asia
    {"name": "Zhangjiajie NP",               "lat": 29.3167, "lon": 110.4333},
    {"name": "Jiuzhaigou NP",                "lat": 33.2600, "lon": 103.9200},
    {"name": "Fuji-Hakone-Izu NP",           "lat": 35.3606, "lon": 138.7274},
    {"name": "Seoraksan NP",                 "lat": 38.1194, "lon": 128.4658},
    {"name": "Taroko NP",                    "lat": 24.1500, "lon": 121.6167},
    # Oceania
    {"name": "Blue Mountains NP",            "lat":-33.7167, "lon": 150.3167},
    {"name": "Fiordland NP",                 "lat":-45.4167, "lon": 167.7167},
    {"name": "Tongariro NP",                 "lat":-39.2000, "lon": 175.5667},
    {"name": "Cradle Mountain NP",           "lat":-41.6500, "lon": 145.9500},
]


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _post_overpass(query, timeout=45):
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            r = requests.post(endpoint, data={"data": query}, timeout=timeout)
            if r.status_code == 504:
                print(f"  504 from {endpoint.split('/')[2]}, trying next...")
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            print(f"  Timeout from {endpoint.split('/')[2]}, trying next...")
        except requests.exceptions.RequestException as e:
            print(f"  Error from {endpoint.split('/')[2]}: {e}")
    return None


def get_parks(latitude, longitude, radius_km=25):
    """
    Fetches ALL types of green/protected areas near the user - national parks,
    nature reserves, protected landscapes, forests, regional parks - anything
    OSM tags as a meaningful natural area. Small and unknown local areas are
    included intentionally.

    Uses a tight default radius (25 km) so results are genuinely nearby.
    Sorted by distance; returns the MAX_PARKS closest.

    Falls back to the Europe-wide hardcoded list (filtered by distance) only
    if every Overpass mirror fails.
    """
    radius_m = radius_km * 1000

    # Broad query: nodes + ways + relations, all meaningful natural/protected tags.
    # No protect_class filter - we want small unknown local areas too.
    query = f"""
    [out:json][timeout:40];
    (
      node["boundary"="national_park"](around:{radius_m},{latitude},{longitude});
      way["boundary"="national_park"](around:{radius_m},{latitude},{longitude});
      relation["boundary"="national_park"](around:{radius_m},{latitude},{longitude});

      node["leisure"="nature_reserve"](around:{radius_m},{latitude},{longitude});
      way["leisure"="nature_reserve"](around:{radius_m},{latitude},{longitude});
      relation["leisure"="nature_reserve"](around:{radius_m},{latitude},{longitude});

      node["boundary"="protected_area"](around:{radius_m},{latitude},{longitude});
      way["boundary"="protected_area"](around:{radius_m},{latitude},{longitude});
      relation["boundary"="protected_area"](around:{radius_m},{latitude},{longitude});

      node["landuse"="forest"]["name"](around:{radius_m},{latitude},{longitude});
      way["landuse"="forest"]["name"](around:{radius_m},{latitude},{longitude});
      relation["landuse"="forest"]["name"](around:{radius_m},{latitude},{longitude});

      relation["boundary"="regional_park"](around:{radius_m},{latitude},{longitude});
      relation["leisure"="park"]["name"](around:{radius_m},{latitude},{longitude});
    );
    out center tags;
    """

    data = _post_overpass(query, timeout=45)

    if data:
        parks = _parse_areas(data, latitude, longitude)
    else:
        parks = []

    if len(parks) < 3:
        print(f"  Live query returned {len(parks)} area(s) - filling from fallback...")
        live_names = {p["name"] for p in parks}
        for fp in FALLBACK_PARKS:
            dist = _haversine_km(latitude, longitude, fp["lat"], fp["lon"])
            if fp["name"] not in live_names and dist <= FALLBACK_MAX_DISTANCE_KM:
                parks.append({
                    "name": fp["name"], "type": "National Park",
                    "lat": fp["lat"],   "lon": fp["lon"],
                    "website": "",      "distance_km": round(dist, 1),
                })

    parks.sort(key=lambda p: p["distance_km"])
    result = parks[:MAX_PARKS]

    if result:
        print(f"Found {len(result)} nearest area(s):")
        for p in result:
            print(f"  {p['distance_km']:>6.1f} km  [{p['type']}]  {p['name']}")
    else:
        print(f"No areas found within {radius_km} km. Try increasing radius_km.")

    return result


def _parse_areas(data, user_lat, user_lon):
    """
    Parse raw Overpass elements into a flat list of area dicts.
    Deduplicates by:
      1. Exact name match
      2. Proximity - if two entries are within 100 m of each other, keep the
         one with the higher-priority type so e.g. Czech "prirodni pamatka X"
         and plain "X" collapse into one entry.
    """
    TYPE_MAP = {
        "national_park":  "National Park",
        "protected_area": "Protected Area",
        "regional_park":  "Regional Park",
    }
    TYPE_PRIORITY = {
        "National Park":  5,
        "Nature Reserve": 4,
        "Regional Park":  3,
        "Forest":         2,
        "Park":           1,
        "Protected Area": 0,
    }

    areas, seen_names = [], set()
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en")
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        if "center" in el:
            lat, lon = el["center"].get("lat"), el["center"].get("lon")
        else:
            lat, lon = el.get("lat"), el.get("lon")

        if lat is None or lon is None:
            continue

        boundary = tags.get("boundary", "")
        leisure  = tags.get("leisure", "")
        landuse  = tags.get("landuse", "")
        if boundary in TYPE_MAP:
            area_type = TYPE_MAP[boundary]
        elif leisure == "nature_reserve":
            area_type = "Nature Reserve"
        elif leisure == "park":
            area_type = "Park"
        elif landuse == "forest":
            area_type = "Forest"
        else:
            area_type = "Protected Area"

        areas.append({
            "name":        name,
            "type":        area_type,
            "lat":         lat,
            "lon":         lon,
            "website":     tags.get("website") or tags.get("contact:website", ""),
            "wikipedia":   tags.get("wikipedia", ""),
            "distance_km": round(_haversine_km(user_lat, user_lon, lat, lon), 1),
        })

    # Proximity dedup: collapse entries within 100 m of each other
    DEDUP_KM = 0.1
    merged, skip = [], set()
    for i, a in enumerate(areas):
        if i in skip:
            continue
        for j, b in enumerate(areas):
            if j <= i or j in skip:
                continue
            if _haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) <= DEDUP_KM:
                # Keep higher-priority type
                if TYPE_PRIORITY.get(b["type"], 0) > TYPE_PRIORITY.get(a["type"], 0):
                    a["type"] = b["type"]
                # Keep shorter (cleaner) name
                if len(b["name"]) < len(a["name"]):
                    a["name"] = b["name"]
                skip.add(j)
        merged.append(a)

    return merged


def get_trails_for_parks(parks, radius_km=10):
    """
    Fetches hiking trails for all areas in a single batched Overpass query.
    Radius is kept tight (10 km default) since we're now looking at small local areas.

    Returns:
        dict: {area_name: [trail_dict, ...]}
    """
    if not parks:
        return {}

    radius_m = radius_km * 1000
    around_clauses = "\n".join(
        f'relation["route"="hiking"](around:{radius_m},{p["lat"]},{p["lon"]});'
        for p in parks
    )
    query = f"""
    [out:json][timeout:55];
    (
      {around_clauses}
    );
    out center tags;
    """

    print("Fetching trails (single batched request)...")
    time.sleep(1)
    data = _post_overpass(query, timeout=60)

    if not data:
        print("  Could not fetch trails - recommending areas without trail detail.")
        return {p["name"]: [] for p in parks}

    SAC_LABELS = {
        "hiking":                    "Easy",
        "mountain_hiking":           "Moderate",
        "demanding_mountain_hiking": "Challenging",
        "alpine_hiking":             "Hard",
        "demanding_alpine_hiking":   "Very Hard",
        "difficult_alpine_hiking":   "Expert",
    }

    all_trails, seen_names = [], set()
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en")
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        center = el.get("center", {})
        try:
            trail_dist = round(float(tags.get("distance") or tags.get("length", "")), 1)
        except (ValueError, TypeError):
            trail_dist = None
        all_trails.append({
            "name":        name,
            "lat":         center.get("lat"),
            "lon":         center.get("lon"),
            "distance_km": trail_dist,
            "difficulty":  SAC_LABELS.get(tags.get("sac_scale", ""), "Unknown"),
            "surface":     tags.get("surface", "unknown"),
        })

    def _dist(lat1, lon1, lat2, lon2):
        if None in (lat1, lon1, lat2, lon2):
            return float("inf")
        dlat = lat1 - lat2
        dlon = (lon1 - lon2) * math.cos(math.radians((lat1 + lat2) / 2))
        return math.sqrt(dlat**2 + dlon**2)

    result = {p["name"]: [] for p in parks}
    for trail in all_trails:
        nearest = min(parks, key=lambda p: _dist(trail["lat"], trail["lon"], p["lat"], p["lon"]))
        result[nearest["name"]].append(trail)

    return result


if __name__ == "__main__":
    parks = get_parks(50.0755, 14.4378)
    trails_by_park = get_trails_for_parks(parks)
    for park in parks:
        trails = trails_by_park.get(park["name"], [])
        print(f"\n[{park['type']}] {park['name']} - {park['distance_km']} km away")
        for t in trails[:3]:
            dist_str = f"{t['distance_km']} km" if t["distance_km"] else "?"
            print(f"  - {t['name']} | {t['difficulty']} | {dist_str}")
