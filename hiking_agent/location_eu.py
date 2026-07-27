"""
Location detection for Trail Finder.

Tries free IP geolocation APIs in order of trust and returns the first one that succeeds, it does NOT average/vote across sources. Real-world testing
showed that "majority agreement" between sources can be confidently wrong: several of these services license from the same underlying registries, so
multiple sources agreeing with each other doesn't mean they're right, it can just mean they share the same stale data. ipinfo.io was the most accurate
against a known real location in testing, so it's tried first.

Falls back to the geocoder library as a last resort. No API keys required. No GPS. No browser permissions.

IMPORTANT LIMITATION: IP geolocation can only ever be as good as what your IP address reveals. If you're on a VPN, in a cloud IDE / dev container
(Codespaces, remote SSH, etc.), on a corporate network, or on mobile data behind carrier-grade NAT, your outbound IP may belong to a data center or
gateway far from your actual location, and every IP-based service will be wrong in the same way, because they're all reading the same IP. If that's
your situation, use the TRAILFINDER_LAT / TRAILFINDER_LON override below instead of relying on any IP-based source.
"""

import os
import time

import requests
import geocoder

_HEADERS = {
    "User-Agent": "TrailFinder/1.0",
    "Accept": "application/json",
}

# (connect_timeout, read_timeout), fails fast on a dead/blocked host instead of waiting a long read timeout.
_TIMEOUT = (3, 5)

# Reused across calls for connection pooling / keep-alive.
_session = requests.Session()

# Tried in this order; first one that returns usable data wins. ipinfo.io first: most accurate against a known real-world location in testing. The others are fallbacks for when it's down or rate-limited.
_IP_APIS = [
    {
        "url":     "https://ipinfo.io/json",
        "lat":     lambda d: float(d["loc"].split(",")[0]) if d.get("loc") else None,
        "lon":     lambda d: float(d["loc"].split(",")[1]) if d.get("loc") else None,
        "city":    lambda d: d.get("city"),
        "country": lambda d: d.get("country"),
        "ok":      lambda d: bool(d.get("loc")),
    },
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
        "url":     "https://geolocation-db.com/json/",
        "lat":     lambda d: d.get("latitude"),
        "lon":     lambda d: d.get("longitude"),
        "city":    lambda d: d.get("city"),
        "country": lambda d: d.get("country_name"),
        "ok":      lambda d: d.get("latitude") not in (None, "Not found"),
    },
]


def _query_one(api):
    """Query a single IP geolocation source. Returns a result dict or None."""
    try:
        r = _session.get(api["url"], headers=_HEADERS, timeout=_TIMEOUT)
        if r.status_code != 200:
            return None
        data = r.json()
        if not api["ok"](data):
            return None
        lat = api["lat"](data)
        lon = api["lon"](data)
        if lat and lon:
            return {
                "lat": float(lat),
                "lon": float(lon),
                "city": api["city"](data) or "Unknown",
                "country": api["country"](data) or "",
                "source": api["url"].split("/")[2],
            }
    except Exception:
        return None
    return None


_cache = {"result": None, "timestamp": 0.0}


def get_current_location(verbose=True, cache_ttl=300):
    """
    Detect location from public IP address.

    Tries each source in _IP_APIS in order and returns the first one that
    succeeds. Falls back to the geocoder library if every API fails.

    Manual override: if the environment variables TRAILFINDER_LAT and
    TRAILFINDER_LON are set, they're used directly and no network calls are
    made. Use this if you know IP geolocation will be wrong for your setup
    (VPN, cloud IDE, corporate network, mobile data), e.g.:
        export TRAILFINDER_LAT=50.0880
        export TRAILFINDER_LON=14.4208
        export TRAILFINDER_CITY=Prague      # optional, cosmetic only
        export TRAILFINDER_COUNTRY=CZ       # optional, cosmetic only

    Args:
        verbose: if True, print which source the location came from.
        cache_ttl: seconds to reuse the last result within this process
                   without hitting the network again. 0 disables caching.

    Returns:
        tuple: (latitude, longitude, city, country)
               Returns (None, None, None, None) if all sources fail.
    """
    lat_env, lon_env = os.environ.get("TRAILFINDER_LAT"), os.environ.get("TRAILFINDER_LON")
    if lat_env and lon_env:
        try:
            return (
                float(lat_env),
                float(lon_env),
                os.environ.get("TRAILFINDER_CITY", "Manual location"),
                os.environ.get("TRAILFINDER_COUNTRY", ""),
            )
        except ValueError:
            pass  # malformed override, fall through to IP geolocation

    if cache_ttl and _cache["result"] and (time.time() - _cache["timestamp"]) < cache_ttl:
        return _cache["result"]

    for api in _IP_APIS:
        res = _query_one(api)
        if res:
            if verbose:
                print(f"Location from {res['source']}: {res['city']}, {res['country']}")
            result = (res["lat"], res["lon"], res["city"], res["country"])
            if cache_ttl:
                _cache["result"], _cache["timestamp"] = result, time.time()
            return result

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
        res = _query_one(api)
        name = api["url"].split("/")[2]
        if res:
            print(f"  {name:22s} → {res['city']} ({res['lat']}, {res['lon']})")
        else:
            print(f"  {name:22s} → failed or returned no data")

    print()
    print("Result used (first successful source, ipinfo.io preferred):")
    lat, lon, city, country = get_current_location(verbose=False, cache_ttl=0)
    if lat:
        print(f"  City    : {city}, {country}")
        print(f"  Coords  : {lat:.4f}, {lon:.4f}")
    else:
        print("  Could not detect location.")
