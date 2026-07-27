import json
import subprocess
from datetime import date, timedelta
import os

#constants
REPO = os.path.dirname(os.path.abspath(__file__))
GARDEN_FILE = os.path.join(REPO, "garden.json")
SVG_FILE = os.path.join(REPO, "garden.svg")

def load_garden():
    try:
        with open(GARDEN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "streak": 0,
            "last_commit_date": None,
            "plant_stage": 0,
            "wilting": False,
            "total_commits": 0
        }

def save_garden(data):
    with open(GARDEN_FILE, "w") as f:
        json.dump(data, f, indent=2)

def update_streak(garden):
    today = str(date.today())
    yesterday = str(date.today() - timedelta(days=1))
    last = garden.get("last_commit_date")

    if last == today:
        return garden
    elif last == yesterday:
        garden["streak"] += 1
        garden["wilting"] = False
    elif last is None:
        garden["streak"] = 1
        garden["wilting"] = False
    else:
        garden["streak"] = 1
        garden["wilting"] = True

    garden["last_commit_date"] = today
    garden["total_commits"] = garden.get("total_commits", 0) + 1
    garden["plant_stage"] = garden["streak"]
    return garden


# ============================================================
# Species rotation: which plant grows on which day of a 30-day
# cycle, 5 days each. The cycle repeats every 30 days.
# ============================================================

_SPECIES_ORDER = ["sunflower", "cactus", "fern", "flytrap", "succulent", "bamboo"]

def get_species_and_stage(streak):
    """Map a streak/day count to (species_name, stage 1-5), cycling every 30 days."""
    day_in_cycle = ((streak - 1) % 30) + 1          # 1..30
    block = (day_in_cycle - 1) // 5                  # 0..5
    stage = ((day_in_cycle - 1) % 5) + 1             # 1..5
    species = _SPECIES_ORDER[block]
    return species, stage


# ============================================================
# Shared pot (100-unit design space; the whole drawing is
# wrapped in scale(2) to fit the 200x220 canvas)
# ============================================================

def _pot_svg(fill):
    return (
        f'<ellipse cx="50" cy="88" rx="11" ry="5" fill="{fill}"/>'
        f'<path d="M36 68 L64 68 L60 88 L40 88 Z" fill="{fill}"/>'
    )


# ============================================================
# Color palettes per species (normal / wilted)
# ============================================================

def _palette(species, wilting):
    palettes = {
        "sunflower": {
            False: dict(pot="#a9673f", stem="#4a8f3c", leaf="#6bbf4f", leaf_s="#3a7a2a",
                        petal="#ffc107", petal_s="#c98a02", center="#e67e22", center_s="#a85d12"),
            True:  dict(pot="#8b6914", stem="#8b6914", leaf="#a0522d", leaf_s="#6b3a1a",
                        petal="#c9a05a", petal_s="#8b6914", center="#8b5a2b", center_s="#5c3a1a"),
        },
        "cactus": {
            False: dict(pot="#a9673f", paddle="#8bc34a", paddle_s="#3f6b2f", spike="#3f6b2f",
                        petal="#c23a72", petal_s="#993556", center="#ffd54f",
                        pebble="#9a9a9a", pebble_s="#707070"),
            True:  dict(pot="#8b6914", paddle="#a0522d", paddle_s="#6b3a1a", spike="#6b3a1a",
                        petal="#a06a7a", petal_s="#6b3a4a", center="#c9a05a",
                        pebble="#8a7a6a", pebble_s="#5a4a3a"),
        },
        "fern": {
            False: dict(pot="#a9673f", frond="#3f6b2f", leaflet="#8bc34a", leaflet_s="#3f6b2f", soil="#5c3a21"),
            True:  dict(pot="#8b6914", frond="#6b3a1a", leaflet="#a0522d", leaflet_s="#6b3a1a", soil="#4a2f1a"),
        },
        "flytrap": {
            False: dict(pot="#a9673f", stem_outline="#262626", stem="#8bc34a", tooth="#262626",
                        lobe="#8bc34a", lobe_s="#3f6b2f", inner="#f8bcc9", inner_s="#ec7fa0",
                        basal="#8bc34a", basal_s="#3f6b2f", bud_top="#ee8fa8", bud_bottom="#f6b9c8"),
            True:  dict(pot="#8b6914", stem_outline="#262626", stem="#a0522d", tooth="#262626",
                        lobe="#a0522d", lobe_s="#6b3a1a", inner="#d9a0a8", inner_s="#b06a78",
                        basal="#a0522d", basal_s="#6b3a1a", bud_top="#b06a78", bud_bottom="#c98a90"),
        },
        "succulent": {
            False: dict(pot="#a9673f", back="#4f9c3d", back_s="#2e5e22", front="#6bbf4f", front_s="#3a7a2a",
                        tip="#9ad678", fleck="#a9762e"),
            True:  dict(pot="#8b6914", back="#8b5a2b", back_s="#5c3a1a", front="#a0522d", front_s="#6b3a1a",
                        tip="#c9a05a", fleck="#6b3a1a"),
        },
        "bamboo": {
            False: dict(pot="#a9673f", stalk="#8bc34a", node="#f0e4c0", leaf="#4a7c3a"),
            True:  dict(pot="#8b6914", stalk="#a0522d", node="#d9c9a0", leaf="#6b3a1a"),
        },
    }
    return palettes[species][wilting]


