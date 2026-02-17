#!/usr/bin/env python3
"""
Fetch AoE4 game data from AoE4 World API.

Usage:
  python3 scripts/fetch_game_data.py --player-id 17689761 --game-id 182257348 --sig <sig>
  python3 scripts/fetch_game_data.py --player-id 17689761 --list-games --civ english --limit 5
  python3 scripts/fetch_game_data.py --benchmarks
"""

import argparse
import json
import sys
import urllib.request
import ssl
import os

# Fix macOS Python SSL cert issue
ssl_ctx = ssl.create_default_context()
try:
    import certifi
    ssl_ctx.load_verify_locations(certifi.where())
except ImportError:
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

API_BASE = "https://aoe4world.com/api/v0"
HEADERS = {"User-Agent": "Mozilla/5.0 (AoE4Coach/1.0)"}
BENCHMARKS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reference_data", "english_pro_benchmarks.json")


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
        return json.loads(resp.read())


def list_games(player_id, civ=None, limit=10):
    url = f"{API_BASE}/players/{player_id}/games?limit={limit}"
    if civ:
        url += f"&civilization={civ}"
    data = fetch_json(url)
    games = []
    for g in data.get("games", []):
        teams = g.get("teams", [])
        player_team = None
        opponent_team = None
        for team in teams:
            for member in team:
                p = member.get("player", {})
                if p.get("profile_id") == player_id:
                    player_team = p
                else:
                    opponent_team = p
        games.append({
            "game_id": g["game_id"],
            "map": g["map"],
            "duration": g["duration"],
            "started_at": g["started_at"],
            "kind": g["kind"],
            "player": player_team,
            "opponent": opponent_team,
        })
    return {"total": data.get("total_count", 0), "games": games}


def fetch_game_summary(player_id, game_id, sig):
    url = f"https://aoe4world.com/players/{player_id}/games/{game_id}/summary?camelize=true&sig={sig}"
    return fetch_json(url)


def load_benchmarks():
    with open(BENCHMARKS_PATH) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Fetch AoE4 game data")
    parser.add_argument("--player-id", type=int, help="Player profile ID")
    parser.add_argument("--game-id", type=int, help="Game ID for summary")
    parser.add_argument("--sig", help="Signature for game summary API")
    parser.add_argument("--list-games", action="store_true", help="List recent games")
    parser.add_argument("--civ", help="Filter by civilization")
    parser.add_argument("--limit", type=int, default=10, help="Number of games to list")
    parser.add_argument("--benchmarks", action="store_true", help="Print pro benchmarks")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.benchmarks:
        data = load_benchmarks()
        print(json.dumps(data, indent=2))
        return

    if args.list_games:
        if not args.player_id:
            print("Error: --player-id required", file=sys.stderr)
            sys.exit(1)
        data = list_games(args.player_id, args.civ, args.limit)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"Total games: {data['total']}\n")
            for g in data["games"]:
                p = g["player"] or {}
                o = g["opponent"] or {}
                result = p.get("result", "?")
                print(f"  Game {g['game_id']} | {g['map']} | {g['duration']}s | {result}")
                print(f"    {p.get('name','?')} ({p.get('civilization','?')}, {p.get('rating','?')}) vs "
                      f"{o.get('name','?')} ({o.get('civilization','?')}, {o.get('rating','?')})")
                print()
        return

    if args.game_id and args.sig:
        if not args.player_id:
            print("Error: --player-id required", file=sys.stderr)
            sys.exit(1)
        data = fetch_game_summary(args.player_id, args.game_id, args.sig)
        print(json.dumps(data, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
