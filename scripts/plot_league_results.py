import os

import matplotlib.pyplot as plt
import pandas as pd

year = 2023

# Get raw result
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.join(script_dir, os.path.pardir)
csv_path = os.path.join(project_dir, "results", f"league_results_{year}.csv")
df = pd.read_csv(csv_path, sep="\t")
df.index = pd.RangeIndex(start=1, stop=len(df) + 1)

# Plot weekly results
plt.figure()
df.plot()
plt.title("Points Per Week")
plt.xlabel("Week Number")
plt.ylabel("Points")
plt.savefig(os.path.join(project_dir, "images", f"weekly_{year}.png"), dpi=200)

# Plot histogram of weekly scores
plt.figure()
# for col in df.columns:
#     plt.hist(df[col], label=col, alpha=0.5, bins=40)
# plt.legend(loc="best")
axes = df.hist(sharex=True, sharey=True, alpha=0.75)
for ax in axes.flatten():
    ax.set_xlabel("Points Per Week")
    ax.set_ylabel("Frequency")
plt.savefig(os.path.join(project_dir, "images", f"weekly_hist_{year}.png"), dpi=200)

# Plot cumulative results
plt.figure()
new_row = pd.DataFrame({col: 0 for col in df.columns}, index=[0])
df = pd.concat([new_row, df]).reset_index(drop=True)
df.cumsum().plot()
plt.title("Total Points")
plt.xlabel("Week Number")
plt.ylabel("Points")
plt.savefig(os.path.join(project_dir, "images", f"total_{year}.png"), dpi=200)

# Plot points behind 1st
plt.figure()
cum_df = df.cumsum()
df_max = cum_df.max(axis=1)
duplicated_max = pd.DataFrame({col: df_max for col in df.columns})
df_diff = cum_df - duplicated_max
df_diff.plot()
plt.title("Points Behind 1st")
plt.xlabel("Week Number")
plt.ylabel("Points")
plt.savefig(os.path.join(project_dir, "images", f"points_behind_{year}.png"), dpi=200)
