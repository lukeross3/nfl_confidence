import argparse

import pandas as pd
import numpy as np

from nfl_confidence.html_parsers.espn import get_week_espn_confidence
from nfl_confidence.html_parsers.fte import get_week_538_confidence
from nfl_confidence.utils import get_ranks, load_team_name_map

parser = argparse.ArgumentParser(description="Args for computing confidence rankings")
parser.add_argument(
    "--week",
    metavar="w",
    type=int,
    required=True,
    help="Week Number",
)
parser.add_argument(
    "--alpha",
    metavar="a",
    type=float,
    required=False,
    default=0.5,
    help="Averaging factor",
)
parser.add_argument(
    "--max_confidence",
    metavar="m",
    type=int,
    required=False,
    default=16,
    help="Maximum confidence value for the week",
)
parser.add_argument("--skip_errors", dest="skip_errors", action="store_true")
parser.set_defaults(skip_errors=False)
args = parser.parse_args()

# Get confidence rankings
espn_confidence = get_week_espn_confidence(args.week, skip_errors=args.skip_errors)
# fte_confidence = get_week_538_confidence(args.week, skip_errors=args.skip_errors)

# Re-map names
nickname_to_official = load_team_name_map()
for conf_list in [espn_confidence]:#, fte_confidence]:
    for i in range(len(conf_list)):
        for team_name in conf_list[i].keys():
            conf_list[i][nickname_to_official[team_name]] = conf_list[i].pop(team_name)

# Get any extra games missed by either source
espn_games = set([frozenset(game.keys()) for game in espn_confidence])
# fte_games = set([frozenset(game.keys()) for game in fte_confidence])
# espn_missing = fte_games - espn_games
# fte_missing = espn_games - fte_games
# for missing_games, conf_list in zip([espn_missing, fte_missing], [espn_confidence, fte_confidence]):
#     for missing_game in missing_games:
#         conf_list.append({team: None for team in missing_game})

# Sort games for every confidence source
espn_confidence = sorted(espn_confidence, key=lambda x: sorted(list(x.keys()))[0])
# fte_confidence = sorted(fte_confidence, key=lambda x: sorted(list(x.keys()))[0])
fte_confidence = espn_confidence

# Compute winners and averaged probabilities
espn_probs = []
fte_probs = []
variance = []
confidence_probs = []
predicted_winners = []
for i in range(len(espn_confidence)):
    team_a = list(espn_confidence[i].keys())[0]
    team_b = list(espn_confidence[i].keys())[1]
    if espn_confidence[i][team_a] is None:
        confidence_probs.append(-1)
        predicted_winners.append(-1)
    else:
        team_a_prob = (
            args.alpha * espn_confidence[i][team_a] + (1 - args.alpha) * fte_confidence[i][team_a]
        )
        team_b_prob = (
            args.alpha * espn_confidence[i][team_b] + (1 - args.alpha) * fte_confidence[i][team_b]
        )
        assert team_a_prob + team_b_prob == 100
        winner = team_a if team_a_prob >= team_b_prob else team_b
        confidence_probs.append(max(team_a_prob, team_b_prob))
        espn_probs.append(espn_confidence[i][winner])
        fte_probs.append(fte_confidence[i][winner])
        variance.append(np.var([espn_probs[-1], fte_probs[-1]]))
        predicted_winners.append(winner)

# Compute confidence ranks
confidence_ranks = get_ranks(values=confidence_probs, zero_indexed=False)
max_conf = max(confidence_ranks)
confidence_ranks += args.max_confidence - max_conf

# Create pandas dataframe
df = pd.DataFrame(
    {
        "team_a": [list(game.keys())[0] for game in espn_confidence],
        "team_b": [list(game.keys())[1] for game in espn_confidence],
        "predicted_winner": predicted_winners,
        "espn_prob": espn_probs,
        "fte_prob": fte_probs,
        "variance": variance,
        "confidence_prob": confidence_probs,
        "confidence_rank": confidence_ranks,
    }
)

# Set None values for games that already happened
df.loc[df.predicted_winner == -1, "confidence_prob"] = None
df.loc[df.predicted_winner == -1, "confidence_rank"] = None
df.loc[df.predicted_winner == -1, "predicted_winner"] = None

# Display the data frame
print(df)