# ============================================================
# SUNFLOWER (5 stages)
# ============================================================

_SF_LEAF_PATH = ("M0 0 L2 -4 L4 -2 L6 -6 L9 -4 L12 -7 L15 -5 L18 -6 L21 -3 L24 -4 L26 0 "
                  "L24 4 L21 3 L18 6 L15 5 L12 7 L9 4 L6 6 L4 2 L2 4 Z")
_SF_VEINS = ["M0 0 L25 0", "M6 -1 L9 -4", "M6 1 L9 4", "M14 -1 L16 -5.5", "M14 1 L16 5.5"]

def _sf_leaf(x, y, angle, scale, fill, stroke):
    v = "".join(f'<path d="{d}" stroke="{stroke}" stroke-width="0.5" fill="none"/>' for d in _SF_VEINS)
    return (f'<g transform="translate({x},{y}) rotate({angle}) scale({scale})">'
            f'<path d="{_SF_LEAF_PATH}" fill="{fill}" stroke="{stroke}" stroke-width="1"/>{v}</g>')

def _sf_bloom(x, y, petal_fill, petal_stroke, center_fill, center_stroke, pulse):
    petals = "".join(
        f'<ellipse cx="0" cy="-9" rx="2.6" ry="6.5" fill="{petal_fill}" stroke="{petal_stroke}" '
        f'stroke-width="0.6" transform="rotate({k})"/>' for k in range(0, 360, 45)
    )
    if pulse:
        center = (f'<circle cx="0" cy="0" r="5" fill="{center_fill}" stroke="{center_stroke}" stroke-width="0.6">'
                  f'<animate attributeName="r" values="5;6.2;5" dur="2s" repeatCount="indefinite"/></circle>')
    else:
        center = f'<circle cx="0" cy="0" r="5" fill="{center_fill}" stroke="{center_stroke}" stroke-width="0.6"/>'
    return f'<g transform="translate({x},{y})">{petals}{center}</g>'

def _sf_bud(x, y, sepal_fill, sepal_stroke, tip_fill, tip_stroke):
    return (f'<g transform="translate({x},{y})">'
            f'<path d="M-4 0 C-4 -6,4 -6,4 0 C4 3,-4 3,-4 0 Z" fill="{sepal_fill}" stroke="{sepal_stroke}" stroke-width="1"/>'
            f'<path d="M-2 -5 L0 -8 L2 -5 Z" fill="{tip_fill}" stroke="{tip_stroke}" stroke-width="0.6"/></g>')

def draw_sunflower(stage, c):
    out = _pot_svg(c["pot"])
    stem_top = {1: 56, 2: 42, 3: 26, 4: 20, 5: 22}.get(stage, 22)
    out += f'<path d="M50 68 C 49 55, 51 45, 50 {stem_top}" stroke="{c["stem"]}" stroke-width="2.5" fill="none"/>'
    if stage >= 2:
        out += _sf_leaf(50, 52, 205, 0.9, c["leaf"], c["leaf_s"])
    if stage >= 3:
        out += _sf_leaf(50, 38, -25, 0.9, c["leaf"], c["leaf_s"])
    if stage == 4:
        out += _sf_bud(50, 16, c["leaf"], c["leaf_s"], c["petal"], c["petal_s"])
    elif stage >= 5:
        out += _sf_bloom(50, 18, c["petal"], c["petal_s"], c["center"], c["center_s"], pulse=True)
    return out


