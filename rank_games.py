import os
import json
import argparse
from operator import lt, gt

def main(args):
    # Parse input file
    assert os.path.isfile(args.input_path), "File not found: " + str(args.input_path)
    file_ext = os.path.splitext(args.input_path)[1]
    assert file_ext == ".json", "Unsupported file type: " + str(file_ext)
    with open(args.input_path, 'r') as f:
        games = json.load(f)

    # Sort by sort_field
    team_a_key = "team_a_" + args.sort_field
    team_b_key = "team_b_" + args.sort_field
    if args.sort_field == "spread":
        inv_val = 0.0
        reverse = True
        comp = lt
    elif args.sort_field == "prob":
        inv_val = 1.0
        reverse = False
        comp = gt
    else:
        raise ValueError("Unsupported sort field: " + str(args.sort_field))
    for i in range(len(games)):
        games[i][team_b_key] = inv_val - games[i][team_a_key]
        if comp(games[i][team_a_key], games[i][team_b_key]):
            games[i]["pick"] = games[i]["team_a"]
            games[i][args.sort_field] = games[i][team_a_key]
        else:
            games[i]["pick"] = games[i]["team_b"]
            games[i][args.sort_field] = games[i][team_b_key]
    sorted_ids = [i[0] for i in sorted(enumerate(games), key=lambda x: x[1][args.sort_field], reverse=reverse)]

    # Assign confidence in ascending order
    for confidence, game_id in enumerate(sorted_ids):
        games[game_id]["confidence"] = confidence + 1

    # Print out picks/confidence scores
    if args.print_sorted:
        for game_id in sorted_ids:
            game = games[game_id]
            print("Pick:\t\t" + str(game["pick"]))
            print("Confidence:\t" + str(game["confidence"]))
            print(args.sort_field.title() + ":\t\t" + str(game[args.sort_field]) + "\n")
    else:
        for game in games:
            print("Pick:\t\t" + str(game["pick"]))
            print("Confidence:\t" + str(game["confidence"]))
            print(args.sort_field.title() + ":\t\t" + str(game[args.sort_field]) + "\n")

    # Save out picks/confidence scores
    with open(args.output_path, 'w') as f:
        json.dump(games, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input_path', metavar='i', type=str, default="odds.json", help='input file path'
    )
    parser.add_argument(
        '--output_path', metavar='o', type=str, default="picks.json", help='output file path'
    )
    parser.add_argument(
        '--sort_field', metavar='s', type=str, default="spread", help='metric by which to sort confidence'
    )
    parser.add_argument('--print_sorted', action='store_true')
    args = parser.parse_args()
    main(args)