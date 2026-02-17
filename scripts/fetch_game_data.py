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


def find_reference_games(player_id, rating_diff_min=30, rating_diff_max=200, limit=50):
    """Find games where the player lost to a higher-rated opponent.
    These are ideal reference games: the opponent's build order is accessible
    via the player's own sig, and represents 'next level' play."""
    data = list_games(player_id, limit=limit)
    refs = []
    for g in data["games"]:
        p = g.get("player") or {}
        o = g.get("opponent") or {}
        p_rating = p.get("rating") or 0
        o_rating = o.get("rating") or 0
        diff = o_rating - p_rating
        if p.get("result") == "loss" and rating_diff_min <= diff <= rating_diff_max:
            refs.append({
                "game_id": g["game_id"],
                "map": g["map"],
                "duration": g["duration"],
                "player_civ": p.get("civilization"),
                "player_rating": p_rating,
                "opponent_name": o.get("name"),
                "opponent_civ": o.get("civilization"),
                "opponent_rating": o_rating,
                "rating_diff": diff,
            })
    return refs


def extract_comparison(summary, player_id):
    """Extract both players' build orders from a game summary for comparison."""
    players = summary.get("players", [])
    mine = None
    theirs = None
    for p in players:
        pid = p.get("profileId") or p.get("profile_id")
        bo = p.get("buildOrder") or p.get("build_order", [])
        info = {
            "name": p.get("name"),
            "profile_id": pid,
            "civilization": p.get("civilization"),
            "build_order_items": len(bo),
            "build_order": bo,
        }
        # Extract villager timings
        for item in bo:
            icon = item.get("icon", "")
            if "villager" in icon:
                info["villager_finished_times"] = item.get("finished", [])
                break
        if pid == player_id:
            mine = info
        else:
            theirs = info
    return {"player": mine, "opponent": theirs}


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
    parser.add_argument("--find-refs", action="store_true", help="Find reference games (losses to higher-rated opponents)")
    parser.add_argument("--compare", action="store_true", help="Extract both players' build orders for comparison")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.benchmarks:
        data = load_benchmarks()
        print(json.dumps(data, indent=2))
        return

    if args.find_refs:
        if not args.player_id:
            print("Error: --player-id required", file=sys.stderr)
            sys.exit(1)
        refs = find_reference_games(args.player_id, limit=args.limit)
        if args.json:
            print(json.dumps(refs, indent=2))
        else:
            print(f"Reference games (losses to higher-rated opponents):\n")
            for r in refs:
                print(f"  Game {r['game_id']} | {r['map']} | {r['duration']}s")
                print(f"    You ({r['player_civ']}, {r['player_rating']}) vs "
                      f"{r['opponent_name']} ({r['opponent_civ']}, {r['opponent_rating']}) [+{r['rating_diff']}]")
                print()
            if not refs:
                print("  No reference games found. Try increasing --limit.")
        return

    if args.compare:
        if not (args.player_id and args.game_id and args.sig):
            print("Error: --player-id, --game-id, and --sig required for --compare", file=sys.stderr)
            sys.exit(1)
        summary = fetch_game_summary(args.player_id, args.game_id, args.sig)
        comparison = extract_comparison(summary, args.player_id)
        print(json.dumps(comparison, indent=2))
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
