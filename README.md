# NFL Confidence

This repo is a personal project to help me beat my friends in our [NFL confidence league](#what-is-a-confidence-league). By my assessment, the outcome of a football game is stochastic and the best we can do is assign a probability to a win or loss. This project grabs win probabilities from a few reputable sites (e.g. ESPN, FiveThirtyEight, etc), aggregates them, and greedily assigns a confidence value to each game based on the predicted win probability. Whether I win or lose the league, my friends have named our league "Man vs. Machine" which I would call a success.

NOTE: the main goal here is for me to beat my friends, not to maintain a codebase for public consumption. Feel free to use this code, but beware of low test coverage, no dockerfile/platform issues, minimal documentation, etc.

## Example Run

```
$ python scripts/print_confidence.py --week 5
                   team_a                team_b      predicted_winner  espn_prob  fte_prob   variance  confidence_prob  confidence_rank
0       arizona-cardinals   philadelphia-eagles   philadelphia-eagles      53.60      58.0   4.840000           55.800              4.0
1    tampa-bay-buccaneers       atlanta-falcons  tampa-bay-buccaneers      87.25      82.0   6.890625           84.625             15.0
2        baltimore-ravens    cincinnati-bengals      baltimore-ravens      54.50      60.0   7.562500           57.250              5.0
3           buffalo-bills   pittsburgh-steelers         buffalo-bills      85.95      88.0   1.050625           86.975             16.0
4       carolina-panthers   san-francisco-49ers   san-francisco-49ers      51.20      70.0  88.360000           60.600              7.0
5       minnesota-vikings         chicago-bears     minnesota-vikings      74.95      76.0   0.275625           75.475             13.0
6        cleveland-browns  los-angeles-chargers  los-angeles-chargers      52.10      52.0   0.002500           52.050              2.0
7        los-angeles-rams        dallas-cowboys      los-angeles-rams      74.20      66.0  16.810000           70.100             10.0
8          denver-broncos    indianapolis-colts        denver-broncos      60.15      60.0   0.005625           60.075              6.0
9    new-england-patriots         detroit-lions  new-england-patriots      54.60      55.0   0.040000           54.800              3.0
10      green-bay-packers       new-york-giants     green-bay-packers      86.35      70.0  66.830625           78.175             14.0
11   jacksonville-jaguars        houston-texans  jacksonville-jaguars      72.75      77.0   4.515625           74.875             12.0
12     kansas-city-chiefs     las-vegas-raiders    kansas-city-chiefs      64.20      78.0  47.610000           71.100             11.0
13          new-york-jets        miami-dolphins        miami-dolphins      57.45      64.0  10.725625           60.725              8.0
14     new-orleans-saints      seattle-seahawks    new-orleans-saints      74.55      57.0  77.000625           65.775              9.0
15  washington-commanders      tennessee-titans      tennessee-titans      41.80      59.0  73.960000           50.400              1.0
```

## What is a Confidence League?

Every week, `n` NFL games are played (usually ~16). League participants pick a winner for each game and then rank the games by their confidence in the winner, assigning a confidence value from 1 up to `n` for each game. If your pick wins, then you get the confidence value for that game added to your score. If your pick loses, you get no points for that game. The league participant with the most points at the end of the regular season wins!