# ============================================================
# CACTUS (5 stages)
# ============================================================

def _cactus_bloom(cx, cy, r, cr, petal_fill, petal_stroke, center_fill):
    return (f'<g transform="translate({cx},{cy})">'
            f'<circle cx="0" cy="-{r*1.33:.1f}" r="{r}" fill="{petal_fill}" stroke="{petal_stroke}" stroke-width="0.6"/>'
            f'<circle cx="-{r*1.13:.1f}" cy="-{r*0.4:.1f}" r="{r}" fill="{petal_fill}" stroke="{petal_stroke}" stroke-width="0.6"/>'
            f'<circle cx="{r*1.13:.1f}" cy="-{r*0.4:.1f}" r="{r}" fill="{petal_fill}" stroke="{petal_stroke}" stroke-width="0.6"/>'
            f'<circle cx="-{r*0.67:.1f}" cy="{r*0.8:.1f}" r="{r}" fill="{petal_fill}" stroke="{petal_stroke}" stroke-width="0.6"/>'
            f'<circle cx="{r*0.67:.1f}" cy="{r*0.8:.1f}" r="{r}" fill="{petal_fill}" stroke="{petal_stroke}" stroke-width="0.6"/>'
            f'<circle cx="0" cy="0" r="{cr}" fill="{center_fill}"/></g>')

_CACTUS_SPIKES_A = [(44,36,41,33),(56,36,59,33),(44,48,40,46),(56,48,60,46),(46,58,43,56),(28,42,25,39)]
_CACTUS_SPIKES_B = [(27,52,23,51),(36,38,33,35),(63,38,66,35),(70,46,73,44),(62,48,59,46),(73,24,76,21),(79,30,82,28)]

def _cactus_spikes(pts, stroke):
    return "".join(f'<line x1="{a}" y1="{b}" x2="{cx}" y2="{cy}" stroke="{stroke}" stroke-width="1" stroke-linecap="round"/>'
                    for a, b, cx, cy in pts)

def draw_cactus(stage, c):
    out = _pot_svg(c["pot"])
    out += f'<ellipse cx="50" cy="46" rx="13" ry="20" fill="{c["paddle"]}" stroke="{c["paddle_s"]}" stroke-width="1.3"/>'
    if stage >= 2:
        out += f'<g transform="rotate(-15 32 60)"><ellipse cx="32" cy="46" rx="9" ry="14" fill="{c["paddle"]}" stroke="{c["paddle_s"]}" stroke-width="1.3"/></g>'
    if stage >= 3:
        out += f'<g transform="rotate(12 66 54)"><ellipse cx="66" cy="42" rx="8" ry="12" fill="{c["paddle"]}" stroke="{c["paddle_s"]}" stroke-width="1.3"/></g>'
        out += _cactus_spikes(_CACTUS_SPIKES_A, c["spike"])
    if stage >= 4:
        out += f'<g transform="rotate(20 76 35)"><ellipse cx="76" cy="26" rx="6" ry="9" fill="{c["paddle"]}" stroke="{c["paddle_s"]}" stroke-width="1.3"/></g>'
        out += _cactus_spikes(_CACTUS_SPIKES_B, c["spike"])
    if stage >= 5:
        out += _cactus_bloom(27, 26, 3, 1.8, c["petal"], c["petal_s"], c["center"])
        out += _cactus_bloom(68, 27, 2.6, 1.5, c["petal"], c["petal_s"], c["center"])
        out += _cactus_bloom(80, 14, 2.2, 1.3, c["petal"], c["petal_s"], c["center"])
        out += "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c["pebble"]}" stroke="{c["pebble_s"]}" stroke-width="0.5"/>'
                        for x, y, r in [(40,66,2.2),(45,65,2),(50,66.5,2.4),(55,65,2),(60,66,2.2)])
    return out


