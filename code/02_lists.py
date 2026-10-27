"""Step 2. Read the Wikipedia county lists of monastic houses into one table.

Sources (all English Wikipedia, CC BY-SA 4.0):
  * England: the 46 county pages "List of monastic houses in <county>" (all
    except the Isle of Wight, which could not be fetched). Only GitHub is
    reachable from the analysis machine, so each page was read with a web
    reader that returns text, with an instruction to copy, row by row, the
    foundation name, the status mark after the name, the bold community
    names, the words after "dissolved", every later-use clause verbatim and
    the coordinates. The returned lines are stored in data/wikipedia_lists/<County>.txt
    (lightly tidied by hand: separators and dashes in names only).
  * Wales and Lancashire: parsed here directly from the raw wikitext in
    _data2/wikipedia_wikitext.json. Lancashire is therefore available both
    ways and is used to check the reader (see results: extraction_check).

Output: work/list_rows.json, one record per table row.
Run: python3 code/02_lists.py
"""
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WT = "/home/claude/hist/_data2/wikipedia_wikitext.json"
MARKS = set("+^$#~*≈")


def parse_coord(s):
    s = (s or "").strip()
    m = re.search(r"(-?\d+(?:\.\d+)?)°\s*([NS])\s+(-?\d+(?:\.\d+)?)°\s*([EW])", s)
    if m:
        lat = float(m.group(1)) * (1 if m.group(2) == "N" else -1)
        lon = float(m.group(3)) * (1 if m.group(4) == "E" else -1)
        return lat, lon, ("approx" if re.search(r"approx|possible|supposed|purported|alleged|probable|poss\.|suggested|not known", s) else "")
    m = re.search(r"(-?\d{2}\.\d+)\s*,\s*(-?\d+\.\d+)", s)
    if m:
        return float(m.group(1)), float(m.group(2)), ""
    return None, None, ""


def parse_fetch_file(path):
    county = os.path.basename(path)[:-4].replace("_", " ")
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip() or "##" not in line:
            continue
        f = [x.strip() for x in line.split("##")]
        name = f[0]
        rest = f[1:]
        coord = ""
        if rest and ("°" in rest[-1] or re.search(r"\d+\.\d+\s*,\s*-?\d+\.\d+", rest[-1])):
            coord = rest.pop()
        while len(rest) < 4:
            rest.append("")
        mark, orders, diss, later = rest[0], rest[1], rest[2], " / ".join(x for x in rest[3:] if x)
        if mark and not set(mark.replace("(?)", "").replace("/", "").replace("(", "").replace(")", "").replace(" ", "")) <= MARKS:
            # mark column holds text: shift right
            orders, diss, later, mark = mark, orders, " / ".join(x for x in [diss, later] if x), ""
        lat, lon, cq = parse_coord(coord)
        out.append(dict(county=county, nation="England", name=name.strip(" *"), mark="".join(c for c in mark if c in MARKS),
                        orders=orders.strip('"'), dissolved_text=diss.strip('"'), later=later.replace('"', ""),
                        lat=lat, lon=lon, coord_quality=cq, source="Wikipedia county list (read via web reader)",
                        source_page="List of monastic houses in " + ("the " if county in ("East Riding of Yorkshire", "West Midlands") else "") + county))
    return out


def clean_wt(s):
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"\[\[(?:File|Image):[^\]]*\]\]", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{(?:nowrap|lang)\|(?:[a-z]+\|)?([^}]*)\}\}", r"\1", s)
    s = s.replace("&nbsp;", " ").replace("''", "")
    return s


