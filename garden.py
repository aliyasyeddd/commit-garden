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
    garden["plant_stage"] = min(garden["streak"], 5)
    return garden

def draw_svg(garden):
    stage = garden["plant_stage"]
    wilting = garden["wilting"]
    streak = garden["streak"]


    leaf_color = "#4caf50" if not wilting else "#a0522d"
    stem_color = "#388e3c" if not wilting else "#8b6914"

    stem_height = 20 + (stage * 20)
    stem_y_start = 180
    stem_y_end = stem_y_start - stem_height

    leaves = ""
    if stage >= 1:
        leaves += f'<ellipse cx="100" cy="{stem_y_end + 20}" rx="18" ry="10" fill="{leaf_color}" transform="rotate(-30 100 {stem_y_end + 20})" />'
    if stage >= 2:
        leaves += f'<ellipse cx="100" cy="{stem_y_end + 10}" rx="18" ry="10" fill="{leaf_color}" transform="rotate(30 100 {stem_y_end + 10})" />'
    if stage >= 3:
        leaves += f'<ellipse cx="100" cy="{stem_y_end}" rx="20" ry="12" fill="{leaf_color}" />'
    if stage >= 4:
        leaves += f'<circle cx="100" cy="{stem_y_end - 12}" r="14" fill="#e91e63" />'
    if stage >= 5:
        leaves += f'<circle cx="100" cy="{stem_y_end - 12}" r="14" fill="#e91e63"><animate attributeName="r" values="14;17;14" dur="2s" repeatCount="indefinite" /></circle>'


    wilt_note = (
        '<text x="100" y="210" text-anchor="middle" '
        'font-size="11" fill="#a0522d">'
        '💧 Missed a day — keep going!'
        '</text>'
    ) if wilting else ""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="220">
                <rect x="80" y="{stem_y_end}" width="8" height="{stem_height}" fill="{stem_color}" />
                <rect x="60" y="178" width="58" height="10" rx="4" fill="#795548" />
                {leaves}
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