"""Step 5. Analysis: write the clean data files and data/results.json (every number used anywhere).

Main set: houses in England and Wales dissolved 1536 to 1541 (year from the Wikipedia list, or
from Wikidata for houses the lists lack or whose row lacks a year; see 03_build.py).

Question 1: afterlife class counts and shares, by order and by nation.
Question 2: setting by order, inside the Domesday area. Three views:
  (a) raw medians of 1086 households within 5 km (hh5) and other measures;
  (b) county-adjusted: each house's hh5 as a percentile among 400 random points in its own
      county (50 = as busy as a typical spot in that county; low = emptier than most);
  (c) OLS of log(1 + hh5) on order with county fixed effects (Benedictine = reference).
Uncertainty: bootstrap (5,000 resamples, seed 1539) for medians and median differences;
Mann-Whitney U for Cistercian monks against Benedictine monks.
Run: python3 code/05_analyse.py
"""
import json
import os

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import mannwhitneyu

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RNG = np.random.default_rng(1539)


def boot_median(x, n=5000):
    x = np.asarray(x, float)
    m = np.median(RNG.choice(x, (n, len(x))), axis=1)
    return [round(float(np.percentile(m, 2.5)), 1), round(float(np.percentile(m, 97.5)), 1)]


def boot_diff(a, b, n=5000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = np.median(RNG.choice(a, (n, len(a))), axis=1) - np.median(RNG.choice(b, (n, len(b))), axis=1)
    return [round(float(np.percentile(d, 2.5)), 1), round(float(np.percentile(d, 97.5)), 1)]


def group(row):
    if row["order"] == "Cistercian":
        return "Cistercian nuns" if row["female"] else "Cistercian monks"
    if row["order"] == "Benedictine":
        return "Benedictine nuns" if row["female"] else "Benedictine monks"
    if row["order"] == "Augustinian":
        return "Augustinian canonesses" if row["female"] else "Augustinian canons"
    return row["order"]


def main():
    B = json.load(open(os.path.join(ROOT, "work", "houses_setting.json")))
    H = pd.DataFrame(B["houses"])
    base = pd.read_csv(os.path.join(ROOT, "data", "baseline_points.csv"))
    H["group"] = H.apply(group, axis=1)
    main = H[(H.dissolved >= 1536) & (H.dissolved <= 1541)].copy()
    main = main.sort_values(["nation", "county", "name"]).reset_index(drop=True)
    main["id"] = ["h%03d" % i for i in range(len(main))]

    # percentile of each house's hh5 among random points in the same county
    def pct(row):
        b = base.loc[base.county == row["ons_county"], "hh5"].values
        if not row.get("dom_area") or len(b) == 0 or pd.isna(row.get("hh5")):
            return np.nan
        return round(100.0 * (np.sum(b < row["hh5"]) + 0.5 * np.sum(b == row["hh5"])) / len(b), 1)
    main["hh5_pct_county"] = main.apply(pct, axis=1)
    H["hh5_pct_county"] = H.apply(pct, axis=1)

    R = {}
    meta = B["meta"]
    R["n_houses"] = int(len(main))
    R["n_england"] = int((main.nation == "England").sum())
    R["n_wales"] = int((main.nation == "Wales").sum())
    R["n_with_coords"] = int(main.lat.notna().sum())
    R["n_without_coords"] = int(main.lat.isna().sum())
    R["n_matched_wikidata"] = int((main.qid != "").sum())
    R["n_wikidata_only"] = int((main.source == "Wikidata only").sum())
    R["n_year_from_wikidata"] = int(((main.dissolved_source == "Wikidata") & (main.source != "Wikidata only")).sum())
    R["list_rows_read"] = meta["list_rows"]
    R["list_rows_xref"] = meta["xref_rows"]
    R["list_rows_duplicates_merged"] = meta["duplicates_merged"]
    R["extraction_check"] = meta["extraction_check"]
    R["wikidata_ew_items"] = meta["wikidata_ew_items"]
    wd = json.load(open(os.path.join(ROOT, "work", "houses_all.json")))
    wde = [h for h in wd if h["nation"] in ("England", "Wales") and h.get("dissolved") and 1536 <= h["dissolved"] <= 1541]
    R["wikidata_dissolved_1536_1541"] = len(wde)
    R["wikidata_dissolved_order_known"] = sum(h["family"] != "Unknown" for h in wde)
    # coordinate agreement between list and Wikidata for matched houses
    wdq = {h["qid"]: h for h in wd}
    dists = []
    for _, r in main[(main.qid != "") & (main.coord_source == "Wikipedia list")].iterrows():
        w = wdq.get(r["qid"])
        if w:
            k = np.cos(np.radians(r["lat"]))
            dists.append(np.hypot((r["lat"] - w["lat"]) * 110.57, (r["lon"] - w["lon"]) * 111.32 * k))
    dists = np.array(dists)
    R["coord_check"] = dict(n=int(len(dists)), median_m=int(round(np.median(dists) * 1000)), share_within_500m=round(float(np.mean(dists < 0.5)), 3),
                            n_over_2km=int(np.sum(dists > 2)))
    R["benchmark"] = dict(wikipedia_england_houses="nearly 900", wikipedia_parish_church_survivals=117,
                          wikipedia_monastic_cathedrals=14, wikipedia_friaries="around 200")
    R["share_of_900"] = round(R["n_england"] / 900, 3)

    # dissolution timeline
    R["by_year"] = {str(int(y)): int(n) for y, n in main.dissolved.value_counts().sort_index().items()}
    R["by_year_order"] = {str(int(y)): {k: int(v) for k, v in g.order.value_counts().items()} for y, g in main.groupby("dissolved")}

    R["friars_1538"] = R["by_year_order"]["1538"].get("Friars", 0)
    R["benedictine_1539"] = R["by_year_order"]["1539"].get("Benedictine", 0)
    R["military_1540"] = R["by_year_order"]["1540"].get("Military orders", 0)
    R["domesday_located_places"] = int(pd.read_csv(os.path.join(os.path.dirname(ROOT), "domesday-destiny", "data", "domesday_places.csv"), usecols=["lat"]).lat.notna().sum())
    # orders
    R["by_order"] = {k: int(v) for k, v in main.order.value_counts().items()}
    R["by_group"] = {k: int(v) for k, v in main.group.value_counts().items()}
    R["order_source"] = {k: int(v) for k, v in main.order_source.replace("", "none").value_counts().items()}
    R["female_houses"] = int(main.female.sum())

    # afterlife
    ac = main.afterlife.value_counts()
    R["afterlife"] = {k: int(v) for k, v in ac.items()}
    R["afterlife_share"] = {k: round(v / len(main), 3) for k, v in ac.items()}
    known = main[~main.afterlife.isin(["unclear", "protected"])]
    R["afterlife_known_n"] = int(len(known))
    R["afterlife_known_share"] = {k: round(v / len(known), 3) for k, v in known.afterlife.value_counts().items()}
    standing = known.afterlife.isin(["cathedral", "monastic", "church", "house", "school", "farm", "other", "ruin"])
    R["standing_share_of_known"] = round(float(standing.mean()), 3)
    R["in_use_share_of_known"] = round(float(known.afterlife.isin(["cathedral", "monastic", "church", "house", "school", "farm", "other"]).mean()), 3)
    R["components_any"] = {c: int(main.components.apply(lambda x: c in x).sum()) for c in
                           ["cathedral", "monastic", "church", "house", "school", "farm", "other", "ruin", "earthworks", "nothing"]}
    R["afterlife_source"] = {k: int(v) for k, v in main.afterlife_source.value_counts().items()}
    R["cathedrals"] = sorted(main.loc[main.afterlife == "cathedral", "name"].tolist())
    R["monastic_again"] = sorted(main.loc[main.afterlife == "monastic", "name"].tolist())
    kn = main[main.kept_name != ""]
    R["kept_name_n"] = int(len(kn))
    R["kept_name_examples"] = sorted(kn.kept_name.tolist())
    R["kept_name_abbey_n"] = int(kn.kept_name.str.contains("Abbey").sum())
    R["kept_name_priory_n"] = int(kn.kept_name.str.contains("Priory").sum())
    R["house_n"] = int((main.afterlife == "house").sum())
    R["afterlife_by_order"] = {o: {k: int(v) for k, v in g.afterlife.value_counts().items()} for o, g in main.groupby("order")}
    R["afterlife_by_nation"] = {o: {k: int(v) for k, v in g.afterlife.value_counts().items()} for o, g in main.groupby("nation")}
    big = ["Benedictine", "Augustinian", "Cistercian", "Friars", "Premonstratensian", "Cluniac", "Gilbertine"]
    R["afterlife_known_share_by_order"] = {}
    for o in big:
        g = main[(main.order == o) & ~main.afterlife.isin(["unclear", "protected"])]
        R["afterlife_known_share_by_order"][o] = dict(n=int(len(g)), **{k: round(v / len(g), 3) for k, v in g.afterlife.value_counts().items()})

    # setting by group, Domesday area
    S = main[main.dom_area == True].copy()  # noqa: E712
    R["dom_area_n"] = int(len(S))
    R["baseline"] = dict(n_points=int(len(base)), n_counties=int(base.county.nunique()), median_hh5=float(base.hh5.median()),
                         median_dom_n5=float(base.dom_n5.median()), median_elev=round(float(base.elev_m.median()), 1),
                         median_relief=round(float(base.relief_m.median()), 1), median_river=float(base.river_m.median()))
    groups = ["Cistercian monks", "Cistercian nuns", "Benedictine monks", "Benedictine nuns", "Augustinian canons", "Augustinian canonesses",
              "Premonstratensian", "Cluniac", "Gilbertine", "Carthusian", "Friars", "Military orders"]
    R["setting"] = {}
    for gname in groups:
        g = S[S.group == gname]
        if len(g) < 5:
            continue
        R["setting"][gname] = dict(n=int(len(g)), hh5_median=float(g.hh5.median()), hh5_ci=boot_median(g.hh5),
                                   hh10_median=float(g.hh10.median()), dom_n5_median=float(g.dom_n5.median()),
                                   nn_km_median=round(float(g.dom_nn_km.median()), 2),
                                   pct_median=round(float(g.hh5_pct_county.median()), 1), pct_ci=boot_median(g.hh5_pct_county.dropna()),
                                   share_below_county_median=round(float((g.hh5_pct_county < 50).mean()), 3),
                                   elev_median=round(float(g.elev_m.median()), 1), relief_median=round(float(g.relief_m.median()), 1),
                                   river_median=float(g.river_m.median()))
    cm = S[S.group == "Cistercian monks"]
    bm = S[S.group == "Benedictine monks"]
    R["cist_vs_ben"] = dict(hh5_diff=float(cm.hh5.median() - bm.hh5.median()), hh5_diff_ci=boot_diff(cm.hh5, bm.hh5),
                            hh5_ratio=round(float(cm.hh5.median() / bm.hh5.median()), 3),
                            pct_diff=round(float(cm.hh5_pct_county.median() - bm.hh5_pct_county.median()), 1),
                            pct_diff_ci=boot_diff(cm.hh5_pct_county.dropna(), bm.hh5_pct_county.dropna()),
                            mannwhitney_p_hh5=float(mannwhitneyu(cm.hh5, bm.hh5).pvalue),
                            mannwhitney_p_pct=float(mannwhitneyu(cm.hh5_pct_county.dropna(), bm.hh5_pct_county.dropna()).pvalue),
                            elev_diff=round(float(cm.elev_m.median() - bm.elev_m.median()), 1),
                            share_cist_below_median=round(float((cm.hh5_pct_county < 50).mean()), 3),
                            share_cist_bottom_quarter=round(float((cm.hh5_pct_county < 25).mean()), 3),
                            share_ben_bottom_quarter=round(float((bm.hh5_pct_county < 25).mean()), 3))
    # regression with county fixed effects
    X = S[S.group.isin(groups)].copy()
    X["y"] = np.log1p(X.hh5)
    X["g"] = X.group
    m = smf.ols("y ~ C(g, Treatment('Benedictine monks')) + C(ons_county)", data=X).fit(cov_type="HC1")
    coefs = {}
    for k, v in m.params.items():
        if k.startswith("C(g"):
            name = k.split("[T.")[1].rstrip("]")
            lo, hi = m.conf_int().loc[k]
            coefs[name] = dict(pct_change=round(100 * (np.exp(v) - 1), 1), ci=[round(100 * (np.exp(lo) - 1), 1), round(100 * (np.exp(hi) - 1), 1)],
                               p=float(m.pvalues[k]))
    R["regression"] = dict(n=int(m.nobs), r2=round(float(m.rsquared), 3), reference="Benedictine monks", effects=coefs)
    # Yorkshire check (Harrying of the North depressed 1086 figures there)
    yk = S[S.ons_county.isin(["North Yorkshire", "West Yorkshire", "South Yorkshire", "East Riding of Yorkshire"])]
    nyk = S[~S.index.isin(yk.index)]
    R["yorkshire"] = {}
    for lab, part in (("Yorkshire", yk), ("Rest of England", nyk)):
        R["yorkshire"][lab] = {g: dict(n=int((part.group == g).sum()), pct_median=round(float(part[part.group == g].hh5_pct_county.median()), 1) if (part.group == g).sum() else None,
                                       hh5_median=float(part[part.group == g].hh5.median()) if (part.group == g).sum() else None)
                               for g in ["Cistercian monks", "Benedictine monks", "Augustinian canons", "Friars"]}
    # robustness: every listed house with coordinates and a known order in the Domesday area, any dissolution date
    A = H[(H.dom_area == True) & H.group.isin(groups)]  # noqa: E712
    R["robust_all_listed"] = {g: dict(n=int((A.group == g).sum()), pct_median=round(float(A[A.group == g].hh5_pct_county.median()), 1),
                                      hh5_median=float(A[A.group == g].hh5.median())) for g in ["Cistercian monks", "Benedictine monks", "Augustinian canons", "Premonstratensian", "Friars"]}
    # Wales: no Domesday, only terrain
    W = main[(main.nation == "Wales") & main.lat.notna()]
    R["wales_terrain"] = {g: dict(n=int((W.group == g).sum()), elev_median=round(float(W[W.group == g].elev_m.median()), 1),
                                  relief_median=round(float(W[W.group == g].relief_m.median()), 1))
                          for g in ["Cistercian monks", "Benedictine monks", "Augustinian canons", "Friars"] if (W.group == g).sum() >= 3}
    # local houses
    R["local"] = {}
    for n in ["Whalley Abbey", "Sawley Abbey"]:
        r = main[main.name == n].iloc[0]
        R["local"][n] = dict(order=r["group"], dissolved=int(r["dissolved"]), afterlife=r["afterlife_label"], evidence=r["afterlife_evidence"],
                             hh5=float(r["hh5"]), hh10=float(r["hh10"]), dom_n5=int(r["dom_n5"]), nn_km=float(r["dom_nn_km"]),
                             pct=float(r["hh5_pct_county"]), county=r["ons_county"], elev=float(r["elev_m"]), relief=float(r["relief_m"]),
                             river_m=float(r["river_m"]), lat=float(r["lat"]), lon=float(r["lon"]), dissolved_text=r["dissolved_text"],
                             later=r["later"], orders=r["orders_text"])
    R["local"]["lancashire_baseline_points"] = 0  # Lancashire is outside the household comparison
    lan = main[(main.ons_county == "Lancashire")]
    au = pd.read_csv(os.path.join(ROOT, "data", "audit_sample.csv"))
    R["audit"] = dict(n=int(len(au)), consistent=int(au.judged_consistent.sum()), seed=1540,
                      earlier_rounds="two earlier samples of 40 (35 and 36 judged consistent) were used to refine the rules")
    R["list_rows_no_year"] = int(((H.source != "Wikidata only") & H.dissolved.isna()).sum())
    w_, s_ = R["local"]["Whalley Abbey"], R["local"]["Sawley Abbey"]
    R["local"]["distance_km"] = round(float(np.hypot((w_["lat"] - s_["lat"]) * 110.57, (w_["lon"] - s_["lon"]) * 111.32 * np.cos(np.radians(53.87)))), 1)
    R["local_notes"] = json.load(open(os.path.join(ROOT, "data", "local_notes.json")))
    R["local"]["lancashire_houses"] = sorted(lan.name.tolist())
    # extremes: emptiest and busiest settings among abbeys of monks/canons
    ab = S[S.group.isin(["Cistercian monks", "Benedictine monks", "Augustinian canons", "Premonstratensian", "Cluniac"])].sort_values("hh5")
    R["emptiest"] = [dict(name=r["name"], group=r["group"], hh5=float(r["hh5"])) for _, r in ab.head(8).iterrows()]
    R["busiest"] = [dict(name=r["name"], group=r["group"], hh5=float(r["hh5"])) for _, r in ab.tail(5).iloc[::-1].iterrows()]

    # files
    cols = ["id", "name", "county", "ons_county", "nation", "lat", "lon", "coord_source", "order", "group", "female", "orders_text",
            "dissolved", "dissolved_source", "dissolved_text", "mark", "later", "afterlife", "afterlife_label", "components", "afterlife_evidence",
            "afterlife_source", "kept_name", "qid", "enwiki", "source", "source_page"]
    out = main[cols].copy()
    out["components"] = out.components.apply(lambda x: ";".join(x))
    out.to_csv(os.path.join(ROOT, "data", "houses.csv"), index=False)
    setc = ["id", "name", "group", "ons_county", "dom_area", "dom_nn_km", "dom_n5", "hh5", "hh10", "hh5_pct_county", "elev_m", "relief_m", "river_m"]
    main[main.lat.notna()][setc].to_csv(os.path.join(ROOT, "data", "house_settings.csv"), index=False)
    feats = []
    for _, r in main[main.lat.notna()].iterrows():
        feats.append(dict(type="Feature", geometry=dict(type="Point", coordinates=[round(r.lon, 5), round(r.lat, 5)]),
                          properties=dict(id=r["id"], name=r["name"], order=r["order"], group=r["group"], dissolved=int(r["dissolved"]),
                                          afterlife=r["afterlife"], afterlife_label=r["afterlife_label"])))
    json.dump(dict(type="FeatureCollection", features=feats), open(os.path.join(ROOT, "data", "houses.geojson"), "w"), ensure_ascii=False)
    json.dump(R, open(os.path.join(ROOT, "data", "results.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: R[k] for k in ["n_houses", "afterlife", "afterlife_known_share", "cist_vs_ben", "regression", "yorkshire", "robust_all_listed", "local", "coord_check", "kept_name_n"]}, indent=1)[:6000])
    print(json.dumps(R["setting"], indent=0)[:3000])


if __name__ == "__main__":
    main()
