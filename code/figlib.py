"""Shared drawing helpers for the static figures (header, paper, blog, collage).

Fonts: Fraunces, Source Serif 4 and IBM Plex Mono TTFs in FONT_DIR (from github.com/google/fonts).
Land: ONS county outlines (OGL v3) from how-roman-is-your-road/data/counties.geojson.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path  # noqa: E402
from pyproj import Transformer  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.dirname(ROOT)
FONT_DIR = os.environ.get("FONT_DIR", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/")
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
    if os.path.exists(FONT_DIR + f):
        fm.fontManager.addfont(FONT_DIR + f)
DISP = fm.FontProperties(fname=FONT_DIR + "FrauncesVar.ttf", weight=900) if os.path.exists(FONT_DIR + "FrauncesVar.ttf") else fm.FontProperties(family="serif", weight="bold")
SER = "Source Serif 4"
MONO = "IBM Plex Mono"

BG = "#EEEBE3"      # limestone
CARD = "#F7F5EF"
FG = "#22241F"      # ink
MUT = "#62665C"
LAND = "#DDD8CC"
LANDLINE = "#C9C3B4"
MOSS = "#4E7A2E"
SLATE = "#4A5563"
WARM = "#B5532A"    # warm accent (rust)
ORDER_COL = {"Benedictine": "#2F3A4A", "Cistercian": "#5E8C34", "Augustinian": "#B07A1F", "Premonstratensian": "#2E7C82",
             "Cluniac": "#7E4A87", "Gilbertine": "#B5532A", "Carthusian": "#2F5C9A", "Friars": "#8C6E54",
             "Military orders": "#A33A3A", "Other orders": "#8F8B80", "Unknown": "#B9B4A7"}
AFTER_COL = {"cathedral": "#2F3A4A", "church": "#55657A", "house": "#A06E12", "school": "#C9A35A", "farm": "#B5532A",
             "other": "#8F8B80", "monastic": "#7E4A87", "ruin": "#5E8C34", "earthworks": "#9DB97E", "nothing": "#CFC9BA",
             "protected": "#B9B4A7", "unclear": "#DDD8CC"}
ALAB = {"cathedral": "Cathedral", "monastic": "Monastery again", "church": "Church in use", "house": "House or hotel",
        "school": "School or college", "farm": "Farm", "other": "Other use", "ruin": "Ruin", "earthworks": "Earthworks only",
        "nothing": "Nothing visible", "protected": "Protected, use unrecorded", "unclear": "Unclear"}
TO_BNG = Transformer.from_crs(4326, 27700, always_xy=True)


def bng(lon, lat):
    return TO_BNG.transform(np.asarray(lon), np.asarray(lat))


def land(ax, nations=("England", "Wales", "Scotland"), fc=LAND, ec=LANDLINE, lw=0.3, outline_only=False):
    g = json.load(open(os.path.join(HIST, "how-roman-is-your-road", "data", "counties.geojson")))
    for f in g["features"]:
        if f["properties"]["nation"] not in nations:
            continue
        geo = f["geometry"]
        parts = geo["geometries"] if geo["type"] == "GeometryCollection" else [geo]
        polys = []
        for gp in parts:
            if gp["type"] == "MultiPolygon":
                polys += gp["coordinates"]
            elif gp["type"] == "Polygon":
                polys.append(gp["coordinates"])
        for poly in polys:
            verts, codes = [], []
            for ring in poly:
                a = np.array(ring)[:, :2]
                x, y = bng(a[:, 0], a[:, 1])
                verts += list(zip(x, y))
                codes += [Path.MOVETO] + [Path.LINETO] * (len(a) - 2) + [Path.CLOSEPOLY]
            ax.add_patch(PathPatch(Path(verts, codes), fc="none" if outline_only else fc, ec=ec, lw=lw, zorder=0))


def gothic_arch(ax, x, y, w, h, color=FG, lw=3, broken=False, zorder=3):
    """Draw a pointed (Gothic) arch outline with its base at (x, y), in axis data units."""
    r = w  # equilateral arch: each arc has radius = span
    t = np.linspace(0, np.arccos(0.5), 40)
    left = np.c_[x + w - r * np.cos(t), y + h * 0 + r * np.sin(t)]   # arc centred on right foot
    right = np.c_[x + r * np.cos(t), y + r * np.sin(t)]              # arc centred on left foot
    spring = h - r * np.sin(np.arccos(0.5))
    left[:, 1] += spring
    right[:, 1] += spring
    if broken:
        right = right[:int(len(right) * 0.62)]
    ax.plot([x, x], [y, y + spring], color=color, lw=lw, solid_capstyle="butt", zorder=zorder)
    ax.plot([x + w, x + w], [y, y + spring], color=color, lw=lw, solid_capstyle="butt", zorder=zorder)
    ax.plot(left[:, 0], left[:, 1], color=color, lw=lw, zorder=zorder)
    ax.plot(right[:, 0], right[:, 1], color=color, lw=lw, zorder=zorder)
