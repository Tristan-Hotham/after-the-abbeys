"""Step 3. Build the house table: join the Wikipedia list rows to Wikidata, assign each
house an order family and an "afterlife" class, and keep the houses dissolved 1536 to 1541.

Inputs: work/list_rows.json (step 2), work/houses_all.json (step 1),
        _data2/wikipedia_link_coords.json (coordinates of Wikipedia articles by title).
Output: work/houses_built.json (all deduplicated list rows plus Wikidata-only houses,
        with order, afterlife and match fields). Step 4 adds the setting measures.

Rules are written out in full below and in README.md.
Run: python3 code/03_build.py
"""
import json
import math
import os
import re
from collections import Counter
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKC = "/home/claude/hist/_data2/wikipedia_link_coords.json"

GENERIC = set("""abbey priory friary friars friar monastery nunnery cell cells grange preceptory camera commandery
of the st saint st. and at in near nr earlier site possible church cathedral house minster college hospital
blackfriars greyfriars whitefriars austin augustinian dominican franciscan carmelite crutched sack pied
abbey, priory, (?) ? the. new old great little holy trinity mary s mary's""".split())

# ---------------------------------------------------------------- order family
FRIAR_WORDS = r"friar|trinitarian|crouched|crutched|friars of the sack|pied friars|bethlehemite|penitent|friary"
# segments that describe a post-Reformation refoundation, ignored when choosing the order at dissolution
MODERN = r"anglican|orthodox|capuchin|society of|servite|sisters of the sacred|recollect|windesheim|community of|chemin|minoresses .* 19|19\d\d|20\d\d"


def family_of_segment(seg):
    s = seg.lower()
    if re.search(MODERN, s):
        return None
    if re.search(r"templar|hospitaller|st\.? john of jerusalem|lazar", s):
        return "Military orders"
    if re.search(FRIAR_WORDS, s):
        return "Friars"
    if re.search(r"cisterc|savign|sauvign|trappist", s):
        return "Cistercian"
    if re.search(r"carthusian|charterhouse", s):
        return "Carthusian"
    if re.search(r"premonstrat", s):
        return "Premonstratensian"
    if re.search(r"gilbertine", s):
        return "Gilbertine"
    if re.search(r"cluniac", s):
        return "Cluniac"
    if re.search(r"augustin|austin canons|arroas|victorine|black canons|bonshommes|canons regular", s):
        return "Augustinian"
    if re.search(r"benedictine|black monks", s):
        return "Benedictine"
    if re.search(r"tironensian|grandmont|fontevrault|fontévrault|fontefralt|bridget|brigittine|bridgettine", s):
        return "Other orders"
    return None


def order_family(orders_text):
    segs = [x.strip() for x in re.split(r";|\band\b(?= [A-Z])", orders_text or "") if x.strip()]
    fams = [f for f in (family_of_segment(s) for s in segs) if f]
    if not fams:
        return None, False
    female = bool(re.search(r"\bnuns?\b|canoness|sisters|abbess|prioress", (orders_text or "").lower())) and not re.search(r"monks|canons\b|friars", segs[-1].lower() if segs else "")
    return fams[-1], female


WD_FAMILY = {"Cistercian": "Cistercian", "Benedictine": "Benedictine", "Cluniac": "Cluniac", "Augustinian": "Augustinian",
             "Premonstratensian": "Premonstratensian", "Gilbertine": "Gilbertine", "Carthusian": "Carthusian",
             "Friars": "Friars", "Military orders": "Military orders", "Other": "Other orders"}

