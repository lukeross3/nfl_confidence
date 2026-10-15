import argparse
import os
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

from nfl_confidence.yahoo import (
    PICK_DTYPES,
    add_yahoo_args,
    get_league_picks,
    get_session,
    get_weekly_points,
    load_league_picks,
)

# Setup and parse script args
now = datetime.now()
current_season = now.year if now.month >= 3 else now.year - 1
parser = argparse.ArgumentParser(
    description="Plot the league's points by week. Downloads this season's picks from Yahoo, "
    "or reads a saved season: picks saved by scripts/get_league_picks.py, or a tab-separated "
    "table of weekly totals with a column per member, as in older seasons' league_results files"
)
add_yahoo_args(parser)
parser.add_argument(
    "--season",
    type=int,
    default=current_season,
    help="Season year, used to name the images",
)
parser.add_argument(
    "--input_path",
    type=str,
    default=None,
    help="Saved season to plot, instead of downloading this season from Yahoo",
)
parser.add_argument("--output_dir", type=str, default="images")
args = parser.parse_args()

# Yahoo gives the group a new ID each season, and takes the pages down once it's over
if args.input_path is None and args.season != current_season:
    parser.error(f"Yahoo only has the {current_season} season. Pass --input_path to plot another")

# Get points by week, with a row per week and a column per member. Picks have a row per
# (member, game), so total those up. Older seasons' files already have the weekly totals.
if args.input_path is None:
    df = get_weekly_points(get_league_picks(get_session(args.state_path), args.group_id))
elif set(PICK_DTYPES) <= set(pd.read_csv(args.input_path, nrows=0).columns):
    df = get_weekly_points(load_league_picks(args.input_path))
else:
    df = pd.read_csv(args.input_path, sep="\t")
    df.index = pd.RangeIndex(start=1, stop=len(df) + 1)
if df.empty:
    raise ValueError("No finished weeks to plot")

# images/ is gitignored, so a fresh clone won't have it
os.makedirs(args.output_dir, exist_ok=True)


def image_path(name: str) -> str:
    return os.path.join(args.output_dir, f"{name}_{args.season}.png")


# Set a clean, modern style
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 12,
        "legend.fontsize": 10,
        "legend.framealpha": 0.9,
        "figure.figsize": (10, 6),
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": plt.cycler(
            color=[
                "#2ecc71",
                "#3498db",
                "#e74c3c",
                "#9b59b6",
                "#f39c12",
                "#1abc9c",
                "#e67e22",
                "#34495e",
            ]
        ),
    }
)

# Plot weekly results
fig, ax = plt.subplots()
df.plot(ax=ax, linewidth=2.5, marker="o", markersize=5, alpha=0.85)
ax.set_title("Points Per Week")
ax.set_xlabel("Week Number")
ax.set_ylabel("Points")
ax.xaxis.set_major_locator(MaxNLocator(integer=True))
ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0)
plt.tight_layout()
plt.savefig(image_path("weekly"), dpi=200, bbox_inches="tight")

