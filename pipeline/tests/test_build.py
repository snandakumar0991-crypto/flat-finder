import build_city
import geo


def area(name, center, r=150):
    return {"type": "Feature", "properties": {"osm": "way/" + name, "name": name},
            "geometry": {"type": "Polygon", "coordinates": [geo.circle(center, r)]}}


def test_match_area_inside_and_by_name():
    areas = [area("Heritage One", (77.0891, 28.4027)), area("Skyon", (77.0966, 28.3995))]
    g = build_city.Grid(areas, lambda a: geo.centroid(a["geometry"]["coordinates"][0]))
    p = {"name": "Conscient Heritage One", "lng": 77.0893, "lat": 28.4030}
    assert build_city.match_area(p, g)["properties"]["name"] == "Heritage One"
    near = {"name": "Ireo Skyon", "lng": 77.0966 + 0.0025, "lat": 28.3995}  # ~245 m east, outside
    assert build_city.match_area(near, g)["properties"]["name"] == "Skyon"
    far = {"name": "Random Homes", "lng": 77.2, "lat": 28.5}
    assert build_city.match_area(far, g) is None


def test_dedupe_merges_phases_close_by():
    a = {"name": "Heritage One", "lng": 77.0890, "lat": 28.4034, "url": "a"}
    b = {"name": "Heritage One", "lng": 77.0891, "lat": 28.4021, "url": "b"}
    c = {"name": "Heritage One", "lng": 77.2, "lat": 28.5, "url": "c"}
    out = build_city.dedupe([a, b, c])
    assert len(out) == 2 and out[0]["merged"] == ["b"]


def test_dedupe_keeps_the_richer_duplicate():
    # same society listed twice: the first copy is sparse, the second has towers, amenities and a rent listing
    sparse = {"mb_id": 1, "name": "K Raheja Quiescent Heights", "lng": 78.3854, "lat": 17.4443, "url": "a",
              "units": 68, "config_text": "6 BHK", "configs": {"units": [{"bhk": 6, "sqft": 6000, "kind": "10002"}]}}
    rich = {"mb_id": 2, "name": "K Raheja Quiescent Heights", "lng": 78.3855, "lat": 17.4443, "url": "b",
            "units": 67, "towers": 2, "amenities": ["Swimming Pool", "Club House"], "config_text": "3, 4 BHK Apartments",
            "rent_listings": [{"bhk": 4, "price": 80000, "url": "r1"}],
            "configs": {"units": [{"bhk": 3, "sqft": 2400, "kind": "10002"}, {"bhk": 4, "sqft": 3000, "kind": "10002"}]}}
    (m,) = build_city.dedupe([sparse, rich])
    assert m["mb_id"] == 2 and m["towers"] == 2 and m["units"] == 68
    assert "Swimming Pool" in m["amenities"] and m["rent_listings"][0]["price"] == 80000
    assert sorted(u["bhk"] for u in m["configs"]["units"]) == [3, 4, 6]
    assert m["merged"] == ["a"]


def test_dedupe_combines_listings_without_doubling():
    a = {"name": "Navadweepa", "lng": 78.38, "lat": 17.44, "url": "a", "rent_listings": [{"bhk": 3, "price": 70000, "url": "x"}]}
    b = {"name": "Navadweepa", "lng": 78.38, "lat": 17.44, "url": "b",
         "rent_listings": [{"bhk": 3, "price": 70000, "url": "x"}, {"bhk": 3, "price": 66000, "url": "y"}]}
    (m,) = build_city.dedupe([a, b])
    assert sorted(l["price"] for l in m["rent_listings"]) == [66000, 70000]


def test_config_bhks():
    assert build_city.config_bhks("3, 4, 5, 6 BHK Apartments") == [3, 4, 5, 6]
    assert build_city.config_bhks("2-4 BHK Flats") == [2, 3, 4]
    assert build_city.config_bhks("2.5, 3 BHK") == [2.5, 3]
    assert build_city.config_bhks("Residential Plot") == []


def test_portal_units_adds_bhks_named_only_in_summary():
    p = {"url": "u", "config_text": "3, 4, 5, 6 BHK Apartments", "configs": {"units": [{"bhk": 6, "sqft": 6000}]}}
    units = build_city.portal_units(p)
    assert [u["bhk"] for u in units] == [6, 3, 4, 5]
    assert units[1]["size_sqft"] is None and units[1]["confidence"] == "portal summary"


def test_kind_of():
    assert build_city.kind_of({"config_text": "2, 3, 4 BHK Multistorey Apartments"}) == "apartment"
    assert build_city.kind_of({"config_text": "Residential Plot"}) == "plot"
    assert build_city.kind_of({"config_text": "4 BHK Villa"}) == "villa"


def test_neighbourhood_sized_area_is_not_a_society_site():
    big = area("DLF Phase 4", (77.08, 28.46), r=700)  # ~1.5 km2
    g = build_city.Grid([big], lambda a: geo.centroid(a["geometry"]["coordinates"][0]))
    p = {"name": "Some Apartments", "lng": 77.08, "lat": 28.46, "acres": 5}
    assert build_city.match_area(p, g) is None


def test_kind_from_unit_codes_when_text_missing():
    assert build_city.kind_of({"configs": {"units": [{"kind": "10000"}]}}) == "plot"
    assert build_city.kind_of({"configs": {"units": [{"kind": "10008"}, {"kind": "10002"}]}}) == "apartment"
    assert build_city.kind_of({}) == "apartment~"


def test_kind_from_card_type_codes():
    assert build_city.kind_of({"type_codes": ["10000"]}) == "plot"
    assert build_city.kind_of({"card_units": [{"kind": "10003", "bhk": 3, "sqft": 1900.0}]}) == "builder floor"


def test_infer_kind_from_name():
    assert build_city.kind_of({"name": "Sai Ram Apartment"}) == "apartment~"
    assert build_city.kind_of({"name": "Rzone Land Plot"}) == "plot~"
    assert build_city.kind_of({"name": "Emaar Business District 114"}) == "commercial~"
    assert build_city.kind_of({"name": "Ashiana Villas"}) == "villa~"


def test_match_verified_needs_whole_name_and_sector():
    ps = [{"mb_id": 1, "name": "M3M", "locality": "Sector 65"},
          {"mb_id": 2, "name": "M3M Heights", "locality": "Sector 65"},
          {"mb_id": 3, "name": "M3M St Andrews at SCDA", "locality": "Sector 113"},
          {"mb_id": 4, "name": "M3M St. Andrews", "locality": "Sector 65"}]
    assert build_city.match_verified({"match": ["M3M Heights"], "sector": "65"}, ps)["mb_id"] == 2
    assert build_city.match_verified({"match": ["M3M St Andrews"], "sector": "65"}, ps)["mb_id"] == 4
    assert build_city.match_verified({"match": ["M3M Heights"], "sector": "65"}, ps, taken={2}) is None