# ============================================================
# FERN (5 stages)
# ============================================================

_FERN_LEVELS = [(51.31, 62, 16), (52.25, 56, 15), (52.81, 50, 13),
                (53.0, 44, 11), (52.81, 38, 9), (52.25, 32, 7), (51.31, 26, 5)]

def _fern_leaflet(lx, ly, L, fill, stroke):
    W = L * 0.35
    d = f"M0 0 C{L*0.3:.1f} -{W/2:.2f},{L*0.7:.1f} -{W/2:.2f},{L} 0 C{L*0.7:.1f} {W/2:.2f},{L*0.3:.1f} {W/2:.2f},0 0 Z"
    left = f'<g transform="translate({lx},{ly}) rotate(-125)"><path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="0.6"/></g>'
    right = f'<g transform="translate({lx},{ly}) rotate(-55)"><path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="0.6"/></g>'
    return left + right

def _fern_frond(angle, with_leaflets, stroke, leaflet_fill, leaflet_stroke):
    stem = f'<path d="M50 68 Q 56 45 50 20" stroke="{stroke}" stroke-width="2" stroke-linecap="round" fill="none"/>'
    leaflets = "".join(_fern_leaflet(lx, ly, L, leaflet_fill, leaflet_stroke) for lx, ly, L in _FERN_LEVELS) if with_leaflets else ""
    return f'<g transform="rotate({angle} 50 68)">{stem}{leaflets}</g>'

def draw_fern(stage, c):
    out = _pot_svg(c["pot"])
    out += f'<ellipse cx="50" cy="67" rx="12" ry="2.6" fill="{c["soil"]}"/>'
    out += _fern_frond(0, stage >= 2, c["frond"], c["leaflet"], c["leaflet_s"])
    if stage >= 3:
        out += _fern_frond(-30, True, c["frond"], c["leaflet"], c["leaflet_s"])
        out += _fern_frond(30, True, c["frond"], c["leaflet"], c["leaflet_s"])
    if stage >= 4:
        out += _fern_frond(-58, stage >= 5, c["frond"], c["leaflet"], c["leaflet_s"])
        out += _fern_frond(58, stage >= 5, c["frond"], c["leaflet"], c["leaflet_s"])
    return out


# ============================================================
# VENUS FLYTRAP (5 stages)
# ============================================================

_FT_TEETH = [(-7.88,-7.61,-15.76,-6.22),(-7.73,-11.07,-15.45,-13.14),(-6.13,-14.14,-12.26,-19.28),
             (-3.38,-16.25,-6.76,-23.5),(0.0,-17.0,0.0,-25.0),(3.38,-16.25,6.76,-23.5),
             (6.13,-14.14,12.26,-19.28),(7.73,-11.07,15.45,-13.14),(7.88,-7.61,15.76,-6.22)]

def _ft_trap(tip_x, tip_y, angle, scale, c):
    teeth = "".join(f'<line x1="{a}" y1="{b}" x2="{cx}" y2="{cy}" stroke="{c["tooth"]}" stroke-width="1.4" stroke-linecap="round"/>'
                     for a, b, cx, cy in _FT_TEETH)
    return (f'<g transform="translate({tip_x},{tip_y}) rotate({angle}) scale({scale})">'
            f'<g transform="scale(1.3,0.85)">{teeth}'
            f'<circle cx="0" cy="-9" r="10" fill="{c["lobe"]}" stroke="{c["lobe_s"]}" stroke-width="1.3"/>'
            f'<circle cx="0" cy="-9" r="6.5" fill="{c["inner"]}" stroke="{c["inner_s"]}" stroke-width="0.8"/>'
            f'</g></g>')

def _ft_stem(path_d, stroke_color, fill_color):
    return (f'<path d="{path_d}" stroke="{stroke_color}" stroke-width="3.4" stroke-linecap="round" fill="none"/>'
            f'<path d="{path_d}" stroke="{fill_color}" stroke-width="1.8" stroke-linecap="round" fill="none"/>')

