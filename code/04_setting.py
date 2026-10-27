"""Step 4. Measure the setting of every house: how many people lived near the site in 1086,
how high and how hilly the ground is, and how far the nearest watercourse is.

For each house with coordinates (and for a set of random comparison points):
  dom_nn_km   distance to the nearest located Domesday place (any size)
  dom_n5      number of located Domesday places within 5 km
  hh5, hh10   1086 households recorded for the Domesday places within 5 km and 10 km
  elev_m      ground height (AWS Terrain Tiles z10, bilinear; reader from within-sight/code/dem.py)
  relief_m    highest minus lowest ground among the site and 16 points on rings 500 m and 1 km away
  river_m     distance to the nearest OS Open Rivers watercourse centre line (canals excluded)
  dom_area    True where the 1086 measures are meaningful: England outside Northumberland, County
              Durham, Tyne and Wear and Cumbria (largely not surveyed), outside Lancashire, Greater
              Manchester and Merseyside (surveyed, but with almost no household counts in the data:
              fewer than 1 in 4 random points there have any recorded households within 5 km),
              outside Greater London and
              more than 3 km from Winchester (London and Winchester are absent from Domesday Book).

Random comparison points: 400 per English county inside the Domesday area, drawn uniformly
inside the county outline (ONS boundaries via how-roman-is-your-road/data/counties.geojson),
seed 1536. They give the typical value of each measure for an ordinary spot in that county.

Inputs: work/houses_built.json; domesday-destiny/data/domesday_places.csv; DEM; OS Open Rivers.
Outputs: work/houses_setting.json, data/baseline_points.csv
Run: python3 code/04_setting.py
"""
import json
import os
import sqlite3
import struct
import sys

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(HIST, "within-sight", "code"))
from dem import DEM  # noqa: E402

DOMESDAY = os.path.join(HIST, "domesday-destiny", "data", "domesday_places.csv")
RIVERS = os.path.join(HIST, "osrivers", "Data", "oprvrs_gb.gpkg")
COUNTIES = os.path.join(HIST, "how-roman-is-your-road", "data", "counties.geojson")
NOT_SURVEYED = {"Northumberland", "Durham", "Tyne and Wear", "Cumbria", "Greater London",
                "Lancashire", "Greater Manchester", "Merseyside"}
WINCHESTER = (51.0612, -1.3131)
ENV_BYTES = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}


