"""
Location detection for Trail Finder.

Tries four free IP geolocation APIs in order of accuracy. Falls back to geocoder library as last resort. No API keys required. No GPS. No browser permissions.
"""

import requests
import geocoder

_HEADERS = {
    "User-Agent": "TrailFinder/1.0",
    "Accept": "application/json",
}

_IP_APIS = [
    {
        "url":     "http://ip-api.com/json/?fields=status,lat,lon,city,country",
        "lat":     lambda d: d.get("lat"),
        "lon":     lambda d: d.get("lon"),
        "city":    lambda d: d.get("city"),
        "country": lambda d: d.get("country"),
        "ok":      lambda d: d.get("status") == "success",
    },
    {
        "url":     "https://ipapi.co/json/",
        "lat":     lambda d: d.get("latitude"),
        "lon":     lambda d: d.get("longitude"),
        "city":    lambda d: d.get("city"),
        "country": lambda d: d.get("country_name"),
        "ok":      lambda d: not d.get("error") and d.get("latitude"),
    },
    {
        "url":     "https://ipinfo.io/json",
        "lat":     lambda d: float(d["loc"].split(",")[0]) if d.get("loc") else None,
        "lon":     lambda d: float(d["loc"].split(",")[1]) if d.get("loc") else None,
        "city":    lambda d: d.get("city"),
        "country": lambda d: d.get("country"),
        "ok":      lambda d: bool(d.get("loc")),
    },
    {
        "url":     "https://geolocation-db.com/json/",
        "lat":     lambda d: d.get("latitude"),
        "lon":     lambda d: d.get("longitude"),
        "city":    lambda d: d.get("city"),
        "country": lambda d: d.get("country_name"),
        "ok":      lambda d: d.get("latitude") not in (None, "Not found"),
    },
]


def get_current_location():
    """
    Detect location from public IP address.

    Tries four geolocation APIs in order — ip-api.com is the most accurate
    and typically returns city-level precision. Falls back to geocoder if all
    APIs fail.

    Returns:
        tuple: (latitude, longitude, city, country)
               Returns (None, None, None, None) if all sources fail.
    """
    for api in _IP_APIS:
        try:
            r = requests.get(api["url"], headers=_HEADERS, timeout=6)
            if r.status_code != 200:
                continue
            data = r.json()
            if not api["ok"](data):
                continue
            lat     = api["lat"](data)
            lon     = api["lon"](data)
            city    = api["city"](data) or "Unknown"
            country = api["country"](data) or ""
            if lat and lon:
                return float(lat), float(lon), city, country
        except Exception:
            continue

    # Final fallback
    try:
        g = geocoder.ip("me")
        if g.ok:
            return g.latlng[0], g.latlng[1], g.city, g.country
    except Exception:
        pass

    return None, None, None, None


if __name__ == "__main__":
    print("Testing all location sources...\n")

    for api in _IP_APIS:
        name = api["url"].split("/")[2]
        try:
            r = requests.get(api["url"], headers=_HEADERS, timeout=6)
            if r.status_code == 200:
                data = r.json()
                if api["ok"](data):
                    lat  = api["lat"](data)
                    lon  = api["lon"](data)
                    city = api["city"](data)
                    print(f"  {name:30s} → {city} ({lat}, {lon})")
                else:
                    print(f"  {name:30s} → returned error in data")
            else:
                print(f"  {name:30s} → HTTP {r.status_code}")
        except Exception as e:
            print(f"  {name:30s} → failed: {e}")

    print()
    print("Best result:")
    lat, lon, city, country = get_current_location()
    if lat:
        print(f"  City    : {city}, {country}")
        print(f"  Coords  : {lat:.4f}, {lon:.4f}")
    else:
        print("  Could not detect location.")
