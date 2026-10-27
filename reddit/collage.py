"""r/dataisbeautiful collage: What became of the abbeys? (2400 x 3000 px)
Run: python3 reddit/collage.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "code"))
from figlib import (AFTER_COL, DISP, FG, MONO, MOSS, MUT, ORDER_COL, SER, bng, land, plt)  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path  # noqa: E402

BG = "#EEEBE3"
STONE = "#8A8F86"
SLATE = "#3E4752"
WARM = "#B5532A"
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
H = pd.read_csv(os.path.join(ROOT, "data", "houses.csv")).dropna(subset=["lat"])
H["x"], H["y"] = bng(H.lon.values, H.lat.values)
S = pd.read_csv(os.path.join(ROOT, "data", "house_settings.csv"))

fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BG)

# ---------------- title
fig.text(0.045, 0.972, "What became of the abbeys?", fontproperties=DISP, fontsize=50, color=FG, va="top")
fig.text(0.045, 0.918, f"Henry VIII closed the monasteries of England and Wales between 1536 and 1540. I traced {R['n_houses']}\nof them to what stands on their sites today, and tested the Cistercians' reputation for empty places.",
         family=SER, fontsize=15, color=FG, va="top", linespacing=1.35)

# ---------------- hero: map inside a Gothic window
ax = fig.add_axes([0.0, 0.30, 0.6, 0.585])
x0, x1, base, apex = 120000, 680000, -20000, 700000
w = x1 - x0
r = w
rise = r * np.sin(np.arccos(0.5))
spring = apex - rise
t = np.linspace(np.pi, np.arccos(0.5) + 0, 60)
# left arc: centred on right springing point, sweeping from the left jamb to the apex
la = np.c_[x1 + r * np.cos(np.linspace(np.pi, np.pi - np.arccos(0.5), 60)), spring + r * np.sin(np.linspace(np.pi, np.pi - np.arccos(0.5), 60))]
ra = np.c_[x0 + r * np.cos(np.linspace(np.arccos(0.5), 0, 60)), spring + r * np.sin(np.linspace(np.arccos(0.5), 0, 60))]
outline = np.vstack([[x0, base], [x0, spring], la, ra, [x1, spring], [x1, base], [x0, base]])
win = Path(outline, [Path.MOVETO] + [Path.LINETO] * (len(outline) - 2) + [Path.CLOSEPOLY])
bgp = PathPatch(win, fc="#E3E6E1", ec="none", zorder=0)
ax.add_patch(bgp)
land(ax, nations=("England", "Wales", "Scotland"), fc="#D9D4C6", ec="#C4BEAE", lw=0.3)
for art in ax.patches[1:]:
    art.set_clip_path(bgp)
order = ["unclear", "protected", "nothing", "earthworks", "other", "school", "farm", "house", "church", "monastic", "cathedral", "ruin"]
for a in order:
    q = H[H.afterlife == a]
    if a in ("unclear", "protected"):
        sc = ax.scatter(q.x, q.y, s=9, facecolors="none", edgecolors="#A9A496", lw=0.6, zorder=3)
    elif a == "nothing":
        sc = ax.scatter(q.x, q.y, s=16, facecolors="none", edgecolors=FG, lw=0.9, zorder=3)
    else:
        col = {"ruin": MOSS, "church": SLATE, "cathedral": SLATE, "house": "#C08A2B", "farm": WARM, "school": "#C08A2B", "other": STONE, "monastic": "#7E4A87", "earthworks": "#9DB97E"}[a]
        sc = ax.scatter(q.x, q.y, s=58 if a == "cathedral" else 26 if a == "ruin" else 20, c=col, marker="^" if a in ("church", "cathedral") else "s" if a in ("house", "school") else "o",
                        lw=0.4, edgecolors=BG, zorder=4)
    sc.set_clip_path(bgp)
# stone frame: double line and a sill
for off, lw, col in ((0, 7, SLATE), (-14000, 1.6, SLATE)):
    o = outline.copy()
    cx = (x0 + x1) / 2
    o[:, 0] = cx + (o[:, 0] - cx) * (1 + off / (w / 2))
    o[:, 1] = base + (o[:, 1] - base) * (1 + off / (apex - base))
    ax.plot(o[:-1, 0], o[:-1, 1], color=col, lw=lw, solid_joinstyle="miter", zorder=6)
ax.plot([x0 - 30000, x1 + 30000], [base - 6000, base - 6000], color=SLATE, lw=9, solid_capstyle="butt", zorder=6)
# label a few
for name, dx, dy, ha in [("Fountains Abbey", 18000, -4000, "left"), ("Tintern Abbey", -16000, -14000, "right"), ("Whalley Abbey", -20000, 8000, "right"),
                         ("Westminster Abbey", 0, 0, None), ("Ely Cathedral Priory", 16000, 4000, "left"), ("Anglesey Priory, Lode, Cambridgeshire", 0, 0, None),
                         ("Rievaulx Abbey", 16000, 14000, "left"), ("Bath Abbey", -16000, -8000, "right")]:
    q = H[H.name == name]
    if not len(q) or ha is None:
        continue
    lab = name.replace(" Cathedral Priory", " Cathedral").replace("Anglesey Priory, Lode, Cambridgeshire", "Anglesey Abbey")
    ax.annotate(lab, xy=(q.x.iloc[0], q.y.iloc[0]), xytext=(q.x.iloc[0] + dx * 2.2, q.y.iloc[0] + dy * 2.2), family=MONO, fontsize=9.5, color=FG, ha=ha, va="center",
                arrowprops=dict(arrowstyle="-", color=FG, lw=0.7), zorder=8)
ax.set_xlim(x0 - 45000, x1 + 45000)
ax.set_ylim(base - 30000, apex + 25000)
ax.set_aspect("equal")
ax.axis("off")

# legend under the window
lg = fig.add_axes([0.04, 0.262, 0.55, 0.04])
lg.axis("off")
lg.set_xlim(0, 1)
lg.set_ylim(0, 1)
items = [("Ruin", MOSS, "o", None), ("Church or cathedral", SLATE, "^", None), ("House or hotel", "#C08A2B", "s", None), ("Farm", WARM, "o", None),
         ("Nothing visible", "none", "o", FG), ("Not recorded", "none", "o", "#A9A496")]
for i, (lab, c, m, ec) in enumerate(items):
    xx = (i % 3) * 0.34
    yy = 0.78 if i < 3 else 0.18
    lg.scatter([xx + 0.012], [yy], s=60, c=c, marker=m, edgecolors=ec if ec else BG, lw=1.0 if ec else 0.4)
    lg.text(xx + 0.035, yy, lab, family=MONO, fontsize=11, color=FG, va="center")

# ---------------- right column: headline numbers
rx = 0.625
blocks = [
    (f"{R['n_houses']}", "religious houses closed 1536 to 1540,\nfrom abbeys to friaries. 1538 alone\n" + f"took {R['by_year']['1538']}, {R['friars_1538']} of them friaries.", FG),
    (f"{R['afterlife_known_share']['house'] * 100:.0f}%", "of sites with a recorded fate are now\na house or hotel, the most common fate.\n" + f"{R['afterlife_known_share']['church'] * 100:.0f}% are churches; only {R['afterlife_known_share']['ruin'] * 100:.0f}% are ruins.", "#A06E12"),
    (f"{R['afterlife_known_share_by_order']['Cistercian']['ruin'] * 100:.0f}%", "of Cistercian sites are ruins, against\n" + f"{R['afterlife_known_share_by_order']['Benedictine']['ruin'] * 100:.0f}% of Benedictine ones, whose churches\noften lived on as parish churches.", MOSS),
    (f"{R['setting']['Cistercian monks']['pct_median']:.0f}th", "percentile: how busy a typical Cistercian\nsite was in 1086, against its own county.\n" + f"Quiet, not empty. Benedictines: {R['setting']['Benedictine monks']['pct_median']:.0f}th.", SLATE),
]
y = 0.872
for big, small, col in blocks:
    fig.text(rx, y, big, fontproperties=DISP, fontsize=46, color=col, va="top")
    fig.text(rx, y - 0.056, small, family=SER, fontsize=13.2, color=FG, va="top", linespacing=1.3)
    y -= 0.153

# ---------------- bottom left: fate by order
ax2 = fig.add_axes([0.17, 0.095, 0.36, 0.13], facecolor=BG)
ords = ["Benedictine", "Augustinian", "Cistercian", "Friars"]
cats = [("church", SLATE, "Church"), ("cathedral", SLATE, None), ("house", "#C08A2B", "House"), ("school", "#C08A2B", None), ("farm", WARM, "Farm"),
        ("other", STONE, "Other"), ("monastic", STONE, None), ("ruin", MOSS, "Ruin"), ("earthworks", "#9DB97E", None), ("nothing", "#CFC9BA", "Nothing")]
A = R["afterlife_known_share_by_order"]
for i, o in enumerate(ords):
    left = 0
    yy = len(ords) - 1 - i
    for k, c, lab in cats:
        v = A[o].get(k, 0)
        if v:
            ax2.barh(yy, v, left=left, color=c, height=0.72, edgecolor=BG, lw=0.8)
            if lab and v >= 0.12:
                ax2.text(left + v / 2, yy, f"{lab}\n{v * 100:.0f}%", ha="center", va="center", family=MONO, fontsize=8.6, color=FG if k == "nothing" else "white", linespacing=1.05)
            left += v
ax2.set_yticks(range(len(ords)))
ax2.set_yticklabels(ords[::-1], family=MONO, fontsize=11.5)
ax2.set_xticks([])
for s in ax2.spines.values():
    s.set_visible(False)
ax2.tick_params(length=0)
fig.text(0.045, 0.238, "WHAT THE SITE IS NOW, BY ORDER", family=MONO, fontsize=11, color=MUT)

# ---------------- bottom right: county percentile
ax3 = fig.add_axes([0.745, 0.11, 0.225, 0.115], facecolor=BG)
gs = ["Carthusian", "Cistercian monks", "Augustinian canons", "Benedictine monks", "Friars"]
for i, g in enumerate(gs):
    s = R["setting"][g]
    yy = len(gs) - 1 - i
    o = "Cistercian" if g.startswith("Cist") else "Benedictine" if g.startswith("Bene") else "Augustinian" if g.startswith("Aug") else g
    ax3.plot(s["pct_ci"], [yy, yy], color=FG, lw=2)
    ax3.scatter([s["pct_median"]], [yy], s=90, marker="s", c=ORDER_COL[o], edgecolors=FG, lw=1, zorder=4)
ax3.axvline(50, color=FG, ls="--", lw=1)
ax3.set_xlim(0, 100)
ax3.set_xticks([0, 50, 100])
ax3.set_xticklabels(["emptier", "county\ntypical", "busier"], family=MONO, fontsize=9.5)
ax3.set_yticks(range(len(gs)))
ax3.set_yticklabels([g.replace("Augustinian canons", "Augustinians").replace("Benedictine monks", "Benedictines").replace("Cistercian monks", "Cistercians") for g in gs][::-1], family=MONO, fontsize=11.5)
for sp in ["top", "right", "left"]:
    ax3.spines[sp].set_visible(False)
ax3.tick_params(axis="y", length=0)
fig.text(0.625, 0.238, "HOW BUSY WAS THE SITE IN 1086?", family=MONO, fontsize=11, color=MUT)

# ---------------- footer
fig.text(0.045, 0.018, "Sources: Wikipedia county lists of monastic houses (CC BY-SA 4.0) and Wikidata (CC0); Domesday households from the Hull Domesday Project\n"
         "(J.J.N. Palmer, G. Slater, University of Hull; CC BY-NC-SA) via realm-domesday; ONS county outlines (OGL v3). Fates classified by fixed rules from the lists'\n"
         f"own words; {R['afterlife']['unclear'] + R['afterlife']['protected']} houses have no recorded fate. 1086 test: {R['dom_area_n']} houses in England outside the far north, Lancashire, London and Winchester.\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib.",
         family=MONO, fontsize=8.6, color=MUT, linespacing=1.45)
fig.savefig(os.path.join(HERE, "what_became_of_the_abbeys.png"), facecolor=BG, dpi=200)
print("ok")