def draw_flytrap(stage, c):
    out = _pot_svg(c["pot"])
    basal = [(-18,26,1.0),(-6,30,1.0),(6,30,1.0),(18,26,1.0)]
    for i, (angle, length, scale) in enumerate(basal):
        d = f"M0 0 C-{length*0.13:.1f} -{length*0.3:.1f},-{length*0.08:.1f} -{length*0.7:.1f},0 -{length} C{length*0.08:.1f} -{length*0.7:.1f},{length*0.13:.1f} -{length*0.3:.1f},0 0 Z"
        x = [46, 48, 52, 54][i]
        out += f'<g transform="translate({x},68) rotate({angle}) scale({scale})"><path d="{d}" fill="{c["basal"]}" stroke="{c["basal_s"]}" stroke-width="1.1"/></g>'

    trap_defs = [
        ("M50 68 Q 38 52 28 40", 28, 40, -75, 1.0),
        ("M50 68 Q 40 46 33 30", 33, 30, -55, 0.9),
        ("M50 68 Q 60 46 67 30", 67, 30, 55, 0.9),
        ("M50 68 Q 62 52 72 40", 72, 40, 75, 1.0),
    ]
    n_traps = {1: 0, 2: 2, 3: 4, 4: 4, 5: 4}.get(stage, 4)
    for path_d, tip_x, tip_y, angle, scale in trap_defs[:n_traps]:
        out += _ft_stem(path_d, c["stem_outline"], c["stem"])
        out += _ft_trap(tip_x, tip_y, angle, scale, c)

    if stage == 4:
        out += _ft_stem("M50 68 L50 40", c["stem_outline"], c["stem"])
    elif stage >= 5:
        out += _ft_stem("M50 68 L50 14", c["stem_outline"], c["stem"])
        out += (f'<g transform="translate(50,10)">'
                f'<path d="M-4 0 A4 4 0 0 1 4 0 Z" fill="{c["bud_top"]}" stroke="{c["stem_outline"]}" stroke-width="1"/>'
                f'<path d="M-4 0 A4 4 0 0 0 4 0 Z" fill="{c["bud_bottom"]}" stroke="{c["stem_outline"]}" stroke-width="1"/></g>')
    return out


# ============================================================
# SUCCULENT (5 stages)
# ============================================================

_SUCC_BACK = [(-72,17.0,3.24),(-50,19.0,3.65),(-30,21.0,3.92),(-10,22.0,4.19),
              (10,22.0,4.19),(30,21.0,3.92),(50,19.0,3.65),(72,17.0,3.24)]
_SUCC_FRONT = [(-55,13.0,2.56),(-33,15.0,2.97),(-12,16.5,3.38),
               (12,16.5,3.38),(33,15.0,2.97),(55,13.0,2.56)]

def _succ_leaf(angle, L, bulge, fill, stroke, tip_fill):
    h1 = L * 0.18
    d_out = f"M0 0 C-{bulge:.2f} -{h1:.2f},-{bulge:.2f} -{L-h1:.2f},0 -{L:.1f} C{bulge:.2f} -{L-h1:.2f},{bulge:.2f} -{h1:.2f},0 0 Z"
    tip_w = bulge * 0.4
    d_tip = f"M0 0 C-{tip_w:.2f} -{h1:.2f},-{tip_w:.2f} -{L-h1:.2f},0 -{L:.1f} C{tip_w:.2f} -{L-h1:.2f},{tip_w:.2f} -{h1:.2f},0 0 Z"
    return (f'<g transform="translate(50,63) rotate({angle}) scale(1.55)">'
            f'<path d="{d_out}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>'
            f'<path d="{d_tip}" fill="{tip_fill}" opacity="0.85"/></g>')

def draw_succulent(stage, c):
    out = _pot_svg(c["pot"])
    back_count = {1: 4, 2: 8, 3: 8, 4: 8, 5: 8}.get(stage, 8)
    front_count = {1: 0, 2: 0, 3: 3, 4: 6, 5: 6}.get(stage, 6)
    back_slice = _SUCC_BACK[2:6] if stage == 1 else _SUCC_BACK[:back_count]
    for angle, L, bulge in back_slice:
        out += _succ_leaf(angle, L, bulge, c["back"], c["back_s"], c["tip"])
    front_slice = _SUCC_FRONT[1:4] if stage == 3 else _SUCC_FRONT[:front_count]
    for angle, L, bulge in front_slice:
        out += _succ_leaf(angle, L, bulge, c["front"], c["front_s"], c["tip"])
    if stage >= 5:
        out += (f'<path d="M46 46 L50 40 L54 46 Z" fill="{c["fleck"]}" opacity="0.9"/>'
                f'<path d="M40 52 L43.5 47 L46.5 52.5 Z" fill="{c["fleck"]}" opacity="0.9"/>'
                f'<path d="M54 52.5 L57 47 L60 52 Z" fill="{c["fleck"]}" opacity="0.9"/>')
    return out