def decode(blob):
    """GeoPackage geometry blob -> list of (N,2) arrays (same reader as lost-villages/code/03_environment.py)."""
    flags = blob[3]
    wkb = blob[8 + ENV_BYTES[(flags >> 1) & 7]:]

    def read(p):
        bo = "<" if wkb[p] == 1 else ">"
        typ = struct.unpack(bo + "I", wkb[p + 1:p + 5])[0]
        dim = 3 if (typ // 1000 in (1, 2) or typ & 0x80000000) else 2
        base = (typ % 1000) & 0xFF
        p += 5
        n = struct.unpack(bo + "I", wkb[p:p + 4])[0]
        p += 4
        if base == 2:
            a = np.frombuffer(wkb[p:p + 8 * dim * n], dtype=bo + "f8").reshape(n, dim)[:, :2]
            return [a], p + 8 * dim * n
        out = []
        for _ in range(n):
            a, p = read(p)
            out += a
        return out, p
    return read(0)[0]


def densify(lines, step=25.0):
    pts = []
    for a in lines:
        if len(a) < 2:
            pts.append(a)
            continue
        seg = np.diff(a, axis=0)
        L = np.hypot(seg[:, 0], seg[:, 1])
        k = np.maximum(1, np.ceil(L / step).astype(int))
        for i in range(len(seg)):
            t = np.arange(k[i]) / k[i]
            pts.append(a[i] + seg[i] * t[:, None])
        pts.append(a[-1:])
    return np.vstack(pts)


def river_tree():
    con = sqlite3.connect(RIVERS)
    lines = []
    for (geom,) in con.execute("select geometry from watercourse_link where form != 'canal'"):
        lines += decode(geom)
    return cKDTree(densify(lines))


def measures(lat, lon, dem, to_bng, to_wgs, dtree, dhh, rtree):
    lat = np.asarray(lat, float)
    lon = np.asarray(lon, float)
    x, y = to_bng.transform(lon, lat)
    xy = np.c_[x, y]
    out = {}
    d, _ = dtree.query(xy)
    out["dom_nn_km"] = np.round(d / 1000, 2)
    for r, key in ((5000, "5"), (10000, "10")):
        idx = dtree.query_ball_point(xy, r)
        out["hh" + key] = np.array([float(dhh[i].sum()) for i in idx]).round(1)
        if key == "5":
            out["dom_n5"] = np.array([len(i) for i in idx])
    e0 = dem.elev(lat, lon)
    out["elev_m"] = np.round(e0, 1)
    samples = [e0]
    for r in (500, 1000):
        for a in np.arange(8) * np.pi / 4:
            lo, la = to_wgs.transform(x + r * np.cos(a), y + r * np.sin(a))
            samples.append(dem.elev(la, lo))
    S = np.vstack(samples)
    out["relief_m"] = np.round(S.max(0) - S.min(0), 1)
    out["river_m"] = np.round(rtree.query(xy)[0])
    return out


def main():
    to_bng = Transformer.from_crs(4326, 27700, always_xy=True)
    to_wgs = Transformer.from_crs(27700, 4326, always_xy=True)
    dem = DEM()
    P = pd.read_csv(DOMESDAY, usecols=["lat", "lng", "households1086"]).dropna(subset=["lat", "lng"])
    px, py = to_bng.transform(P["lng"].values, P["lat"].values)
    dtree = cKDTree(np.c_[px, py])
    dhh = P["households1086"].fillna(0).values
    print("rivers ...")
    rtree = river_tree()
    feats = [f for f in json.load(open(COUNTIES))["features"] if f["properties"]["nation"] in ("England", "Wales")]
    geoms = [shape(f["geometry"]) for f in feats]
    gtree = STRtree(geoms)

    B = json.load(open(os.path.join(ROOT, "work", "houses_built.json")))
    H = [h for h in B["houses"] if h["lat"] is not None]
    lat = np.array([h["lat"] for h in H])
    lon = np.array([h["lon"] for h in H])
    M = measures(lat, lon, dem, to_bng, to_wgs, dtree, dhh, rtree)
    for i, h in enumerate(H):
        for k, v in M.items():
            h[k] = float(v[i]) if k not in ("dom_n5",) else int(v[i])
        p = Point(h["lon"], h["lat"])
        cty = None
        for j in gtree.query(p):
            if geoms[j].contains(p):
                cty = feats[j]["properties"]["county"]
                break
        if cty is None:
            j = gtree.nearest(p)
            if geoms[j].distance(p) < 0.05:
                cty = feats[j]["properties"]["county"]
        h["ons_county"] = cty
        nat = feats[[f["properties"]["county"] for f in feats].index(cty)]["properties"]["nation"] if cty else h["nation"]
        win = np.hypot((h["lat"] - WINCHESTER[0]) * 110.57, (h["lon"] - WINCHESTER[1]) * 69.9) < 3
        h["dom_area"] = bool(nat == "England" and cty not in NOT_SURVEYED and cty is not None and not win)
    json.dump(B, open(os.path.join(ROOT, "work", "houses_setting.json"), "w"), ensure_ascii=False, indent=0)

    # random comparison points
    rng = np.random.default_rng(1536)
    rows = []
    for f, g in zip(feats, geoms):
        c = f["properties"]["county"]
        if f["properties"]["nation"] != "England" or c in NOT_SURVEYED:
            continue
        minx, miny, maxx, maxy = g.bounds
        got = []
        while len(got) < 400:
            xs = rng.uniform(minx, maxx, 2000)
            ys = rng.uniform(miny, maxy, 2000)
            for xx, yy in zip(xs, ys):
                if g.contains(Point(xx, yy)):
                    if c == "Hampshire" and np.hypot((yy - WINCHESTER[0]) * 110.57, (xx - WINCHESTER[1]) * 69.9) < 3:
                        continue
                    got.append((yy, xx))
                    if len(got) == 400:
                        break
        a = np.array(got)
        m = measures(a[:, 0], a[:, 1], dem, to_bng, to_wgs, dtree, dhh, rtree)
        for i in range(len(a)):
            rows.append(dict(county=c, lat=round(a[i, 0], 5), lon=round(a[i, 1], 5), **{k: (v[i].item() if hasattr(v[i], "item") else v[i]) for k, v in m.items()}))
    pd.DataFrame(rows).to_csv(os.path.join(ROOT, "data", "baseline_points.csv"), index=False)
    print(len(H), "houses measured;", len(rows), "baseline points")


if __name__ == "__main__":
    main()
