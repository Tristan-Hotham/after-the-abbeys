"""Step 7. Render header.png (1200 x 630 social card) with matplotlib.
Run: python3 code/07_header.py
"""
import json
import os

import pandas as pd
from figlib import (BG, DISP, FG, MONO, MOSS, MUT, ORDER_COL, ROOT, SER, bng, gothic_arch, land, plt)

R = json.load(open(os.path.join(ROOT, "data", "results.json")))
H = pd.read_csv(os.path.join(ROOT, "data", "houses.csv")).dropna(subset=["lat"])
H["x"], H["y"] = bng(H.lon.values, H.lat.values)

fig = plt.figure(figsize=(6, 3.15), dpi=200, facecolor=BG)
ax = fig.add_axes([0.53, 0.0, 0.47, 1.0])
land(ax, lw=0.2)
for o in ["Friars", "Augustinian", "Benedictine", "Premonstratensian", "Cluniac", "Gilbertine", "Carthusian", "Military orders", "Other orders", "Unknown", "Cistercian"]:
    q = H[H.order == o]
    ax.scatter(q.x, q.y, s=7 if o == "Cistercian" else 3.2, c=ORDER_COL[o], lw=0, alpha=.95 if o == "Cistercian" else .75, zorder=3)
ax.set_xlim(150000, 670000)
ax.set_ylim(5000, 600000)
ax.set_aspect("equal")
ax.axis("off")
fig.text(0.05, 0.86, "DATA STUDY  ·  ENGLAND AND WALES, 1536 TO 1540", family=MONO, fontsize=6.5, color=MUT)
fig.text(0.05, 0.80, "What became\nof the abbeys?", fontproperties=DISP, fontsize=27, color=FG, va="top", linespacing=0.95)
fig.text(0.05, 0.47, f"{R['n_houses']:,} religious houses closed by Henry VIII,\ntraced to what stands on their sites today.\nAnd did the Cistercians really seek\nout empty places?", family=SER, fontsize=8.2, color=FG, va="top", linespacing=1.35)
lg = fig.add_axes([0.05, 0.13, 0.45, 0.06])
lg.axis("off"); lg.set_xlim(0, 1); lg.set_ylim(0, 1)
for i, o in enumerate(["Cistercian", "Benedictine", "Augustinian", "Friars"]):
    lg.scatter([i * 0.25 + 0.01], [0.5], s=14, c=ORDER_COL[o], lw=0)
    lg.text(i * 0.25 + 0.04, 0.5, o, family=MONO, fontsize=5.8, color=MUT, va="center")
fig.text(0.05, 0.07, "Dr Tristan Hotham  ·  Independent researcher", family=MONO, fontsize=6, color=MUT)
a2 = fig.add_axes([0.44, 0.27, 0.08, 0.22])
gothic_arch(a2, 0.1, 0.0, 0.8, 1.0, color=MOSS, lw=2.4, broken=True)
a2.set_xlim(0, 1)
a2.set_ylim(0, 1.05)
a2.set_aspect("equal")
a2.axis("off")
fig.savefig(os.path.join(ROOT, "header.png"), facecolor=BG, dpi=200)
print("header.png")
