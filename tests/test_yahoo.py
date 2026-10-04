import pandas as pd
import pytest

from nfl_confidence.odds import get_valid_team_names
from nfl_confidence.yahoo import (
    get_current_week,
    get_locked_picks,
    get_matchups,
    get_top_picks,
    get_yahoo_team_names,
    parse_group_picks,
    parse_week_games,
    pickem_url,
)


def test_pickem_url():
    assert (
        pickem_url("39345/grouppicks")
        == "https://football.fantasysports.yahoo.com/pickem/39345/grouppicks"
    )
    assert (
        pickem_url("39345/grouppicks", year=2025)
        == "https://football.fantasysports.yahoo.com/2025/pickem/39345/grouppicks"
    )


def test_parse_group_picks_finished_week(group_picks_week1_html):
    picks = parse_group_picks(group_picks_week1_html, week=1)

    # 6 members x 16 games, all graded
    assert len(picks) == 96
    assert picks.correct.notna().all()
    assert picks.winner.notna().all()
    assert (picks.week == 1).all()
    assert (picks.n_games == 16).all()

    # Weekly totals match what Yahoo showed
    totals = picks.groupby("team_id").points.sum().to_dict()
    assert totals == {1: 69, 2: 90, 3: 101, 4: 91, 5: 93, 6: 95}

    # Each member uses each confidence value once
    for _, member_picks in picks.groupby("team_id"):
        assert sorted(member_picks.confidence) == list(range(1, 17))

    # Spot check one pick
    first = picks[(picks.team_id == 3) & (picks.game == 1)].iloc[0]
    assert first.team_name == "Member 3"
    assert (first.favorite, first.underdog, first.spread) == ("Sea", "NE", 3.5)
    assert (first.winner, first.pick, first.confidence) == ("Sea", "Sea", 8)
    assert first.correct and first.points == 8


def test_parse_group_picks_in_progress_week(group_picks_week4_html):
    picks = parse_group_picks(group_picks_week4_html, week=4)

    # Only the played game's picks are visible, but the game count includes hidden games
    assert len(picks) == 6
    assert (picks.game == 1).all()
    assert (picks.n_games == 16).all()
    assert (picks.winner == "Cle").all()
    assert picks.set_index("team_id").points.to_dict() == {
        1: 3,
        2: 8,
        3: 0,
        4: 0,
        5: 0,
        6: 0,
    }


def test_parse_group_picks_total_mismatch(group_picks_week1_html):
    html = group_picks_week1_html.replace("<strong>101</strong>", "<strong>100</strong>")
    with pytest.raises(ValueError, match="sum to 101"):
        parse_group_picks(html, week=1)


def test_parse_group_picks_no_table():
    with pytest.raises(ValueError, match="No group picks table"):
        parse_group_picks("<html><body>Off to training camp</body></html>", week=1)


def test_yahoo_team_names_cover_all_teams():
    assert set(get_yahoo_team_names().values()) == get_valid_team_names()


def test_get_current_week():
    html = """
    <ul id="ysf-tertiary-week">
      <li class=" first "><a href="/pickem/39345/grouppicks?week=1"><span>1</span></a></li>
      <li class=" selected"><a href="/pickem/39345/grouppicks?week=2"><span>2</span></a></li>
    </ul>
    """
    assert get_current_week(html) == 2
    with pytest.raises(ValueError):
        get_current_week("<html></html>")


def test_parse_week_games(group_picks_week4_html):
    games = parse_week_games(group_picks_week4_html, week=4)
    assert len(games) == 16
    assert list(games.game) == list(range(1, 17))
    assert games.winner.iloc[0] == "Cle"
    assert games.winner.iloc[1:].isna().all()


