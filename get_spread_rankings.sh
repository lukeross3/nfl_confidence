# Get spreads in odds.json file
python3 update_odds.py \
    --aggregator median \
    --config_path config.json \
    --output_path odds.json

# Rank confidence according to spreads
python3 rank_games.py \
    --input_path odds.json \
    --output_path picks.json \
    --sort_field spread \
    --print_sorted