def parse_raw(title, county_of=None):
    w = json.load(open(WT))[title]["wt"]
    # location-map coordinates by label, used when a row lacks {{coord}}
    lm = {}
    for m in re.finditer(r"\{\{Location map~[^}]*?lat=(-?[\d.]+)\|long=(-?[\d.]+)[^}]*?link=([^|}]+)", w):
        lm[m.group(3).strip()] = (float(m.group(1)), float(m.group(2)))
    county = None
    out = []
    for part in re.split(r"\n(?====)", w):
        h = re.match(r"===\s*\[?\[?([^\]=]+?)\]?\]?\s*===", part)
        if h:
            county = h.group(1).strip()
        for blk in re.split(r"\n\|-[^\n]*\n", part)[1:]:
            lines = blk.split("\n")
            first = lines[0]
            if not first.startswith("|") or first.startswith("|}") or first.startswith("|+") or first.startswith("|-"):
                continue
            cell = first[1:]
            body = "\n".join(lines[1:])
            if "colspan" in body[:300]:
                orders = "XREF"
            else:
                orders = None
            mk = re.search(r"<sup>\s*([^<]*)</sup>", cell)
            mark = "".join(c for c in (mk.group(1) if mk else "") if c in MARKS)
            link = re.search(r"\[\[([^|\]#]+)", cell)
            name = clean_wt(re.sub(r"<sup>.*?</sup>", "", cell)).strip()
            if not name or name.startswith("!"):
                continue
            cells = re.split(r"\n\|", "\n" + body)
            prov = cells[2] if len(cells) > 2 else ""
            if orders is None:
                orders = "; ".join(re.findall(r"'''([^']+)'''", prov))
            ptxt = clean_wt(prov).replace("<br />", "; ").replace("<br/>", "; ").replace("<br>", "; ")
            ptxt = re.sub(r"<[^>]+>", "", ptxt)
            dm = re.search(r"dissolved\.?\s*([^;]*)", ptxt)
            diss = dm.group(1).strip() if dm else ""
            later = ""
            if dm:
                later = " / ".join(x.strip() for x in ptxt[dm.end():].split(";") if x.strip())
            cm = re.search(r"\{\{coord\|(-?[\d.]+)\|(-?[\d.]+)", body)
            if cm:
                lat, lon = float(cm.group(1)), float(cm.group(2))
            elif link and link.group(1).strip() in lm:
                lat, lon = lm[link.group(1).strip()]
            else:
                lat = lon = None
            out.append(dict(county=county_of or county, nation="Wales" if "Wales" in title else "England", name=name,
                            mark=mark, orders=orders, dissolved_text=diss, later=later, lat=lat, lon=lon, coord_quality="",
                            link=link.group(1).strip() if link else "", source="Wikipedia list (raw wikitext)", source_page=title))
    return out


def year_of(text):
    ys = [int(y) for y in re.findall(r"(?<!\d)(1[0-9]{3})(?!\d)", text or "")]
    if not ys:
        return None
    inwin = [y for y in ys if 1530 <= y <= 1545]
    return inwin[0] if inwin else ys[0]


def main():
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "wikipedia_lists", "*.txt"))):
        if os.path.basename(p) == "Lancashire.txt":
            continue
        rows += parse_fetch_file(p)
    rows += parse_raw("List of monastic houses in Lancashire", county_of="Lancashire")
    wales = parse_raw("List of monastic houses in Wales")
    rows += wales
    for r in rows:
        r["dissolved_year"] = year_of(r["dissolved_text"])
    # extraction check: reader output for Lancashire against the raw wikitext
    fetched = {r["name"]: r for r in parse_fetch_file(os.path.join(ROOT, "data", "wikipedia_lists", "Lancashire.txt"))}
    raw = {r["name"]: r for r in rows if r["county"] == "Lancashire"}
    common = sorted(set(fetched) & set(raw))
    chk = dict(rows_raw=len(raw), rows_reader=len(fetched), matched_names=len(common),
               same_mark=sum(fetched[n]["mark"] == raw[n]["mark"] for n in common),
               same_year=sum(year_of(fetched[n]["dissolved_text"]) == raw[n]["dissolved_year"] for n in common),
               same_first_order=sum((fetched[n]["orders"].split(";")[0].strip().lower()[:12] == raw[n]["orders"].split(";")[0].strip().lower()[:12]) for n in common))
    json.dump(dict(rows=rows, extraction_check=chk), open(os.path.join(ROOT, "work", "list_rows.json"), "w"), ensure_ascii=False, indent=0)
    from collections import Counter
    print(len(rows), "rows;", Counter(r["nation"] for r in rows))
    print("with coords", sum(r["lat"] is not None for r in rows))
    print("check", chk)
    d = [r for r in rows if r["dissolved_year"] and 1536 <= r["dissolved_year"] <= 1541]
    print("dissolved 1536-1541:", len(d), Counter(r["nation"] for r in d), "with coords", sum(r["lat"] is not None for r in d))
    print(Counter(r["dissolved_year"] for r in rows if r["dissolved_year"] and 1520 <= r["dissolved_year"] <= 1560).most_common())


if __name__ == "__main__":
    main()
