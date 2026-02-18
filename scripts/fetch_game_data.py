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
import re
import sys
import urllib.request
import urllib.parse
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


def parse_aoe4world_url(url):
    """Parse an AoE4 World game URL into player_id, game_id, sig.
    Example: https://aoe4world.com/players/8354416-EL-loueMT/games/220749753?sig=abc123
    """
    m = re.match(r'https?://aoe4world\.com/players/(\d+)[^/]*/games/(\d+)', url)
    if not m:
        return None
    player_id = int(m.group(1))
    game_id = int(m.group(2))
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    sig = qs.get("sig", [None])[0]
    return {"player_id": player_id, "game_id": game_id, "sig": sig}


def scrape_game_sigs(player_id, player_slug=None, page=1, filter_civ=None):
    """Scrape game IDs and sigs from a player's games page on AoE4 World.
    Only works if the player has public match history enabled.
    If filter_civ is specified, enriches with civ info from API."""
    slug = player_slug or str(player_id)
    url = f"https://aoe4world.com/players/{slug}/games?page={page}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
        html = resp.read().decode()
    # Extract game_id and sig pairs from href attributes
    pattern = re.compile(r'games/(\d+)\?sig=([a-f0-9]+)')
    matches = pattern.findall(html)
    results = [{"game_id": int(gid), "sig": sig} for gid, sig in matches]
    
    # If filtering by civ, fetch game details to get civ info
    if filter_civ and results:
        game_ids = [r["game_id"] for r in results]
        # Fetch games from API to get civ info
        api_url = f"{API_BASE}/players/{player_id}/games?limit=50"
        api_data = fetch_json(api_url)
        games_by_id = {}
        for g in api_data.get("games", []):
            games_by_id[g["game_id"]] = g
        
        filtered = []
        for r in results:
            gid = r["game_id"]
            if gid in games_by_id:
                g = games_by_id[gid]
                for team in g.get("teams", []):
                    for m in team:
                        p = m.get("player", {})
                        if p.get("profile_id") == player_id:
                            if p.get("civilization") == filter_civ:
                                r["civilization"] = filter_civ
                                r["map"] = g.get("map")
                                r["duration"] = g.get("duration")
                                r["result"] = p.get("result")
                                r["rating"] = p.get("rating")
                                filtered.append(r)
                            break
        return filtered
    return results


def load_benchmarks():
    with open(BENCHMARKS_PATH) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Fetch AoE4 game data")
    parser.add_argument("--url", help="AoE4 World game URL (auto-extracts player-id, game-id, sig)")
    parser.add_argument("--player-id", type=int, help="Player profile ID")
    parser.add_argument("--game-id", type=int, help="Game ID for summary")
    parser.add_argument("--sig", help="Signature for game summary API")
    parser.add_argument("--list-games", action="store_true", help="List recent games")
    parser.add_argument("--civ", help="Filter by civilization")
    parser.add_argument("--limit", type=int, default=10, help="Number of games to list")
    parser.add_argument("--benchmarks", action="store_true", help="Print pro benchmarks")
    parser.add_argument("--find-refs", action="store_true", help="Find reference games (losses to higher-rated opponents)")
    parser.add_argument("--compare", action="store_true", help="Extract both players' build orders for comparison")
    parser.add_argument("--scrape-sigs", action="store_true", help="Scrape game sigs from player's games page (requires public match history)")
    parser.add_argument("--player-slug", help="Player slug for scraping (e.g. '8354416-EL-loueMT')")
    parser.add_argument("--filter-civ", help="Filter scraped games by civilization (e.g. 'english')")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    # Auto-extract from URL if provided
    if args.url:
        parsed = parse_aoe4world_url(args.url)
        if not parsed:
            print(f"Error: Could not parse URL: {args.url}", file=sys.stderr)
            sys.exit(1)
        args.player_id = args.player_id or parsed["player_id"]
        args.game_id = args.game_id or parsed["game_id"]
        args.sig = args.sig or parsed["sig"]

    if args.benchmarks:
        data = load_benchmarks()
        print(json.dumps(data, indent=2))
        return

    if args.scrape_sigs:
        slug = args.player_slug or (str(args.player_id) if args.player_id else None)
        if not slug:
            print("Error: --player-id or --player-slug required", file=sys.stderr)
            sys.exit(1)
        sigs = scrape_game_sigs(args.player_id, slug, filter_civ=args.filter_civ)
        if args.json:
            print(json.dumps(sigs, indent=2))
        else:
            print(f"Found {len(sigs)} games with sigs:\n")
            for s in sigs:
                extra = f" | {s.get('map', '?')} | {s.get('result', '?')} | {s.get('rating', '?')}" if args.filter_civ else ""
                print(f"  Game {s['game_id']} | sig={s['sig'][:12]}...{extra}")
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
