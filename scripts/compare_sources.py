import gspread as gs
import pandas as pd

from nfl_confidence.utils import get_ranks, get_secret_key_path

secret_path = get_secret_key_path(directory="secrets", username="lukeross")
gc = gs.service_account(filename=secret_path)
sh = gc.open("Luke Confidence 21-22")

for mu in [0.0, 0.25, 0.5, 0.75, 1.0]:
    score = 0
    weeks = [f"Week {n+1}" for n in range(4)]
    for week in weeks:
        ws = sh.worksheet(week)
        df = pd.DataFrame(ws.get_all_records())
        df["weighted_avg"] = mu * df["espn"] + (1 - mu) * df["538"]
        df["weighted_confidence"] = get_ranks(values=df.weighted_avg, zero_indexed=False)
        week_score = sum(df["weighted_confidence"] * df["was_correct"])
        score += week_score
    print(f"mu: {mu}; score: {score}")
