import argparse

from nfl_confidence.yahoo import DEFAULT_STATE_PATH, get_league_picks, get_session

# Setup and parse script args
parser = argparse.ArgumentParser(
    description="Show every league member's top confidence pick each week (16, or the number "
    "of games on bye weeks), and call out anyone who has used the same team as a top pick "
    "more than once"
)
parser.add_argument("--group_id", type=int, default=39345, help="Pick'em group ID")
parser.add_argument("--state_path", type=str, default=DEFAULT_STATE_PATH)
args = parser.parse_args()

# Get this season's picks so far. Yahoo's top value each week is the number of games.
session = get_session(args.state_path)
picks = get_league_picks(session, args.group_id)
top_picks = picks[picks.confidence == picks.n_games]

# Each member's pick by week, marked with whether it won
result_marks = top_picks.correct.map({True: " ✓", False: " ✗"}).fillna("")
table = (
    top_picks.assign(cell=top_picks.pick + result_marks)
    .pivot(index="week", columns="team_name", values="cell")
    .reindex(index=sorted(picks.week.unique()), columns=sorted(picks.team_name.unique()))
    .fillna("?")
)

# Label bye weeks with their top value
n_games = picks.groupby("week").n_games.first()
table.index = [
    f"{week} (top={n_games[week]})" if n_games[week] < 16 else week for week in table.index
]

# Season record on top picks. Pending games have correct missing, which sum and count skip.
wins = top_picks.groupby("team_name").correct.sum()
losses = top_picks.groupby("team_name").correct.count() - wins
table.loc["W-L"] = [f"{wins.get(name, 0)}-{losses.get(name, 0)}" for name in table.columns]

print("Top picks by week (? = hidden until the game kicks off)\n")
print(table.to_string(), "\n")

# Call out teams a member has used as a top pick more than once
repeat_weeks = top_picks.groupby(["team_name", "pick"]).week.apply(list)
repeat_weeks = repeat_weeks[repeat_weeks.apply(len) > 1]
if repeat_weeks.empty:
    print("No repeat top picks")
else:
    print("Repeat top picks:")
    for (team_name, pick), weeks in repeat_weeks.items():
        print(f"  {team_name}: {pick} in weeks {', '.join(str(week) for week in weeks)}")