# Plot histogram of weekly scores
n_cols = len(df.columns)
fig, axes = plt.subplots(2, (n_cols + 1) // 2, figsize=(12, 8))
axes = axes.flatten()
colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

# Calculate shared x-axis range across all columns
x_min = df.min().min()
x_max = df.max().max()
bin_edges = range(int(x_min // 10) * 10, int(x_max // 10 + 2) * 10, 10)

for i, col in enumerate(df.columns):
    ax = axes[i]
    ax.hist(
        df[col],
        bins=bin_edges,
        alpha=0.8,
        color=colors[i % len(colors)],
        edgecolor="white",
        linewidth=1.2,
    )
    ax.set_title(col, fontsize=12, fontweight="bold")
    ax.set_xlabel("Points Per Week")
    ax.set_ylabel("Frequency")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlim(bin_edges[0], bin_edges[-1])
# Hide unused subplots
for j in range(i + 1, len(axes)):
    axes[j].set_visible(False)
fig.suptitle("Distribution of Weekly Scores", fontsize=16, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(image_path("weekly_hist"), dpi=200, bbox_inches="tight")

# Plot cumulative results, starting from 0 the week before the first
fig, ax = plt.subplots()
start = pd.DataFrame(0, index=[df.index[0] - 1], columns=df.columns)
cum_df = pd.concat([start, df]).cumsum()
cum_df.plot(ax=ax, linewidth=2.5, marker="o", markersize=4, alpha=0.85)
ax.set_title("Total Points")
ax.set_xlabel("Week Number")
ax.set_ylabel("Points")
ax.xaxis.set_major_locator(MaxNLocator(integer=True))
ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0)
plt.tight_layout()
plt.savefig(image_path("total"), dpi=200, bbox_inches="tight")

# Plot points behind 1st
fig, ax = plt.subplots()
df_max = cum_df.max(axis=1)
duplicated_max = pd.DataFrame({col: df_max for col in df.columns})
df_diff = cum_df - duplicated_max
df_diff.plot(ax=ax, linewidth=2.5, marker="o", markersize=4, alpha=0.85)
ax.set_title("Points Behind 1st")
ax.set_xlabel("Week Number")
ax.set_ylabel("Points")
ax.xaxis.set_major_locator(MaxNLocator(integer=True))
ax.axhline(y=0, color="gray", linestyle="--", linewidth=1, alpha=0.7)
ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0)
plt.tight_layout()
plt.savefig(image_path("points_behind"), dpi=200, bbox_inches="tight")

# Create statistics graphic
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("League Statistics", fontsize=18, fontweight="bold", y=0.98)

stat_colors = {"avg": "#3498db", "std": "#9b59b6", "best": "#2ecc71", "worst": "#e74c3c"}

# Average weekly score
ax = axes[0, 0]
avg_scores = df.mean().sort_values(ascending=False)
bars = ax.barh(
    avg_scores.index, avg_scores.values, color=stat_colors["avg"], edgecolor="white", linewidth=1.5
)
ax.bar_label(
    bars,
    fmt="%.1f",
    padding=8,
    fontsize=10,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=stat_colors["avg"], alpha=0.9),
)
ax.set_xlabel("Average Points per Week")
ax.set_title("Average Weekly Performance", pad=10)
ax.invert_yaxis()
ax.set_xlim(right=avg_scores.max() * 1.15)

# Standard deviation
ax = axes[0, 1]
std_dev = df.std().sort_values(ascending=False)
bars = ax.barh(
    std_dev.index, std_dev.values, color=stat_colors["std"], edgecolor="white", linewidth=1.5
)
ax.bar_label(
    bars,
    fmt="%.1f",
    padding=8,
    fontsize=10,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=stat_colors["std"], alpha=0.9),
)
ax.set_xlabel("Standard Deviation")
ax.set_title("Consistency (Lower = More Consistent)", pad=10)
ax.invert_yaxis()
ax.set_xlim(right=std_dev.max() * 1.15)

# Best week score
ax = axes[1, 0]
best_scores = df.max().sort_values(ascending=False)
bars = ax.barh(
    best_scores.index,
    best_scores.values,
    color=stat_colors["best"],
    edgecolor="white",
    linewidth=1.5,
)
ax.bar_label(
    bars,
    fmt="%.0f",
    padding=8,
    fontsize=10,
    fontweight="bold",
    bbox=dict(
        boxstyle="round,pad=0.3", facecolor="white", edgecolor=stat_colors["best"], alpha=0.9
    ),
)
ax.set_xlabel("Points")
ax.set_title("Best Week Score", pad=10)
ax.invert_yaxis()
ax.set_xlim(right=best_scores.max() * 1.1)

# Worst week score
ax = axes[1, 1]
worst_scores = df.min().sort_values(ascending=True)
bars = ax.barh(
    worst_scores.index,
    worst_scores.values,
    color=stat_colors["worst"],
    edgecolor="white",
    linewidth=1.5,
)
ax.bar_label(
    bars,
    fmt="%.0f",
    padding=8,
    fontsize=10,
    fontweight="bold",
    bbox=dict(
        boxstyle="round,pad=0.3", facecolor="white", edgecolor=stat_colors["worst"], alpha=0.9
    ),
)
ax.set_xlabel("Points")
ax.set_title("Worst Week Score", pad=10)
ax.invert_yaxis()
ax.set_xlim(right=worst_scores.max() * 1.1)

plt.tight_layout()
plt.savefig(
    image_path("stats"),
    dpi=200,
    bbox_inches="tight",
    facecolor="white",
)
plt.close()
