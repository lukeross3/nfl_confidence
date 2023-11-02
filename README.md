<h1 align="center">
<p>NFL Confidence
</h1>

<h4 align=center>

![CI Build](https://github.com/lukeross3/nfl_confidence/actions/workflows/ci.yaml/badge.svg)

Bragging Rights 🤝 Software Engineering
</h4>

This repo is a personal project to help me beat my friends in our [NFL confidence league](#what-is-a-confidence-league). This project grabs moneyline odds from the most popular oddsmakers, aggregates them, and greedily assigns a confidence value to each game based on the predicted win probability.

In the 2022-2023 season I won the league and beat Shivam for the 3rd straight year. The league has since been named **"Man vs. Machine"** which I'd call a success in its own right!

## Example Run

```
$ python scripts/print_confidence.py
               home_team              away_team      predicted_winner  prob_variance  oddsmaker_agreement  confidence_prob  confidence_rank
0    pittsburgh-steelers       tennessee-titans   pittsburgh-steelers       0.000037                  1.0         0.576144                8
1     kansas-city-chiefs         miami-dolphins    kansas-city-chiefs       0.000054                  1.0         0.522164                3
2       cleveland-browns      arizona-cardinals      cleveland-browns       0.000024                  1.0         0.754698               15
3        atlanta-falcons      minnesota-vikings       atlanta-falcons       0.000035                  1.0         0.655774               13
4       baltimore-ravens       seattle-seahawks      baltimore-ravens       0.000040                  1.0         0.694440               14
5     new-orleans-saints          chicago-bears    new-orleans-saints       0.000053                  1.0         0.759823               16
6      green-bay-packers       los-angeles-rams     green-bay-packers       0.000015                  1.0         0.599242               10
7         houston-texans   tampa-bay-buccaneers        houston-texans       0.000018                  1.0         0.575376                7
8   new-england-patriots  washington-commanders  new-england-patriots       0.000051                  1.0         0.613363               12
9      carolina-panthers     indianapolis-colts    indianapolis-colts       0.000038                  1.0         0.569476                6
10   philadelphia-eagles         dallas-cowboys   philadelphia-eagles       0.000044                  1.0         0.593731                9
11     las-vegas-raiders        new-york-giants     las-vegas-raiders       0.000034                  1.0         0.530778                4
12    cincinnati-bengals          buffalo-bills    cincinnati-bengals       0.000121                  1.0         0.549072                5
13         new-york-jets   los-angeles-chargers  los-angeles-chargers       0.000126                  1.0         0.613125               11
```

## What is a Confidence League?

Every week, `n` NFL games are played (usually ~16). League participants pick a winner for each game and then rank the games by their confidence in the winner, assigning a confidence value from 1 up to `n` for each game. If your pick wins, then you get the confidence value for that game added to your score. If your pick loses, you get no points for that game. The league participant with the most points at the end of the regular season wins!
