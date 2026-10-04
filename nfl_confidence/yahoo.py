import json
import os
import re
import time
from typing import Dict, FrozenSet, List, Optional, Set

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag
from loguru import logger

PICKEM_BASE_URL = "https://football.fantasysports.yahoo.com"
DEFAULT_STATE_PATH = "secrets/yahoo_state.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

# Yahoo serves this page title (with a 200 status) when the request isn't logged in
LOGGED_OUT_TITLE = "There was a Problem"

# Group picks table layout: 3 game header rows (favored, spread, underdog), a column header
# row, then one row per member. Columns are a label, one per game, then the weekly total.
GROUP_PICKS_TABLE_CLASS = "yspNflPickGroupPickTable"
N_GAME_HEADER_ROWS = 4
WINNER_CLASS = "yspNflPickWin"
PICK_CELL_PATTERN = re.compile(r"^(?P<team>\S+)\s*\((?P<confidence>\d+)\)$")

# Columns and types of the picks table from parse_group_picks and get_league_picks. correct
# is nullable, so mean, sum and count skip pending games.
PICK_DTYPES = {
    "week": "int64",
    "team_id": "int64",
    "team_name": "object",
    "game": "int64",
    "n_games": "int64",
    "favorite": "object",
    "underdog": "object",
    "spread": "float64",
    "winner": "object",
    "pick": "object",
    "confidence": "int64",
    "correct": "boolean",
    "points": "float64",
}


def pickem_url(path: str, year: Optional[int] = None) -> str:
    """Build a Pro Football Pick'em URL, optionally for a past season

    Args:
        path (str): Path below /pickem, e.g. "39345/grouppicks"
        year (Optional[int], optional): Past season to fetch. Defaults to None (current season).

    Returns:
        str: Full URL
    """
    year_prefix = f"/{year}" if year is not None else ""
    return f"{PICKEM_BASE_URL}{year_prefix}/pickem/{path}"


def get_session(state_path: str = DEFAULT_STATE_PATH) -> requests.Session:
    """Build a requests session carrying the Yahoo cookies saved by scripts/yahoo_login.py

    Args:
        state_path (str, optional): Path to the Playwright storage state JSON.
            Defaults to DEFAULT_STATE_PATH.

    Returns:
        requests.Session: Session with Yahoo login cookies set
    """
    with open(state_path, "r") as f:
        state = json.load(f)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    for cookie in state["cookies"]:
        session.cookies.set(
            cookie["name"], cookie["value"], domain=cookie["domain"], path=cookie["path"]
        )
    return session


def get_page(session: requests.Session, url: str) -> str:
    """GET a pickem page, raising if the session is no longer logged in

    Args:
        session (requests.Session): Session from get_session
        url (str): Page URL

    Returns:
        str: Page HTML
    """
    response = session.get(url)
    response.raise_for_status()
    title = re.search(r"<title>(.*?)</title>", response.text, re.S)
    if title is not None and LOGGED_OUT_TITLE in title.group(1):
        raise PermissionError(
            f"Not logged in to Yahoo when fetching {url}. Re-run scripts/yahoo_login.py"
        )
    return response.text


def _classes(cell: Tag) -> List[str]:
    return cell.get("class") or []


