import re

import requests
from bs4 import BeautifulSoup

from nfl_confidence.html_parsers.utils import convert_percent_to_float


def find_percent_in_html(soup: BeautifulSoup, class_value: str):
    [percent_tag] = soup.findAll(name="div", attrs={"class": class_value})
    percent = convert_percent_to_float(percent_tag.text)
    return percent


def get_team_name(soup: BeautifulSoup, home: bool = True):

    # Home vs away case
    if home:
        team_class = "Gamestrip__Team--home"
    else:
        team_class = "Gamestrip__Team--away"

    # Get team name from html
    [team_div] = soup.select(f'div[class*="{team_class}"]')
    [team_name_a] = team_div.findAll(name="a", attrs={"class": "AnchorLink truncate"})
    team_url = team_name_a["href"]
    url_parts = team_url.split("/")
    team_name = url_parts[-1]

    # Edge case for trailing slash
    if team_name == "":
        team_name = url_parts[-2]

    return team_name


def get_espn_confidence(game_id: int, skip_errors: bool = False):

    # Wrap in try block
    try:
        # Get HTML
        url = f"https://www.espn.com/nfl/game/_/gameId/{game_id}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'}
        resp = requests.get(url, headers=headers)  # Need to specify User-Agent in req to avoid 403
        resp.raise_for_status()
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        # Get team names
        home_team = get_team_name(soup, home=True)
        away_team = get_team_name(soup, home=False)

        # Get the home/away team win %
        away_class = "matchupPredictor__teamValue matchupPredictor__teamValue--b left-0 top-0 flex items-baseline absolute copy"  # noqa: E501
        home_class = "matchupPredictor__teamValue matchupPredictor__teamValue--a bottom-0 right-0 flex items-baseline absolute copy"  # noqa: E501
        home_percent = find_percent_in_html(soup=soup, class_value=home_class)
        away_percent = find_percent_in_html(soup=soup, class_value=away_class)

        # Adjust for tie %
        tie_percent = 100 - (home_percent + away_percent)
        home_percent += tie_percent / 2
        away_percent += tie_percent / 2

        return {home_team: round(home_percent, 2), away_team: round(away_percent, 2)}

    # Except if skipping errors
    except Exception as e:
        if skip_errors:
            return {}
        raise e


def get_espn_game_ids(week_no: int, year: int = 2023):

    # Get HTML
    url = f"https://www.espn.com/nfl/schedule/_/week/{week_no}/year/{year}/seasontype/2"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'}
    resp = requests.get(url, headers=headers)  # Need to specify User-Agent in req to avoid 403
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Get the game IDs
    game_ids = []
    game_links = soup.findAll(attrs={"href": re.compile(r"\/nfl\/game\?gameId=\d+")})
    for game_link in game_links:
        game_id = int(re.search(r"\d+", game_link["href"]).group(0))
        game_ids.append(game_id)
    return game_ids


def get_week_espn_confidence(week_no: int, skip_errors: bool = False):
    game_ids = get_espn_game_ids(week_no=week_no)
    confidences = [
        get_espn_confidence(game_id=game_id, skip_errors=skip_errors) for game_id in game_ids
    ]
    return list(filter(lambda x: len(x) > 0, confidences))