def test_get_locked_picks(group_picks_week4_html):
    week_games = parse_week_games(group_picks_week4_html, week=4)
    picks = parse_group_picks(group_picks_week4_html, week=4)
    matchups = get_matchups(week_games)
    assert matchups[0] == frozenset(("cleveland-browns", "pittsburgh-steelers"))

    # Only the first game has started
    locked = get_locked_picks(week_games, picks, team_id=3, open_matchups=set(matchups[1:]))
    assert len(locked) == 1
    assert (locked.pick.iloc[0], locked.confidence.iloc[0]) == ("Pit", 5)
    assert not locked.correct.iloc[0]

    # Nothing started yet, and no picks visible
    locked = get_locked_picks(week_games, picks.iloc[0:0], team_id=3, open_matchups=set(matchups))
    assert locked.empty

    # An open game from a different week
    with pytest.raises(ValueError, match="not in this Yahoo week"):
        get_locked_picks(
            week_games,
            picks,
            team_id=3,
            open_matchups={frozenset(("new-york-jets", "new-york-giants"))},
        )

    # The second game has no odds, but hasn't started on Yahoo either
    with pytest.raises(ValueError, match="Can't tell whether these games have started"):
        get_locked_picks(week_games, picks, team_id=3, open_matchups=set(matchups[2:]))

    # The member's own visible pick doesn't mean the game has started
    own_pick = picks[picks.team_id == 3].assign(game=2, pick="Bal", confidence=16)
    with pytest.raises(ValueError, match="Can't tell whether these games have started"):
        get_locked_picks(
            week_games,
            pd.concat([picks, own_pick]),
            team_id=3,
            open_matchups=set(matchups[2:]),
        )


def test_get_locked_picks_game_in_progress(group_picks_week4_html):
    # The first game has kicked off but isn't final: no winner, picks visible but not graded,
    # and no points yet
    live = (
        group_picks_week4_html.replace('class="yspNflPickWin"', "")
        .replace('class="incorrect"', 'class=""')
        .replace('class="ysf-pick-opponent correct"', 'class="ysf-pick-opponent"')
        .replace("<strong>3</strong>", "<strong>0</strong>")
        .replace("<strong>8</strong>", "<strong>0</strong>")
    )
    week_games = parse_week_games(live, week=4)
    picks = parse_group_picks(live, week=4)
    assert week_games.winner.isna().all()
    assert picks.correct.isna().all()
    matchups = get_matchups(week_games)

    # Other members' visible picks show it has started
    locked = get_locked_picks(week_games, picks, team_id=3, open_matchups=set(matchups[1:]))
    assert len(locked) == 1
    assert (locked.pick.iloc[0], locked.confidence.iloc[0]) == ("Pit", 5)
    assert pd.isna(locked.correct.iloc[0])

    # With no other member's pick visible, it can't tell the game started, so it fails loudly
    with pytest.raises(ValueError, match="Can't tell whether these games have started"):
        get_locked_picks(
            week_games, picks[picks.team_id == 3], team_id=3, open_matchups=set(matchups[1:])
        )


def test_get_top_picks(group_picks_week1_html):
    week1 = parse_group_picks(group_picks_week1_html, week=1)
    assert get_top_picks(week1, team_id=3) == {"los-angeles-chargers": [1]}

    # The same pick at 16 in a second week is a repeat
    two_weeks = pd.concat([week1, week1.assign(week=2)])
    assert get_top_picks(two_weeks, team_id=3) == {"los-angeles-chargers": [1, 2]}

    # On a 15-game bye week, the top pick is the one at 15
    bye_week = pd.DataFrame(
        {
            "week": [5, 5],
            "team_id": [3, 3],
            "pick": ["KC", "LAC"],
            "confidence": [15, 14],
            "n_games": [15, 15],
        }
    )
    assert get_top_picks(pd.concat([week1, bye_week]), team_id=3) == {
        "los-angeles-chargers": [1],
        "kansas-city-chiefs": [5],
    }
    repeat_on_bye_week = bye_week.assign(confidence=[14, 15])
    assert get_top_picks(pd.concat([week1, repeat_on_bye_week]), team_id=3) == {
        "los-angeles-chargers": [1, 5]
    }

    assert get_top_picks(pd.DataFrame(), team_id=3) == {}
