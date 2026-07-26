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

def _leaf_svg(x, y, angle, scale, fill, stroke):
    return (
        f'<g transform="translate({x},{y}) rotate({angle}) scale({scale})">'
        f'<path d="{_LEAF_PATH}" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
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
    else:
        stem_color = "#8b6914"
        leaf_fill = "#a0522d"
        leaf_stroke = "#6b3a1a"
        petal_fill = "#c9a05a"
        petal_stroke = "#8b6914"
        center_fill = "#8b5a2b"
        center_stroke = "#5c3a1a"

    stem_height = 20 + (stage * 20)
    stem_y_start = 180
    stem_y_end = stem_y_start - stem_height

    growth = ""

    if stage >= 1:
        growth += _leaf_svg(100, stem_y_start - stem_height * 0.35, -200, 0.9, leaf_fill, leaf_stroke)
    if stage >= 2:
        growth += _leaf_svg(100, stem_y_start - stem_height * 0.6, -20, 1.0, leaf_fill, leaf_stroke)
    if stage >= 3:
        growth += _leaf_svg(100, stem_y_start - stem_height * 0.85, -165, 0.75, leaf_fill, leaf_stroke)
    if stage == 4:
        growth += _bloom_svg(100, stem_y_end, petal_fill, petal_stroke, center_fill, center_stroke, pulse=False)
    elif stage >= 5:
        growth += _bloom_svg(100, stem_y_end, petal_fill, petal_stroke, center_fill, center_stroke, pulse=True)

    wilt_note = (
        '<text x="100" y="210" text-anchor="middle" '
        'font-size="11" fill="#a0522d">'
        '💧 Missed a day — keep going!'
        '</text>'
    ) if wilting else ""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="220">
                <rect x="80" y="{stem_y_end}" width="8" height="{stem_height}" fill="{stem_color}" />
                <rect x="60" y="178" width="58" height="10" rx="4" fill="#795548" />
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