# ---------------------------------------------------------------- afterlife
NEG = r"now ruined|closed|until|demolish|destroyed|ruinous|disuse|redundant|no longer|possibly|purportedly|possible|apparently|alleged|supposedly|hypothesis|reputedly|briefly|became ruinous|later called|1540–1550|in precinct|decay|died out"
GRANT = r"^\s*(granted|given|alienated|annexed|sold|leased|passed|purchased|held|reverted|restored to|briefly|transferred|refounded as)"
R = {
    "cathedral": r"cathedral",
    "church": r"parochial|parish church|parish chapel|in use as (a |the )?(parish )?church|royal peculiar|priory church of|church now in|church in use|church .* in use|chapel now|in use as chapel|place of worship|church continues|conventual church .* parish|nave .* parish|built on site.*church|church .* built on (the )?site|incorporated into .*church|church of st .* on site|current church",
    "house": r"mansion|country house|house named|private house|manor house|house built|houses? (called|built)|incorporated into (a |the )?(later |private )?(house|residence)|converted into (a )?(manor )?house|private residence|secular residence|residence|stately home|\bhall\b built|'[^']*\b(hall|house|court|abbey|priory|park|place|manor|friary|friarage|grange|nunnery|cottage)'|built on (the )?site .* house|house (and|built|on site)|hotel|in use as a dwelling|divided up as private housing|incorporated into houses|residences in|occupied by (a |an )?([\w-]+ )?house\b|vicarage|rectory",
    "school": r"school|college (built|founded)|college\b.*on site|university|grammar school|education|refounded .*college|part of christ church",
    "farm": r"farm|barn|grange",
    "other": r"museum|public house|\binn\b|restaurant|shopping|car park|hospital|prison|gaol|nightclub|warehouse|station|offices|almshouse|cinema|distillery|golf|superstore|cattlemarket|police|(?<![a-z])works\b|meditation|facilities|retreat|conference|exhibition|brewery|nursing home|theatre|workhouse|register office|headquarters|storehouse|industrial|concert|now [\w ]*\bhall\b",
    "ruin": r"\(eh\)|\beh\b|\(nt\)|\bnt\b|cadw|\(lt\)|english heritage|ruin|remains (now )?(extant|visible|within)|gatehouse remains|walled garden|public park|ruins extant|in the care of|guardianship|open to public|with public access|monument|priory remains|abbey remains",
    "earthworks": r"earthwork|cropmark",
    "nothing": r"no (substantial |identifiable |visible )?(remains|trace)|nothing .* visible|submerged|beneath the sea|destroyed by the sea|destroyed by coastal|built over|housing estate|few visible remains|nothing of the|beneath the ground|demolished|destroyed|no longer exists|site now occupied by",
}
ORDER = ["cathedral", "monastic", "church", "house", "school", "farm", "church_site", "other", "ruin", "earthworks", "nothing", "protected"]
LABEL = {"cathedral": "Cathedral", "monastic": "Monastery again", "church": "Church", "house": "House or hotel", "school": "School or college",
         "farm": "Farm", "other": "Other use", "ruin": "Ruin", "earthworks": "Earthworks only",
         "nothing": "Nothing visible", "protected": "Protected, use unrecorded", "unclear": "Unclear"}


