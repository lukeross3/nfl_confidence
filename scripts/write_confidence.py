import argparse

import gspread as gs
import pandas as pd

from nfl_confidence.utils import get_ranks, get_secret_key_path

parser = argparse.ArgumentParser(description="Args for computing confidence rankings")
parser.add_argument(
    "--secret_dir",
    metavar="d",
    type=str,
    required=False,
    default="secrets",
    help="Directory containing google sheets secret",
)
parser.add_argument(
    "--username",
    metavar="u",
    type=str,
    default="lukeross",
    help="Username for google sheets account",
)
parser.add_argument(
    "--sheet",
    metavar="s",
    type=str,
    required=False,
    default="Luke Confidence 21-22",
    help="Sheet name under the account",
)
parser.add_argument(
    "--worksheet",
    metavar="w",
    type=str,
    required=False,
    default="Week 9",
    help="Worksheet name within the given sheet",
)
parser.add_argument(
    "--max_confidence",
    metavar="m",
    type=int,
    required=False,
    default=16,
    help="Maximum confidence value for the week",
)
args = parser.parse_args()

# Read sheet as a Pandas DF
print("Reading google sheet...")
secret_path = get_secret_key_path(directory=args.secret_dir, username=args.username)
gc = gs.service_account(filename=secret_path)
sh = gc.open(args.sheet)
ws = sh.worksheet(args.worksheet)
df = pd.DataFrame(ws.get_all_records())

# Compute confidence from "avg" column
print("Computing confidence...")
df["confidence"] = get_ranks(values=df.avg, zero_indexed=False)

# Adjust confidence so that max is 16
max_conf = max(df.confidence)
df.confidence += args.max_confidence - max_conf

# Update the sheet
print("Writing results...")
ws.update([df.columns.values.tolist()] + df.values.tolist())
print("Done!")
