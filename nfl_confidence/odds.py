import requests


def get_the_odds_json(api_key: str):
    url = "https://api.the-odds-api.com/v3/odds/"
    params = {
        "sport": "americanfootball_nfl",
        "region": "us",
        "apiKey": api_key,
        "mkt": "spreads",
    }
    resp = requests.get(url, params)
    resp.raise_for_status()
    return resp.json()
