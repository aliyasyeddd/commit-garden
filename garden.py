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


# ---- sunflower drawing helpers ----

_LEAF_PATH = (
    "M0 0 L2 -4 L4 -2 L6 -6 L9 -4 L12 -7 L15 -5 L18 -6 L21 -3 L24 -4 L26 0 "
    "L24 4 L21 3 L18 6 L15 5 L12 7 L9 4 L6 6 L4 2 L2 4 Z"
)

# pot shape lifted directly from the plant artifact (100x100 viewBox), scaled 2x
# to fit this script's 200x220 canvas
_POT_RIM = '<ellipse cx="100" cy="176" rx="22" ry="10" fill="{fill}"/>'
_POT_BODY = '<path d="M72 136 L128 136 L120 176 L80 176 Z" fill="{fill}"/>'

def _pot_svg(fill):
    return _POT_RIM.format(fill=fill) + _POT_BODY.format(fill=fill)

def _leaf_svg(x, y, angle, scale, fill, stroke):
    return (
        f'<g transform="translate({x},{y}) rotate({angle}) scale({scale})">'
        f'<path d="{_LEAF_PATH}" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
        f'</g>'
    )

def _bud_svg(x, y, sepal_fill, sepal_stroke, tip_fill, tip_stroke):
    # closed bud: rounded green sepal shape with a yellow tip peeking through the top
    return (
        f'<g transform="translate({x},{y})">'
        f'<path d="M-4 0 C-4 -6,4 -6,4 0 C4 3,-4 3,-4 0 Z" '
        f'fill="{sepal_fill}" stroke="{sepal_stroke}" stroke-width="1"/>'
        f'<path d="M-2 -5 L0 -8 L2 -5 Z" '
        f'fill="{tip_fill}" stroke="{tip_stroke}" stroke-width="0.6"/>'
        f'</g>'
    )

def _bloom_svg(x, y, petal_fill, petal_stroke, center_fill, center_stroke, pulse=False):
    petals = "".join(
        f'<ellipse cx="0" cy="-16" rx="4.5" ry="11" fill="{petal_fill}" '
        f'stroke="{petal_stroke}" stroke-width="1" transform="rotate({k})"/>'
        for k in range(0, 360, 45)
    )
    if pulse:
        center = (
            f'<circle cx="0" cy="0" r="9" fill="{center_fill}" '
            f'stroke="{center_stroke}" stroke-width="1">'
            f'<animate attributeName="r" values="9;11;9" dur="2s" repeatCount="indefinite" />'
            f'</circle>'
        )
    else:
        center = (
            f'<circle cx="0" cy="0" r="9" fill="{center_fill}" '
            f'stroke="{center_stroke}" stroke-width="1"/>'
        )
    return f'<g transform="translate({x},{y})">{petals}{center}</g>'


def draw_svg(garden):
    stage = garden["plant_stage"]
    wilting = garden["wilting"]
    streak = garden["streak"]

    # color palette (wilted = browner, dimmer tones)
    if not wilting:
        stem_color = "#4a8f3c"
        leaf_fill = "#6bbf4f"
        leaf_stroke = "#3a7a2a"
        petal_fill = "#ffc107"
        petal_stroke = "#c98a02"
        center_fill = "#e67e22"
        center_stroke = "#a85d12"
        pot_fill = "#a9673f"
    else:
        stem_color = "#8b6914"
        leaf_fill = "#a0522d"
        leaf_stroke = "#6b3a1a"
        petal_fill = "#c9a05a"
        petal_stroke = "#8b6914"
        center_fill = "#8b5a2b"
        center_stroke = "#5c3a1a"
        pot_fill = "#8b6914"

    # stem length per stage, matching the reference growth artwork exactly
    # (scaled 2x from the 100-unit reference: stage1=12, stage2=26, stage3=42, stage4=48, stage5=46)
    _STAGE_STEM_HEIGHT = {1: 24, 2: 52, 3: 84, 4: 96, 5: 92}
    stem_height = _STAGE_STEM_HEIGHT.get(stage, 92 if stage > 5 else 24)
    stem_y_start = 136  # top of the pot rim (where the pot trapezoid's top edge sits)
    stem_y_end = stem_y_start - stem_height

    growth = ""

    # stage 1: bare stem only (no leaves yet, matching the reference)
    # stage 2: first leaf; stage 3: second leaf
    if stage >= 2:
        growth += _leaf_svg(100, 104, -200, 0.9, leaf_fill, leaf_stroke)
    if stage >= 3:
        growth += _leaf_svg(100, 76, -20, 1.0, leaf_fill, leaf_stroke)

    # stage 3: stem keeps growing taller, leaves stay as-is (no new leaf)
    # stage 4: closed bud at the top
    # stage 5+: bud opens into the full bloom, center pulses
    if stage == 4:
        growth += _bud_svg(100, stem_y_end, leaf_fill, leaf_stroke, petal_fill, petal_stroke)
    elif stage >= 5:
        growth += _bloom_svg(100, stem_y_end, petal_fill, petal_stroke, center_fill, center_stroke, pulse=True)

    wilt_note = (
        '<text x="100" y="210" text-anchor="middle" '
        'font-size="11" fill="#a0522d">'
        '💧 Missed a day — keep going!'
        '</text>'
    ) if wilting else ""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="220" viewBox="0 0 200 220">
                {_pot_svg(pot_fill)}
                <rect x="96" y="{stem_y_end}" width="8" height="{stem_height}" fill="{stem_color}" />
                {growth}
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