# ============================================================
# BAMBOO (5 stages)
# ============================================================

def _bb_stalk(x, y_base, y_top, width, stroke):
    return f'<path d="M{x} {y_base} L{x} {y_top}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" fill="none"/>'

def _bb_nodes(x, ys, rx, fill):
    return "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="1.3" fill="{fill}"/>' for y in ys)

def _bb_cluster(x, y, specs, fill):
    inner = "".join(
        f'<g transform="rotate({a})"><path d="M0 0 C-{w:.1f} -{w*1.25:.1f},-{w:.1f} -{L*0.7:.1f},0 -{L} '
        f'C{w:.1f} -{L*0.7:.1f},{w:.1f} -{w*1.25:.1f},0 0 Z" fill="{fill}"/></g>'
        for a, L, w in specs
    )
    return f'<g transform="translate({x},{y})">{inner}</g>'

def draw_bamboo(stage, c):
    out = _pot_svg(c["pot"])
    out += _bb_stalk(40, 68, 44, 4, c["stalk"])
    if stage >= 2:
        out += _bb_nodes(40, [60, 52], 2.6, c["node"])
        out += _bb_cluster(40, 44, [(-50,16,3.2),(-20,19,3.6),(10,17,3.3),(35,14,2.8)], c["leaf"])
        out += _bb_stalk(50, 68, 20, 5, c["stalk"])
    if stage >= 3:
        out += _bb_nodes(50, [52, 38, 26], 3.1, c["node"])
        out += _bb_cluster(50, 20, [(-45,20,3.8),(-15,24,4.2),(15,22,4.0),(45,18,3.4)], c["leaf"])
    if stage >= 4:
        out += _bb_cluster(50, 42, [(15,14,2.8),(35,16,3.0),(55,13,2.6)], c["leaf"])
        out += _bb_stalk(60, 68, 36, 4.5, c["stalk"])
    if stage >= 5:
        out += _bb_nodes(60, [54, 45], 2.85, c["node"])
        out += _bb_cluster(60, 36, [(-20,15,3.0),(10,18,3.5),(35,16,3.2),(55,13,2.6)], c["leaf"])
    return out


_DRAW_FUNCS = {
    "sunflower": draw_sunflower,
    "cactus": draw_cactus,
    "fern": draw_fern,
    "flytrap": draw_flytrap,
    "succulent": draw_succulent,
    "bamboo": draw_bamboo,
}


def draw_svg(garden):
    streak = garden["streak"]
    wilting = garden["wilting"]

    species, stage = get_species_and_stage(max(streak, 1))
    colors = _palette(species, wilting)
    plant_svg = _DRAW_FUNCS[species](stage, colors)

    wilt_note = (
        '<text x="100" y="210" text-anchor="middle" font-size="11" fill="#a0522d">'
        '💧 Missed a day — keep going!</text>'
    ) if wilting else ""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="220" viewBox="0 0 200 220">
                <g transform="scale(2)">{plant_svg}</g>
                <text x="100" y="200" text-anchor="middle" font-size="12" fill="#555">🔥 {streak} day streak</text>
                {wilt_note}
              </svg>"""

    with open(SVG_FILE, "w", encoding="utf-8") as f:
        f.write(svg)


def stage_commit():
    subprocess.run(["git", "-C", REPO, "add", GARDEN_FILE, SVG_FILE], check=True)
    result = subprocess.run(
        ["git", "-C", REPO, "commit", "--no-verify", "-m", "garden updated"],
        capture_output=True
    )

def main():
    garden = load_garden()
    garden = update_streak(garden)
    save_garden(garden)
    draw_svg(garden)
    stage_commit()

if __name__ == "__main__":
    main()