def get_yahoo_team_names() -> Dict[str, str]:
    """Map Yahoo team abbreviations (e.g. "Sea") to standardized team names
    (e.g. "seattle-seahawks")

    Returns:
        Dict[str, str]: Yahoo abbreviation -> standardized team name
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(current_dir, "assets", "yahoo_team_abbreviations.json"), "r") as f:
        return json.load(f)


def get_current_week(html: str) -> int:
    """Get the week Yahoo selects by default on a group picks page

    Args:
        html (str): HTML of /pickem/{group_id}/grouppicks, without a week param

    Raises:
        ValueError: If the selected week can't be found

    Returns:
        int: Current week number
    """
    soup = BeautifulSoup(html, "html.parser")
    selected = soup.select_one('li.selected a[href*="grouppicks?week="]')
    if selected is None:
        raise ValueError("Couldn't find the selected week on the group picks page")
    return int(re.search(r"week=(\d+)", selected["href"]).group(1))


def _get_table_rows(html: str, week: int) -> List[Tag]:
    table = BeautifulSoup(html, "html.parser").find("table", class_=GROUP_PICKS_TABLE_CLASS)
    if table is None:
        raise ValueError(f"No group picks table found for week {week}")
    return table.find_all("tr")


def _parse_games(rows: List[Tag]) -> List[Dict]:
    favored, spreads, underdogs = [row.find_all("td")[1:-1] for row in rows[:3]]
    games = []
    for favorite_cell, spread_cell, underdog_cell in zip(favored, spreads, underdogs):
        winner = None
        if WINNER_CLASS in _classes(favorite_cell):
            winner = favorite_cell.get_text(strip=True)
        elif WINNER_CLASS in _classes(underdog_cell):
            winner = underdog_cell.get_text(strip=True)
        spread = spread_cell.get_text(strip=True)
        games.append(
            {
                "favorite": favorite_cell.get_text(strip=True),
                "underdog": underdog_cell.get_text(strip=True),
                # Yahoo shows "--" for games without a line yet
                "spread": float(spread) if re.fullmatch(r"[\d.]+", spread) else None,
                "winner": winner,
            }
        )
    return games


def parse_week_games(html: str, week: int) -> pd.DataFrame:
    """Parse the games on a group picks page, including games whose picks are still hidden

    Args:
        html (str): HTML of /pickem/{group_id}/grouppicks?week={week}
        week (int): Week number the page is for

    Returns:
        pd.DataFrame: Columns game, favorite, underdog, spread, winner (None until final)
    """
    games = pd.DataFrame(_parse_games(_get_table_rows(html, week)))
    games.insert(0, "game", range(1, len(games) + 1))
    return games


def _picks_table(records: List[Dict]) -> pd.DataFrame:
    # Fixed columns and types, so an empty table matches a real one
    return pd.DataFrame(records, columns=list(PICK_DTYPES)).astype(PICK_DTYPES)


def parse_group_picks(html: str, week: int) -> pd.DataFrame:
    """Parse a group picks page into one row per (member, game). Skips picks Yahoo hides
    (other members' picks on games that haven't locked; your own row shows yours) and picks
    not made yet. Pending games have correct and points missing.

    Args:
        html (str): HTML of /pickem/{group_id}/grouppicks?week={week}
        week (int): Week number the page is for

    Raises:
        ValueError: If the picks table is missing, or a member's points don't add up to
            the weekly total Yahoo shows

    Returns:
        pd.DataFrame: Columns and types from PICK_DTYPES. Yahoo's confidence values for a
            week run from 1 to n_games, the number of games that week.
    """
    rows = _get_table_rows(html, week)
    games = _parse_games(rows)

    # One row per member, with a pick per game and the weekly total at the end
    records = []
    for row in rows[N_GAME_HEADER_ROWS:]:
        cells = row.find_all("td")
        member_link = cells[0].find("a")
        team_id = int(member_link["href"].rstrip("/").split("/")[-1])
        team_name = member_link.get_text(strip=True)
        yahoo_total = int(cells[-1].get_text(strip=True) or 0)

        member_points = 0
        for game_index, (cell, game) in enumerate(zip(cells[1:-1], games), start=1):
            text = cell.get_text(" ", strip=True)
            if text in ("", "--"):
                continue  # Pick hidden until the game locks, or not made yet
            match = PICK_CELL_PATTERN.match(text)
            if match is None:
                raise ValueError(f"Unrecognized pick cell {text!r} in week {week}")
            confidence = int(match.group("confidence"))
            correct = None
            if "correct" in _classes(cell):
                correct = True
            elif "incorrect" in _classes(cell):
                correct = False
            points = None if correct is None else confidence * correct
            member_points += points or 0
            records.append(
                {
                    "week": week,
                    "team_id": team_id,
                    "team_name": team_name,
                    "game": game_index,
                    "n_games": len(games),
                    **game,
                    "pick": match.group("team"),
                    "confidence": confidence,
                    "correct": correct,
                    "points": points,
                }
            )

        if member_points != yahoo_total:
            raise ValueError(
                f"Week {week} points for {team_name!r} sum to {member_points}, "
                f"but Yahoo shows {yahoo_total}"
            )

    return _picks_table(records)


def get_league_picks(
    session: requests.Session, group_id: int, first_week: int = 1, last_week: int = 18
) -> pd.DataFrame:
    """Fetch and parse every week's group picks, stopping at the first week with no
    visible picks

    Args:
        session (requests.Session): Session from get_session
        group_id (int): Pick'em group ID
        first_week (int, optional): First week to fetch. Defaults to 1.
        last_week (int, optional): Last week to fetch. Defaults to 18.

    Returns:
        pd.DataFrame: All weeks' picks, with the columns from parse_group_picks. Empty if no
            picks are visible.
    """
    weeks = []
    for week in range(first_week, last_week + 1):
        url = pickem_url(f"{group_id}/grouppicks") + f"?week={week}"
        week_df = parse_group_picks(get_page(session, url), week)
        if week_df.empty:
            logger.info(f"No picks visible yet for week {week}, stopping")
            break
        weeks.append(week_df)
        time.sleep(1)  # Go easy on Yahoo
    if not weeks:
        return _picks_table([])
    return pd.concat(weeks, ignore_index=True)


def get_top_picks(picks: pd.DataFrame, team_id: int) -> Dict[str, List[int]]:
    """Get the teams a member has picked at each week's top confidence value, e.g. to avoid
    repeat 16s. The top value is the week's number of games, so 16 normally, and less on
    bye weeks.

    Args:
        picks (pd.DataFrame): Picks from parse_group_picks or get_league_picks
        team_id (int): Member whose picks to check

    Returns:
        Dict[str, List[int]]: Standardized team name -> weeks it was the top pick
    """
    team_names = get_yahoo_team_names()
    matches = picks[(picks.team_id == team_id) & (picks.confidence == picks.n_games)]
    teams_picked = {}
    for pick, week in zip(matches.pick, matches.week):
        teams_picked.setdefault(team_names[pick], []).append(int(week))
    return teams_picked


def get_matchups(week_games: pd.DataFrame) -> List[FrozenSet[str]]:
    """Get each game's pair of standardized team names, e.g. to match against the odds API

    Args:
        week_games (pd.DataFrame): Games from parse_week_games

    Returns:
        List[FrozenSet[str]]: Pair of standardized team names for each game, in order
    """
    team_names = get_yahoo_team_names()
    return [
        frozenset((team_names[favorite], team_names[underdog]))
        for favorite, underdog in zip(week_games.favorite, week_games.underdog)
    ]


def get_locked_picks(
    week_games: pd.DataFrame,
    picks: pd.DataFrame,
    team_id: int,
    open_matchups: Set[FrozenSet[str]],
) -> pd.DataFrame:
    """Find the week's games that can no longer be picked, along with one member's picks on
    them

    Args:
        week_games (pd.DataFrame): Games from parse_week_games
        picks (pd.DataFrame): Picks from parse_group_picks for the same week
        team_id (int): Member whose picks to return
        open_matchups (Set[FrozenSet[str]]): Standardized team name pairs of the games that
            haven't started yet

    Raises:
        ValueError: If an open matchup isn't one of the week's games, or a game that isn't
            open hasn't started either (e.g. the odds API doesn't list it yet). It also
            raises for a game in progress when no other member's pick on it is visible, since
            nothing on the page shows the game has started.

    Returns:
        pd.DataFrame: Locked games, with columns from parse_week_games plus the member's pick,
            confidence, and correct (NaN where the member has no visible pick)
    """
    matchups = get_matchups(week_games)
    unknown = open_matchups - set(matchups)
    if unknown:
        raise ValueError(f"Games not in this Yahoo week: {[sorted(m) for m in unknown]}")

    # Yahoo shows other members' picks once a game locks, and the winner once it's final.
    # The member's own row isn't used, since it may show their picks before games lock.
    other_picks = picks.loc[picks.team_id != team_id, "game"]
    started = week_games.game.isin(other_picks) | week_games.winner.notna()
    is_open = pd.Series(matchups, index=week_games.index).isin(open_matchups)
    missing = week_games[~is_open & ~started]
    if not missing.empty:
        games = ", ".join(f"{game.favorite} vs {game.underdog}" for game in missing.itertuples())
        raise ValueError(
            f"Can't tell whether these games have started: {games}. The odds API doesn't "
            "list them, and Yahoo shows no other member's pick or a result for them yet. If "
            "they haven't kicked off, the odds API hasn't posted them yet, so rerun later. If "
            "they're in progress and nobody else picked them, rerun once they're final"
        )

    locked = week_games[~is_open]
    member_picks = picks.loc[picks.team_id == team_id, ["game", "pick", "confidence", "correct"]]
    return locked.merge(member_picks, on="game", how="left")
