import json
import subprocess
from datetime import date, timedelta
import os

#constants
REPO = os.path.dirname(os.path.abspath(__file__))
GARDEN_FILE = os.path.join(REPO, "garden.json")
SVG_FILE = os.path.join(REPO, "garden.svg")

# Load and save garden data
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
            "total_commits": 0,
            "best_streak": 0  # NEW
        }

# Save garden data
def save_garden(data):
    with open(GARDEN_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Update streak based on last commit date
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
    garden["best_streak"] = max(garden.get("best_streak", 0), garden["streak"])  # NEW
    return garden

# Draw the SVG representation of the garden
def draw_svg(garden):
    stage = garden["plant_stage"]
    wilting = garden["wilting"]
    streak = garden["streak"]
    total_commits = garden.get("total_commits", 0)
    best_streak = garden.get("best_streak", 0)

    # Decide which plant to draw
    if streak >= 21:
        plant_type = "blossom"
    elif streak >= 11:
        plant_type = "tree"
    elif streak >= 6:
        plant_type = "cactus"
    else:
        plant_type = "sprout"

    leaf_color = "#4caf50" if not wilting else "#a0522d"
    stem_color = "#388e3c" if not wilting else "#8b6914"
    bg_color = "#f0fff0" if not wilting else "#fff8e1"

    wilt_note = '<text x="100" y="235" text-anchor="middle" font-size="11" fill="#a0522d">Missed a day — keep going!</text>' if wilting else ""

    if plant_type == "sprout":
        capped = min(streak, 5)
        stem_height = 20 + (capped * 20)
        stem_y_end = 180 - stem_height
        leaves = ""
        if capped >= 1:
            leaves += f'<ellipse cx="100" cy="{stem_y_end + 20}" rx="18" ry="10" fill="{leaf_color}" transform="rotate(-30 100 {stem_y_end + 20})" />'
        if capped >= 2:
            leaves += f'<ellipse cx="100" cy="{stem_y_end + 10}" rx="18" ry="10" fill="{leaf_color}" transform="rotate(30 100 {stem_y_end + 10})" />'
        if capped >= 3:
            leaves += f'<ellipse cx="100" cy="{stem_y_end}" rx="20" ry="12" fill="{leaf_color}" />'
        if capped >= 4:
            leaves += f'<circle cx="100" cy="{stem_y_end - 12}" r="14" fill="#e91e63" />'
        if capped >= 5:
            leaves += f'<circle cx="100" cy="{stem_y_end - 12}" r="14" fill="#e91e63"><animate attributeName="r" values="14;17;14" dur="2s" repeatCount="indefinite" /></circle>'
        plant = f"""
  <rect x="80" y="{stem_y_end}" width="8" height="{stem_height}" fill="{stem_color}" />
  <rect x="60" y="178" width="58" height="10" rx="4" fill="#795548" />
  {leaves}"""
        label = "🌱 Sprout"

    elif plant_type == "cactus":
        plant = f"""
  <rect x="95" y="100" width="12" height="80" fill="#2e7d32" />
  <rect x="68" y="120" width="27" height="10" fill="#2e7d32" />
  <rect x="62" y="110" width="10" height="30" fill="#2e7d32" />
  <rect x="107" y="130" width="27" height="10" fill="#2e7d32" />
  <rect x="130" y="118" width="10" height="30" fill="#2e7d32" />
  <rect x="80" y="178" width="42" height="10" rx="4" fill="#795548" />
  <circle cx="100" cy="98" r="6" fill="#a5d6a7" />"""
        label = "🌵 Cactus"
        bg_color = "#fffde7" if not wilting else "#fff8e1"

    elif plant_type == "tree":
        plant = f"""
  <rect x="94" y="130" width="14" height="50" fill="#5d4037" />
  <ellipse cx="100" cy="110" rx="35" ry="30" fill="#388e3c" />
  <ellipse cx="75" cy="125" rx="22" ry="18" fill="#43a047" />
  <ellipse cx="125" cy="125" rx="22" ry="18" fill="#43a047" />
  <ellipse cx="100" cy="90" rx="25" ry="22" fill="#66bb6a" />
  <rect x="72" y="178" width="58" height="10" rx="4" fill="#795548" />"""
        label = "🌳 Tree"
        bg_color = "#e8f5e9" if not wilting else "#fff8e1"

    elif plant_type == "blossom":
        plant = f"""
  <rect x="94" y="130" width="14" height="50" fill="#5d4037" />
  <ellipse cx="100" cy="105" rx="38" ry="32" fill="#f8bbd0" />
  <ellipse cx="72" cy="122" rx="24" ry="18" fill="#f48fb1" />
  <ellipse cx="128" cy="122" rx="24" ry="18" fill="#f48fb1" />
  <ellipse cx="100" cy="88" rx="26" ry="20" fill="#fce4ec" />
  <circle cx="100" cy="100" r="8" fill="#ffeb3b" />
  <circle cx="100" cy="100" r="8" fill="#ffeb3b"><animate attributeName="r" values="8;11;8" dur="3s" repeatCount="indefinite" /></circle>
  <rect x="72" y="178" width="58" height="10" rx="4" fill="#795548" />"""
        label = "🌸 Cherry Blossom"
        bg_color = "#fce4ec" if not wilting else "#fff8e1"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="250">
  <rect width="200" height="250" fill="{bg_color}" rx="12" />
  {plant}
  <text x="100" y="200" text-anchor="middle" font-size="11" fill="#555">{label} — {streak} day streak</text>
  <text x="100" y="215" text-anchor="middle" font-size="10" fill="#888">{total_commits} total commits</text>
  <text x="100" y="229" text-anchor="middle" font-size="10" fill="#aaa">best: {best_streak} days</text>
  {wilt_note}
</svg>"""

    with open(SVG_FILE, "w", encoding="utf-8") as f:
        f.write(svg)

# Stage and commit the changes to the repository
def stage_commit():
    subprocess.run(["git", "-C", REPO, "add", GARDEN_FILE, SVG_FILE], check=True)
    result = subprocess.run(
        ["git", "-C", REPO, "commit", "--no-verify", "-m", "garden updated"],
        capture_output=True
    )

# Check if there was nothing to commit
def main():
    garden = load_garden()
    garden = update_streak(garden)
    save_garden(garden)
    draw_svg(garden)
    stage_commit()

# Run the main function if this script is executed directly
if __name__ == "__main__":
    main()