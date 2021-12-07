import requests
from bs4 import BeautifulSoup

from nfl_confidence.html_parsers.utils import convert_percent_to_float


def get_week_538_confidence(week_no: int, skip_errors: bool = False):

    # Get HTML
    url = "https://projects.fivethirtyeight.com/2021-nfl-predictions/games/"
    resp = requests.get(url)
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Filter down to the correct week
    [week_group, _] = soup.findAll(name="div", attrs={"class": "week-group"})
    found_week = False
    for week in week_group:
        week_title = week.findAll(name="h3", string=f"Week {week_no}")
        if len(week_title) == 1:
            found_week = True
            break
    assert found_week, f"Couldn't find week #{week_no} in 538 html"

    # Get probabilities for each game in the week
    out = []
    game_tables = week.findAll(name="table", attrs={"class": "game-body"})
    for game_table in game_tables:
        game_probs = {}
        team_rows = game_table.findAll(name="tr")
        for team_row in team_rows:
            try:
                [team_name] = team_row.findAll(name="td", attrs={"class": "td text team"})
                [team_prob] = team_row.findAll(name="td", attrs={"class": "td number chance"})
            except ValueError as e:
                if skip_errors:
                    continue
                raise e
            game_probs[team_name.text.lower()] = convert_percent_to_float(team_prob.text)
        if len(game_probs) > 0:
            out.append(game_probs)

    return out