def clause_hits(later, mark, name):
    """Return the set of afterlife components found, and the clause that set each one."""
    hits, why = set(), {}
    clauses = [c.strip() for c in re.split(r"\s/\s|;", later or "") if c.strip()]
    # a bare "demolished ..." clause cancels the clause before it ("house built on site / demolished 1863")
    clauses = [c for i, c in enumerate(clauses)
               if not (i + 1 < len(clauses) and re.match(r"(and )?(demolished|destroyed)", clauses[i + 1].lower()))]
    for c in clauses:
        cl = c.lower()
        if re.search(GRANT, cl) and not re.search(r"/|now|currently|built|incorporat|converted|site", cl[12:]):
            continue
        neg = re.search(NEG, cl) and not re.search(r"rebuilt|restored", cl)
        if re.search(r"in use as (a )?barn", cl) and not neg:
            hits.add("farm"); why.setdefault("farm", c)
            continue
        if "farmhouse" in cl and not re.search(r"mansion|country house", cl) and not neg:
            hits.add("farm"); why.setdefault("farm", c)
            continue
        if re.search(r"incorporated into [A-Z][\w']+ (Court|Hall|House|Place|Manor|Park)|[A-Z][\w']+ (Court|Hall|House|Manor) built", c) and not neg:
            hits.add("house"); why.setdefault("house", c)
        historic = re.search(r"\b1[0-8]\d\d\b", cl) and not re.search(r"now|current|extant|present|today|built|founded|on (the )?site|occup", cl)
        for k in ["cathedral", "church", "house", "school", "farm", "other"]:
            if re.search(R[k], cl):
                if k == "cathedral" and (neg or not re.search(r"extant|present|founded|in use", cl) or re.search(r"demolish|decay", (later or "").lower())):
                    continue
                if k in ("school", "other") and historic:
                    continue
                if k == "church" and re.search(r"built", cl) and not re.search(r"incorporat|nave|conventual|priory church|monastic|remains", cl):
                    hits.add("church_site"); why.setdefault("church_site", c)
                    continue
                if k in ("church", "house", "school", "farm", "other") and neg:
                    continue
                if k == "house" and re.search(r"farmhouse|public house|almshouse|warehouse|workhouse|meeting house|guest-house|house of|storehouse|houses called 'the friars'", cl) and not re.search(r"mansion|country house|house named|private house|manor house", cl):
                    if "farmhouse" in cl:
                        hits.add("farm"); why.setdefault("farm", c)
                    if re.search(r"public house|warehouse|workhouse|storehouse", cl):
                        hits.add("other"); why.setdefault("other", c)
                    continue
                if k == "school" and re.search(r"granted to .*college|college, (cambridge|oxford) 1|eton college|winchester college|king's college|new college|queen's college|god's house|magdalen college|pembroke|st john's college|trinity college, cambridge 1|wolsey|cardinal", cl):
                    continue
                if k == "farm" and re.search(r"granted|grange of|grange by|status of a grange|retained for use as grange", cl):
                    continue
                hits.add(k); why.setdefault(k, c)
        if re.search(R["ruin"], cl) and not re.search(r"possibly|beneath the ground|incorporate|thoroughly destroyed|remains demolished|no remains|ruinous before|became ruinous|ruined by|now ruined|ruins of previous|considerable remains' existing", cl):
            hits.add("ruin"); why.setdefault("ruin", c)
        if re.search(R["earthworks"], cl):
            hits.add("earthworks"); why.setdefault("earthworks", c)
        if re.search(R["nothing"], cl) and not re.search(r"remains (now )?incorporated|remains visible|ruins extant|apart from", cl):
            hits.add("nothing"); why.setdefault("nothing", c)
    if "+" in mark:
        if "cathedral" in name.lower():
            hits.add("cathedral"); why.setdefault("cathedral", "list mark + on a cathedral priory")
        else:
            hits.add("church"); why.setdefault("church", "list mark +")
    if "$" in mark:
        hits.add("earthworks"); why.setdefault("earthworks", "list mark $")
    if "#" in mark:
        hits.add("nothing"); why.setdefault("nothing", "list mark #")
    if "*" in mark:
        hits.add("monastic"); why.setdefault("monastic", "list mark * (current monastic use)")
    return hits, why


def afterlife(row, wd):
    hits, why = clause_hits(row.get("later", ""), row.get("mark", ""), row.get("name", ""))
    src = "list"
    if wd:
        types = set(wd.get("types", []))
        if "monastery ruins" in types:
            hits.add("ruin"); why.setdefault("ruin", "Wikidata: instance of monastery ruins")
        if "destroyed monastery" in types and not hits:
            hits.add("nothing"); why.setdefault("nothing", "Wikidata: instance of destroyed monastery")
    # a site with standing remains of any kind is not 'nothing visible'
    if "nothing" in hits and hits & {"church", "house", "school", "farm", "ruin", "cathedral", "other", "church_site"}:
        hits.discard("nothing")
    if "earthworks" in hits and hits & {"ruin"}:
        hits.discard("earthworks")
    primary = next((k for k in ORDER if k in hits), "unclear")
    if primary == "unclear" and "^" in row.get("mark", ""):
        primary = "other"; why["other"] = "list mark ^ (non-church use) with no further detail"
    if primary == "unclear" and wd and set(wd.get("heritage", [])) & set(HERITAGE):
        primary, src = "protected", "wikidata"
        why["protected"] = "Wikidata: " + ", ".join(HERITAGE[q] for q in wd["heritage"] if q in HERITAGE)
    reason = why.get(primary, "")
    if primary == "church_site":
        primary = "church"
    return primary, sorted(h.replace("church_site", "church") for h in hits), reason, src


