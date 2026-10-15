<h1 align="center">
  NFL Confidence
</h1>

<h4 align=center>
  
  ![CI Build](https://github.com/lukeross3/nfl_confidence/actions/workflows/ci.yaml/badge.svg)

</h4>

This repo is a personal project to help me beat my friends in our [NFL confidence league](#what-is-a-confidence-league). This project grabs moneyline odds from a few popular oddsmakers, aggregates them, and greedily assigns a confidence value to each game based on the predicted win probability.

Using this strategy, I've won the league the last 2 seasons (2022-2023 and 2023-2024) and beat Shivam for the 4th straight year. The league has since been named **"Man vs. Machine"** which I'd call a success in its own right!

## Example Run

```
$ python scripts/print_confidence.py
               home_team              away_team      predicted_winner  confidence_prob  confidence_rank
0    pittsburgh-steelers       tennessee-titans   pittsburgh-steelers         0.576144                8
1     kansas-city-chiefs         miami-dolphins    kansas-city-chiefs         0.522164                3
2       cleveland-browns      arizona-cardinals      cleveland-browns         0.754698               15
3        atlanta-falcons      minnesota-vikings       atlanta-falcons         0.655774               13
4       baltimore-ravens       seattle-seahawks      baltimore-ravens         0.694440               14
5     new-orleans-saints          chicago-bears    new-orleans-saints         0.759823               16
6      green-bay-packers       los-angeles-rams     green-bay-packers         0.599242               10
7         houston-texans   tampa-bay-buccaneers        houston-texans         0.575376                7
8   new-england-patriots  washington-commanders  new-england-patriots         0.613363               12
9      carolina-panthers     indianapolis-colts    indianapolis-colts         0.569476                6
10   philadelphia-eagles         dallas-cowboys   philadelphia-eagles         0.593731                9
11     las-vegas-raiders        new-york-giants     las-vegas-raiders         0.530778                4
12    cincinnati-bengals          buffalo-bills    cincinnati-bengals         0.549072                5
13         new-york-jets   los-angeles-chargers  los-angeles-chargers         0.613125               11
```

This run doesn't use `--yahoo`, so values count down from 16 (`--max_confidence`). Yahoo uses 1 up to the number of games, so in a bye week use `--yahoo` or pass `--max_confidence` with that week's game count.

## Yahoo Pick'em

Our league runs on Yahoo Pick'em, which has no API, so these scripts read the league's pages using your own Yahoo login.

1. Log in once with `python scripts/yahoo_login.py`. It opens Chrome; sign in, and your session is saved to `secrets/`. Run it again whenever a script says your session has expired.
2. Run `python scripts/print_confidence.py --yahoo` to make your picks, even mid-week. It skips the confidence values you've already used on games that have started, and warns you if your top pick repeats a team you've used as a top pick before.

Two more scripts look at the whole league's season so far:

- `python scripts/print_top_picks.py` shows everyone's top pick each week and calls out repeats.
- `python scripts/get_league_picks.py` saves every pick to `results/league_picks_<season>.csv`.

## What is a Confidence League?

Every week, `n` NFL games are played (at most 16). League participants pick a winner for each game and then rank the games by their confidence in the winner, giving each game a different confidence value from `1` up to `n`. If your pick wins, then you get the confidence value for that game added to your score. If your pick loses, you get no points for that game. The league participant with the most points at the end of the regular season wins!

Our league adds one rule: you can't use the same team as your top pick (usually your 16) more than once a season.
