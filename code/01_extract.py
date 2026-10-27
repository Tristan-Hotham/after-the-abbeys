"""Step 1. Read the Wikidata monastery rows, collapse repeated rows to one record per
house, place each in a nation and county by a point-in-polygon test, and write
work/houses_all.json.

Wikidata returns one row per combination of values (type, order, designation,
dates). For each house (QID) I keep:
  * every instance type label and every heritage designation QID (as sets);
  * the order: if several are given, a single "family" is chosen by the rules in
    ORDER_FAMILY below (a Cistercian label anywhere wins over Benedictine,
    because Wikidata often lists the Benedictine rule as well as the reform order);
  * founded = the earliest inception year; dissolved = the dissolution year if
    exactly one distinct year in 1530 to 1545 is given, else the earliest.
Coordinates: if several points are given, the first is kept and the spread is
recorded.
Run: python3 code/01_extract.py
"""
import json, os, re
from collections import defaultdict
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "/home/claude/hist/_data2/wikidata/monasteries_uk.json"
COUNTIES = "/home/claude/hist/how-roman-is-your-road/data/counties.geojson"

# order label -> family used in the analysis
ORDER_FAMILY = {
    "Cistercians": "Cistercian", "Order of Cistercians of the Strict Observance": "Cistercian",
    "Congregation of Savigny": "Cistercian",  # Savigniac houses merged into the Cistercians in 1147
    "Bernardine Cistercians of Esquermes": "Cistercian",
    "Benedictines": "Benedictine", "Nuns of the order of Saint Benedict": "Benedictine",
    "Order of Cluny": "Cluniac",
    "Canons Regular of Saint Augustine": "Augustinian", "Augustinians": "Augustinian",
    "Order of St. Augustine": "Augustinian", "Augustinian nuns": "Augustinian",
    "Canons Regular of the Lateran": "Augustinian", "Canonesses Regular of Saint Augustine": "Augustinian",
    "Premonstratensians": "Premonstratensian",
    "Gilbertine Order": "Gilbertine",
    "Carthusian Order": "Carthusian",
    "Franciscans": "Friars", "Dominican Order": "Friars", "Carmelites": "Friars",
    "Crutched Friars": "Friars", "Trinitarian Order": "Friars", "Nuns of the Order of Preachers": "Friars",
    "Knights Hospitaller": "Military orders", "Knights Templar": "Military orders",
    "Grandmontines": "Other", "Bridgettines": "Other", "Order of Fontevrault": "Other",
    "Ursulines": "Other", "Order of Buddhist Contemplatives": "Other",
}
# instance-type labels that also name an order, used when P611 (order) is missing
TYPE_FAMILY = {
    "Cistercian monastery": "Cistercian", "Cistercian nunnery": "Cistercian", "Trappist monastery": "Cistercian",
    "benedictine abbey": "Benedictine", "benedictine nunnery": "Benedictine",
    "Augustinian friary": "Friars", "Franciscan friary": "Friars", "dominican friary": "Friars",
    "Carmelite monastery": "Friars", "friary": "Friars",
    "Carthusian monastery": "Carthusian",
}
PRIORITY = ["Cistercian", "Carthusian", "Premonstratensian", "Gilbertine", "Cluniac", "Augustinian",
            "Friars", "Military orders", "Benedictine", "Other"]


def year(s):
    m = re.match(r"^(-?\d{1,4})-", s or "")
    return int(m.group(1)) if m else None


def main():
    rows = json.load(open(SRC))
    by = defaultdict(list)
    for r in rows:
        by[r["m"]].append(r)
    feats = json.load(open(COUNTIES))["features"]
    geoms = [shape(f["geometry"]) for f in feats]
    tree = STRtree(geoms)
    out = []
    for q, rs in by.items():
        pts = sorted({r["c"] for r in rs if r.get("c", "").startswith("Point(")})
        if not pts:
            continue
        xy = [tuple(map(float, p[6:-1].split())) for p in pts]
        lon, lat = xy[0]
        spread = max(abs(a - lon) + abs(b - lat) for a, b in xy)
        types = sorted({r["tLabel"] for r in rs if r.get("tLabel")})
        her = sorted({r["heritage"] for r in rs if r.get("heritage", "").startswith("Q")})
        orders = sorted({r["orderLabel"] for r in rs if r.get("orderLabel") and not r["orderLabel"].startswith("http")})
        fams = {ORDER_FAMILY.get(o, "Other") for o in orders}
        src = "P611 order"
        if not fams:
            fams = {TYPE_FAMILY[t] for t in types if t in TYPE_FAMILY}
            src = "instance type" if fams else "none"
        fam = next((f for f in PRIORITY if f in fams), "Unknown")
        incs = sorted({year(r.get("inc")) for r in rs if year(r.get("inc")) is not None})
        dis = sorted({year(r.get("diss")) for r in rs if year(r.get("diss")) is not None})
        dis_in = [d for d in dis if 1530 <= d <= 1545]
        diss = dis_in[0] if len(dis_in) >= 1 else (dis[0] if dis else None)
        p = Point(lon, lat)
        nation = county = None
        for i in tree.query(p):
            if geoms[i].contains(p):
                nation, county = feats[i]["properties"]["nation"], feats[i]["properties"]["county"]
                break
        if nation is None:  # coastal points just off the generalised outline: nearest polygon within 2 km
            i = tree.nearest(p)
            if geoms[i].distance(p) < 0.03:
                nation, county = feats[i]["properties"]["nation"], feats[i]["properties"]["county"]
                nation_note = "nearest polygon"
        out.append(dict(qid=q, name=rs[0]["mLabel"], lat=lat, lon=lon, coord_spread_deg=round(spread, 4),
                        types=types, heritage=her, orders=orders, family=fam, family_source=src,
                        founded=incs[0] if incs else None, dissolved=diss,
                        dissolved_all=dis, enwiki=rs[0].get("enwiki"), nation=nation, county=county))
    json.dump(out, open(os.path.join(ROOT, "work", "houses_all.json"), "w"), indent=0)
    from collections import Counter
    print(len(out), "houses with coordinates of", len(by))
    print(Counter(h["nation"] for h in out))
    ew = [h for h in out if h["nation"] in ("England", "Wales")]
    print("E&W", len(ew), "dissolved 1536-1541:", sum(1 for h in ew if h["dissolved"] and 1536 <= h["dissolved"] <= 1541))
    print(Counter(h["family"] for h in ew if h["dissolved"] and 1536 <= h["dissolved"] <= 1541))


if __name__ == "__main__":
    main()