HERITAGE = {"Q219538": "scheduled monument", "Q15700818": "Grade I listed building",
            "Q15700831": "Grade II* listed building", "Q15700834": "Grade II listed building"}
KEPT = re.compile(r"'((?:[^']|'(?=s\b))*\b(Abbey|Priory|Friary|Friarage|Nunnery|Friars|Temple)\b(?:[^']|'(?=s\b))*)'")


def kept_name(later):
    m = KEPT.search(later or "")
    if m:
        return m.group(1)
    m = re.search(r"\b([A-Z][a-z]+ (Abbey|Priory)) (House|built)", later or "")
    return m.group(1) if m else ""


# ---------------------------------------------------------------- matching
def toks(name):
    n = re.sub(r"[^a-z' ]", " ", name.lower().replace("—", " ").replace("-", " "))
    return {t.strip("'") for t in n.split() if t.strip("'") and t.strip("'") not in GENERIC and len(t.strip("'")) > 2}


def normname(x):
    return re.sub(r"[^a-z]+", " ", x.lower()).strip()


def fuzzy(a, b):
    n = lambda x: " ".join(sorted(toks(x))) or x.lower()
    return SequenceMatcher(None, n(a), n(b)).ratio()


def km(a, b, c, d):
    k = math.cos(math.radians((a + c) / 2))
    return math.hypot((a - c) * 110.57, (b - d) * 111.32 * k)


