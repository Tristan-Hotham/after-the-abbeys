"""Step 6. Build index.html and README.md.

Every number in the page text is a placeholder like {{setting.Cistercian monks.pct_median|f0}}
filled from data/results.json; the compact map and chart data are embedded as `const D = ...`.
Formats: int (thousands commas), pct0, pct1, f0, f1, f2, raw, words, abs (absolute value, f1).
Run: python3 code/06_build_site.py
"""
import json
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))

GROUPS = ["Benedictine monks", "Benedictine nuns", "Cistercian monks", "Cistercian nuns", "Augustinian canons", "Augustinian canonesses",
          "Premonstratensian", "Cluniac", "Gilbertine", "Carthusian", "Friars", "Military orders", "Other orders", "Unknown"]
ORDERS = ["Benedictine", "Cistercian", "Augustinian", "Premonstratensian", "Cluniac", "Gilbertine", "Carthusian", "Friars", "Military orders", "Other orders", "Unknown"]
AFTER = ["cathedral", "monastic", "church", "house", "school", "farm", "other", "ruin", "earthworks", "nothing", "protected", "unclear"]


def build_data():
    H = pd.read_csv(os.path.join(ROOT, "data", "houses.csv"), keep_default_na=False)
    S = pd.read_csv(os.path.join(ROOT, "data", "house_settings.csv"), keep_default_na=False).set_index("id")
    counties = sorted(set(H.county))
    rows = []
    for _, h in H.iterrows():
        if h["lat"] == "":
            continue
        s = S.loc[h["id"]] if h["id"] in S.index else None
        dom = s is not None and str(s["dom_area"]) == "True"
        title = h["enwiki"].rsplit("/", 1)[-1] if h["enwiki"] else ""
        rows.append([round(float(h["lat"]), 4), round(float(h["lon"]), 4), h["name"], counties.index(h["county"]), GROUPS.index(h["group"]),
                     ORDERS.index(h["order"]), int(h["dissolved"]), AFTER.index(h["afterlife"]), h["afterlife_evidence"], h["kept_name"],
                     float(s["hh5"]) if dom else None, float(s["hh5_pct_county"]) if dom and s["hh5_pct_county"] != "" else None,
                     round(float(s["elev_m"])) if s is not None else None, title, h["later"][:400], h["dissolved_text"][:80]])
    return dict(h=rows, counties=counties, groups=GROUPS, orders=ORDERS, after=AFTER, R=R)


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int":
        return f"{int(round(v)):,}"
    if f == "pct0":
        return f"{v * 100:.0f}%"
    if f == "pct1":
        return f"{v * 100:.1f}%"
    if f == "f0":
        return f"{v:.0f}"
    if f == "f1":
        return f"{v:.1f}"
    if f == "f2":
        return f"{v:.2f}"
    if f == "abs":
        return f"{abs(v):.0f}"
    if f == "words":
        w = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen".split()
        return w[int(v)] if int(v) < len(w) else f"{int(v):,}"
    return str(v)


def sub(m):
    path, _, f = m.group(1).partition("|")
    return fmt(get(path.strip()), f.strip() or "raw")


def main():
    D = build_data()
    site = json.dumps(D, ensure_ascii=False, separators=(",", ":")).replace("–", "-").replace("—", "-")
    open(os.path.join(ROOT, "work", "site.json"), "w").write(site)
    t = open(os.path.join(CODE, "page_template.html")).read()
    t = re.sub(r"\{\{(.+?)\}\}", sub, t)
    t = t.replace("/*DATA*/", "const D = " + site + ";")
    open(os.path.join(ROOT, "index.html"), "w").write(t)
    print("index.html", len(t.encode()) // 1024, "KB")
    md = re.sub(r"\{\{(.+?)\}\}", sub, open(os.path.join(CODE, "README_template.md")).read())
    open(os.path.join(ROOT, "README.md"), "w").write(md)
    print("README.md written")


if __name__ == "__main__":
    main()
