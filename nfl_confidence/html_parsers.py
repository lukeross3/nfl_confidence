import re

import requests
from bs4 import BeautifulSoup


def convert_percent_to_float(percent_str: str):
    assert percent_str[-1] == "%"
    return float(percent_str[:-1])


def find_percent_in_html(soup: BeautifulSoup, class_value: str):
    [percent_tag] = soup.findAll(name="span", attrs={"class": class_value})
    percent = convert_percent_to_float(percent_tag.text)
    return percent


def get_team_name(soup: BeautifulSoup, home: bool = True):

    # Home vs away case
    if home:
        team_class = "team home"
    else:
        team_class = "team away"

    # Get team name from html
    [team_div] = soup.findAll(name="div", attrs={"class": team_class})
    [team_name_a] = team_div.findAll(name="a", attrs={"class": "team-name"})
    team_url = team_name_a["href"]
    url_parts = team_url.split("/")
    team_name = url_parts[-1]

    # Edge case for trailing slash
    if team_name == "":
        team_name = url_parts[-2]

    return team_name


def get_espn_confidence(game_id: int):

    # Get HTML
    url = f"https://www.espn.com/nfl/game/_/gameId/{game_id}"
    resp = requests.get(url)
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Get the home/away team win %
    try:
        home_percent = find_percent_in_html(soup=soup, class_value="value-home")
        away_percent = find_percent_in_html(soup=soup, class_value="value-away")
    except AssertionError:
        raise RuntimeError(
            f"Couldn't find win percentages for game ID {game_id}. Please check that the game "
            f"exists and has not been played yet: {url}"
        )

    # Adjust for tie %
    tie_percent = 100 - (home_percent + away_percent)
    home_percent += tie_percent / 2
    away_percent += tie_percent / 2

    # Get team names
    home_team = get_team_name(soup, home=True)
    away_team = get_team_name(soup, home=False)

    return {home_team: round(home_percent, 2), away_team: round(away_percent, 2)}


def get_espn_game_ids(week_no: int):

    # Get HTML
    url = "https://www.espn.com/nfl/schedule"
    resp = requests.get(url)
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Check the week is correct
    [button] = soup.findAll(
        name="button", attrs={"class": "button button-filter dropdown-toggle sm selected-date"}
    )
    # TODO: No text in button?

    # Get the game IDs
    game_ids = []
    game_links = soup.findAll(attrs={"href": re.compile(r"/nfl/game/_/gameId/\d+")})
    for game_link in game_links:
        game_id = int(re.search(r"\d+", game_link["href"]).group(0))
        game_ids.append(game_id)
    return game_ids


def get_week_espn_confidence(week_no: int):
    game_ids = get_espn_game_ids(week_no=week_no)
    return [get_espn_confidence(game_id=game_id) for game_id in game_ids]


import json
confidences = get_week_espn_confidence(1000)
print(json.dumps(confidences, indent=4))