def main():
    L = json.load(open(os.path.join(ROOT, "work", "list_rows.json")))
    rows = [r for r in L["rows"] if r["orders"] != "XREF"]
    wd_all = [h for h in json.load(open(os.path.join(ROOT, "work", "houses_all.json"))) if h["nation"] in ("England", "Wales")]
    linkc = json.load(open(LINKC))["coords"]
    for h in wd_all:
        h["title"] = (h.get("enwiki") or "").rsplit("/", 1)[-1].replace("_", " ")
    by_title = {h["title"]: h for h in wd_all if h["title"]}

    # fill missing list coordinates: Wikidata item with the same title or name, else Wikipedia article coordinates
    for r in rows:
        r["coord_source"] = "Wikipedia list" if r["lat"] is not None else ""
        if r["lat"] is None:
            for key in [r.get("link", ""), r["name"]]:
                if key in by_title:
                    r["lat"], r["lon"], r["coord_source"] = by_title[key]["lat"], by_title[key]["lon"], "Wikidata (same article)"
                    break
                if key in linkc:
                    r["lat"], r["lon"], r["coord_source"] = linkc[key][0], linkc[key][1], "Wikipedia article coordinates"
                    break
    for r in rows:
        if r["lat"] is None:
            full = lambda h: SequenceMatcher(None, normname(r["name"]), normname(h["name"])).ratio()
            best = max(wd_all, key=full)
            if full(best) >= 0.9:
                r["lat"], r["lon"], r["coord_source"] = best["lat"], best["lon"], "Wikidata (name match)"
    # deduplicate list rows that appear under two counties or twice in one list
    keep = []
    for r in rows:
        dup = None
        for k in keep:
            if "earlier site" in (r["name"] + k["name"]).lower():
                continue
            if r["lat"] is not None and k["lat"] is not None and km(r["lat"], r["lon"], k["lat"], k["lon"]) < 1.0 and (normname(r["name"]) == normname(k["name"]) or SequenceMatcher(None, normname(r["name"]), normname(k["name"])).ratio() >= 0.9) and family_of_segment(r["orders"] or "x") == family_of_segment(k["orders"] or "x"):
                if (r["dissolved_year"] == k["dissolved_year"]) or not r["dissolved_year"] or not k["dissolved_year"]:
                    dup = k
                    break
            if r["name"] == k["name"] and r["lat"] is None:
                dup = k
                break
        if dup is None:
            keep.append(r)
        else:
            for f in ("later", "orders", "dissolved_text"):
                if len(r.get(f) or "") > len(dup.get(f) or ""):
                    dup[f] = r[f]
            dup["mark"] = "".join(sorted(set(dup["mark"]) | set(r["mark"])))
            dup["dissolved_year"] = dup["dissolved_year"] or r["dissolved_year"]
    n_dups = len(rows) - len(keep)
    rows = keep

    # match list rows to Wikidata items one to one: score every plausible pair, then take pairs best first
    pairs = []
    for i, r in enumerate(rows):
        r["qid"] = ""
        r["match_name"] = False
        for h in wd_all:
            if r.get("link") and h["title"] == r.get("link"):
                pairs.append((-10, i, h["qid"], True))
                continue
            if r["lat"] is None:
                if h["name"].lower() == r["name"].lower():
                    pairs.append((-5, i, h["qid"], True))
                continue
            d = km(r["lat"], r["lon"], h["lat"], h["lon"])
            if d > 3:
                continue
            share = len(toks(r["name"]) & toks(h["name"]))
            if share > 0:
                pairs.append((d - 2 * share, i, h["qid"], True))
            elif d < 0.4 and (set(r["name"].lower().split()) & set(h["name"].lower().split())) - {"st", "the", "of", "priory", "abbey"}:
                pairs.append((d, i, h["qid"], False))
    pairs.sort()
    used, done = set(), set()
    for sc, i, q, byname in pairs:
        if i in done or q in used:
            continue
        rows[i]["qid"], rows[i]["match_name"] = q, byname
        done.add(i)
        used.add(q)
    wd_by_q = {h["qid"]: h for h in wd_all}

    out = []
    for r in rows:
        wd = wd_by_q.get(r["qid"])
        fam, female = order_family(r["orders"])
        fam_src = "Wikipedia list"
        if fam is None and r["name"]:
            nm = r["name"].lower()
            if re.search(r"blackfriars|greyfriars|whitefriars|austin friar|friary|crutched|trinitarian", nm):
                fam, fam_src = "Friars", "name"
            elif re.search(r"preceptory|commandery|camera\b|temple", nm):
                fam, fam_src = "Military orders", "name"
            elif re.search(r"charterhouse", nm):
                fam, fam_src = "Carthusian", "name"
        if fam is None and wd and wd["family"] not in ("Unknown",):
            fam, fam_src = WD_FAMILY[wd["family"]], "Wikidata"
        yr = r["dissolved_year"]
        yr_src = "Wikipedia list" if yr else ""
        if (not yr and wd and wd.get("dissolved") and r["match_name"] and "*" not in r["mark"]
                and "earlier site" not in r["name"].lower() and not r["dissolved_text"] and "~" not in r["mark"]
                and "?" not in r["name"] and fam is not None and fam_src == "Wikipedia list"
                and not re.search(r"saxon|celtic|pre-conquest|minster|uncertain", (r["orders"] or "").lower())
                and SequenceMatcher(None, normname(r["name"]), normname(wd["name"])).ratio() >= 0.75
                and not re.search(r"^old |earlier|nunnery|\?", r["name"].lower())):
            yr, yr_src = wd["dissolved"], "Wikidata"
        prim, comps, reason, asrc = afterlife(r, wd)
        out.append(dict(name=r["name"], county=r["county"], nation=r["nation"], lat=r["lat"], lon=r["lon"],
                        coord_source=r["coord_source"] or ("Wikidata" if wd else ""), coord_quality=r.get("coord_quality", ""),
                        order=fam or "Unknown", order_source=fam_src if fam else "", female=female,
                        orders_text=r["orders"], dissolved=yr, dissolved_source=yr_src, dissolved_text=r["dissolved_text"],
                        mark=r["mark"], later=r["later"], afterlife=prim, afterlife_label=LABEL[prim], components=comps,
                        afterlife_evidence=reason, afterlife_source=asrc, kept_name=kept_name(r["later"]) if prim == "house" else "",
                        qid=r["qid"], wikidata_types=wd["types"] if wd else [], heritage=wd["heritage"] if wd else [],
                        enwiki=(wd or {}).get("enwiki") or "", source=r["source"], source_page=r["source_page"]))
    # a Wikidata year is not borrowed by a row that sits on the site of a listed house with a stated year
    for r in out:
        if r["dissolved_source"] == "Wikidata" and r["lat"] is not None and any(
                o is not r and o["lat"] is not None and o["dissolved_source"] == "Wikipedia list" and o["dissolved"]
                and 1536 <= o["dissolved"] <= 1541 and km(o["lat"], o["lon"], r["lat"], r["lon"]) < 0.3 for o in out):
            r["dissolved"], r["dissolved_source"] = None, ""
    # Wikidata-only houses dissolved 1536 to 1541 that match no list row
    extra = 0
    for h in wd_all:
        if h["qid"] in used or not h.get("dissolved") or not (1536 <= h["dissolved"] <= 1541):
            continue
        near = [o for o in out if (o["lat"] is not None and km(o["lat"], o["lon"], h["lat"], h["lon"]) < 3.0
                                   and (toks(o["name"]) & toks(h["name"]) or fuzzy(o["name"], h["name"]) >= 0.6
                                        or km(o["lat"], o["lon"], h["lat"], h["lon"]) < 0.5))
                or (o["lat"] is None and fuzzy(o["name"], h["name"]) >= 0.75)
                or (o["lat"] is not None and km(o["lat"], o["lon"], h["lat"], h["lon"]) < 30 and fuzzy(o["name"], h["name"]) >= 0.8)
                or (o["lat"] is not None and km(o["lat"], o["lon"], h["lat"], h["lon"]) < 100 and toks(o["name"]) and toks(o["name"]) <= toks(h["name"]) | toks(o["name"]) and toks(h["name"]) <= toks(o["name"]))]
        if near:
            for o in near:
                if not o["qid"]:
                    o["qid"] = h["qid"]
            continue
        prim, comps, reason, asrc = afterlife(dict(later="", mark="", name=h["name"]), h)
        extra += 1
        out.append(dict(name=h["name"], county=h["county"], nation=h["nation"], lat=h["lat"], lon=h["lon"], coord_source="Wikidata",
                        coord_quality="", order=WD_FAMILY.get(h["family"], "Unknown"), order_source="Wikidata" if h["family"] != "Unknown" else "",
                        female=any("nun" in t for t in h["types"]), orders_text="; ".join(h["orders"]), dissolved=h["dissolved"],
                        dissolved_source="Wikidata", dissolved_text="", mark="", later="", afterlife=prim, afterlife_label=LABEL[prim],
                        components=comps, afterlife_evidence=reason, afterlife_source="wikidata", kept_name="", qid=h["qid"],
                        wikidata_types=h["types"], heritage=h["heritage"], enwiki=h.get("enwiki") or "", source="Wikidata only",
                        source_page=""))
    meta = dict(list_rows=len(L["rows"]), xref_rows=sum(r["orders"] == "XREF" for r in L["rows"]), duplicates_merged=n_dups,
                wikidata_only_added=extra, extraction_check=L["extraction_check"], wikidata_ew_items=len(wd_all))
    json.dump(dict(houses=out, meta=meta), open(os.path.join(ROOT, "work", "houses_built.json"), "w"), ensure_ascii=False, indent=0)
    D = [o for o in out if o["dissolved"] and 1536 <= o["dissolved"] <= 1541]
    print(meta)
    print("main set", len(D), Counter(o["nation"] for o in D), "coords", sum(o["lat"] is not None for o in D), "matched wd", sum(bool(o["qid"]) for o in D))
    print(Counter(o["order"] for o in D).most_common())
    print(Counter(o["afterlife"] for o in D).most_common())


if __name__ == "__main__":
    main()
