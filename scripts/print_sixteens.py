import argparse

from nfl_confidence.yahoo import DEFAULT_STATE_PATH, get_league_picks, get_session

# Setup and parse script args
parser = argparse.ArgumentParser(
    description="Show every league member's top confidence pick each week, and call out "
    "anyone who has used the same team at the top confidence value more than once"
)
parser.add_argument("--group_id", type=int, default=39345, help="Pick'em group ID")
parser.add_argument(
    "--max_confidence", type=int, default=16, help="Confidence value to show picks for"
)
parser.add_argument("--state_path", type=str, default=DEFAULT_STATE_PATH)
args = parser.parse_args()

# Get this season's picks so far
session = get_session(args.state_path)
picks = get_league_picks(session, args.group_id)
sixteens = picks[picks.confidence == args.max_confidence]

# Each member's pick by week, marked with whether it won
result_marks = sixteens.correct.map({True: " ✓", False: " ✗"}).fillna("")
table = (
    sixteens.assign(cell=sixteens.pick + result_marks)
    .pivot(index="week", columns="team_name", values="cell")
    .reindex(index=sorted(picks.week.unique()), columns=sorted(picks.team_name.unique()))
    .fillna("?")
)

# Season record at the top confidence value
finished = sixteens[sixteens.correct.notna()].astype({"correct": bool})
wins = finished.groupby("team_name").correct.sum()
losses = finished.groupby("team_name").correct.size() - wins
table.loc["W-L"] = [f"{wins.get(name, 0)}-{losses.get(name, 0)}" for name in table.columns]

print(f"{args.max_confidence}-point picks (? = hidden until the game kicks off)\n")
print(table.to_string(), "\n")

# Call out teams a member has used at the top value more than once
repeat_weeks = sixteens.groupby(["team_name", "pick"]).week.apply(list)
repeat_weeks = repeat_weeks[repeat_weeks.apply(len) > 1]
if repeat_weeks.empty:
    print(f"No repeat {args.max_confidence}s")
else:
    print(f"Repeat {args.max_confidence}s:")
    for (team_name, pick), weeks in repeat_weeks.items():
        print(f"  {team_name}: {pick} in weeks {', '.join(str(week) for week in weeks)}")
