import argparse
from datetime import datetime

import gspread as gs
import pandas as pd
from loguru import logger
from pydantic import BaseModel, ConfigDict
from pytz import timezone
from tqdm import tqdm

from nfl_confidence.odds import (
    get_the_odds_json,
    get_this_weeks_games,
    parse_the_odds_json,
)
from nfl_confidence.settings import Settings
from nfl_confidence.utils import get_ranks, read_config, update_cell


class ScriptParams(BaseModel):
    week_number: int  # Week number to initialize
    gspread_username: str = "lukeross"  # Username for google sheets account
    sheet_name: str = "Luke NFL Confidence '24-'25"  # Google sheet names to update
    winner_col_name: str = (
        "Predicted Winner"  # Name of the column corresponding to the predicted winner
    )
    confidence_col_name: str = (
        "Confidence Rank"  # Name of the column corresponding to the confidence score
    )
    game_id_col_name: str = "Game ID"  # Name of the column corresponding to the game ID
    max_confidence: int = 16

    model_config = ConfigDict(extra="forbid")


def main(config: ScriptParams):
    # Check the current time
    settings = Settings()
    now = datetime.now(tz=timezone("US/Eastern"))
    date_str = now.strftime("%I:%M on %A, %b %d")
    correct_time = input(f"\n\nIs it curently {date_str}? (y/n) ")
    if correct_time.lower() != "y":
        logger.error("System time is wrong. Please restart")
        exit()

    # Load the spreadsheet object
    gc = gs.service_account(filename=settings.GOOGLE_SHEETS_SECRET_PATH)
    sh = gc.open(config.sheet_name)
    worksheet_name = f"Week {config.week_number}"
    ws = sh.worksheet(worksheet_name)

    # Get the game IDs to update
    df = pd.DataFrame(ws.get_all_records())
    winner_col_idx = list(df.columns).index(config.winner_col_name) + 1  # Account for 1-indexing
    confidence_col_idx = (
        list(df.columns).index(config.confidence_col_name) + 1
    )  # Account for 1-indexing
    game_ids = list(df[config.game_id_col_name])
    total_games = len(game_ids)
    game_ids_to_update = [
        gid
        for gid in game_ids
        if df[df[config.game_id_col_name] == gid][config.winner_col_name] is not None
    ]
    n_existing = total_games - len(game_ids_to_update)
    logger.info(
        f"Found {total_games} total games; {n_existing} already picked, {len(game_ids_to_update)} "
        "to update"
    )
    cont = input(f"\nUpdate {len(game_ids_to_update)} games? (y/n) ")
    if cont.lower() != "y":
        logger.error("Stopping")
        exit()

    # Get Moneyline/Head2head odds
    the_odds_json = get_the_odds_json(
        api_key=settings.THE_ODDS_API_KEY.get_secret_value(), odds_format="american"
    )

    # Parse the response json into GameOdds objects
    games = parse_the_odds_json(the_odds_json=the_odds_json)

    # Filter to only this week's games
    games = get_this_weeks_games(games=games)

    # Compute confidence ranks
    win_probs = [game.win_probability for game in games]
    confidence_ranks = get_ranks(values=win_probs, zero_indexed=False)
    max_conf = max(confidence_ranks)
    confidence_ranks += config.max_confidence - max_conf
    gid2rank = {}
    for game, confidence_rank in zip(games, confidence_ranks):
        gid2rank[game.id] = int(confidence_rank)

    # Loop over games and write confidence scores
    for game_id in tqdm(game_ids_to_update, desc="Writing confidence scores"):
        [row_idx] = df.index[df[config.game_id_col_name] == game_id].tolist()
        row_idx += 2  # Account for 1 indexing and header row
        [game] = [g for g in games if g.id == game_id]
        update_cell(ws=ws, row=row_idx, col=winner_col_idx, value=game.predicted_winner.value)
        update_cell(ws=ws, row=row_idx, col=confidence_col_idx, value=gid2rank[game.id])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config_path",
        type=str,
        default="scripts/initialize_week_sheets.yaml",
        help="Path to the config file",
    )
    args = parser.parse_args()
    config = read_config(args.config_path, ScriptParams)
    main(config)
