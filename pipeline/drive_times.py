"""Drive time from every society to the city's anchors (e.g. a school and an office), once, cached.

usage: python drive_times.py <city>   -> out/<city>/anchors.json, out/<city>/drive_times.json

Needs out/<city>/mb_projects.json (run mb_crawl.py first). Anchors come from data/cities.json.
An anchor without lat/lng is geocoded with OpenStreetMap Nominatim; check the printed map link and,
if it is off, paste the right "lat, lng" from Google Maps into cities.json as "lat" and "lng".

Times are from the public OSRM router: road distance and free-flow time, with NO traffic.
Peak-hour times in HITEC City are much longer; the site labels these as "no traffic".
"""
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).parent
CITIES = json.loads((ROOT.parent / "data" / "cities.json").read_text(encoding="utf-8"))
UA = "flat-finder/0.1 (personal use)"
OSRM = "https://router.project-osrm.org/table/v1/driving/"
CHUNK = 80  # societies per OSRM request, plus the anchors


def get_json(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return json.loads(urllib.request.urlopen(req, timeout=60).read())
        except Exception as e:  # rate limit or hiccup: back off
            print("  retry", attempt + 1, e, flush=True)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("gave up: " + url[:120])


def geocode(a, bbox):
    s, w, n, e = bbox
    q = urllib.parse.urlencode({"q": a.get("query") or a["address"], "format": "json", "limit": 1,
                                "viewbox": f"{w},{n},{e},{s}", "bounded": 1})
    r = get_json("https://nominatim.openstreetmap.org/search?" + q)
    time.sleep(1.1)  # Nominatim policy: at most 1 request per second
    if not r:
        raise SystemExit(f"could not geocode {a['label']}: add \"lat\" and \"lng\" for it in data/cities.json")
    return float(r[0]["lat"]), float(r[0]["lon"])


def anchors_for(city):
    cfg = CITIES[city]
    out = []
    for a in cfg.get("anchors", []):
        lat, lng = (a["lat"], a["lng"]) if "lat" in a else geocode(a, cfg["bbox"])
        out.append({**a, "lat": lat, "lng": lng})
        print(f"{a['label']}: {lat:.5f}, {lng:.5f}  check: https://www.google.com/maps?q={lat},{lng}")
    return out


def table(origins, anchors):
    """OSRM table: minutes and km from each origin to each anchor."""
    coords = ";".join(f"{lng},{lat}" for lat, lng in origins + [(a["lat"], a["lng"]) for a in anchors])
    n = len(origins)
    q = urllib.parse.urlencode({"sources": ";".join(map(str, range(n))),
                                "destinations": ";".join(str(n + i) for i in range(len(anchors))),
                                "annotations": "duration,distance"})
    r = get_json(OSRM + coords + "?" + q)
    if r.get("code") != "Ok":
        raise RuntimeError(r.get("message") or r.get("code"))
    return [[(None if d is None else round(d / 60, 1), None if m is None else round(m / 1000, 1))
             for d, m in zip(r["durations"][i], r["distances"][i])] for i in range(n)]


def main(city):
    out = ROOT / "out" / city
    anchors = anchors_for(city)
    if not anchors:
        raise SystemExit(f"{city} has no anchors in data/cities.json")
    (out / "anchors.json").write_text(json.dumps(anchors, indent=1))
    cache_f = out / "drive_times.json"
    cache = json.loads(cache_f.read_text(encoding="utf-8")) if cache_f.exists() else {}
    key = "|".join(f"{a['key']}@{a['lat']:.5f},{a['lng']:.5f}" for a in anchors)
    if cache.get("_anchors") != key:
        cache = {"_anchors": key}  # anchors moved: recompute everything
    projects = [p for p in json.loads((out / "mb_projects.json").read_text(encoding="utf-8")) if p.get("lat") and p.get("lng")]
    todo = [p for p in projects if str(p["mb_id"]) not in cache]
    print(f"{len(projects)} located projects, {len(todo)} to route")
    for i in range(0, len(todo), CHUNK):
        part = todo[i:i + CHUNK]
        rows = table([(p["lat"], p["lng"]) for p in part], anchors)
        for p, row in zip(part, rows):
            cache[str(p["mb_id"])] = {a["key"]: {"min": t, "km": km} for a, (t, km) in zip(anchors, row)}
        cache_f.write_text(json.dumps(cache))
        print(f"  routed {min(i + CHUNK, len(todo))}/{len(todo)}", flush=True)
        time.sleep(1.0)  # the public OSRM server is shared: be gentle


if __name__ == "__main__":
    main(next((a for a in sys.argv[1:] if a in CITIES), "hyderabad"))
