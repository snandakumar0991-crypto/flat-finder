# Hyderabad: our search

A family 3 BHK to rent in a gated society. The school matters most, then the office.

- School: Anthea Montessori, Plot 2, Shilpi Valley, Gafoor Nagar, Madhapur 500081
- Office: Sattva Knowledge City, Silpa Gram Craft Village, HITEC City 500032
- Today: My Home Vihanga, ₹64k rent + about ₹8k maintenance (₹72k a month)

Open `http://localhost:5173/?city=hyderabad&preset=ours` for the saved search: 3 BHK, rent up to ₹75k, at most 20 minutes to the school and 25 to the office, closest to the school first. Each card shows how much closer or further it is than Vihanga.

## What the numbers are, and are not

- **Rent** is the median of live Magicbricks rent listings for that society and BHK. Maintenance is **not** included, so compare with ₹64k, not ₹72k.
- **Drive time** is by road with **no traffic** (OSRM). Peak hour around HITEC City is a lot slower, so treat 20 minutes as a ranking, not a promise. Check the top few in Google Maps at 8:30 am.
- Societies with no route yet are "not checked", never a match.

## Run it on Windows

Install Python 3.9+ and Node 20+ (for example `winget install Python.Python.3.12 OpenJS.NodeJS.LTS`). Then, in PowerShell from the repo folder:

```powershell
cd pipeline
py mb_crawl.py list hyderabad        # a few minutes
py mb_crawl.py projects hyderabad    # about an hour; safe to stop and rerun
py osm_fetch.py hyderabad
py drive_times.py hyderabad          # prints a Google Maps link for each anchor: check them
py build_city.py hyderabad

cd ..\web
npm install
npm run dev                          # then open the link above
```

If an anchor lands in the wrong place, copy the right "lat, lng" from Google Maps into `data/cities.json` as `"lat"` and `"lng"` on that anchor and run `drive_times.py` and `build_city.py` again.

Do not commit `pipeline/cache/` or `osm_buildings.geojson`. Bedroom-size reading (OCR, Jev, HRERA) is not used for Hyderabad.
