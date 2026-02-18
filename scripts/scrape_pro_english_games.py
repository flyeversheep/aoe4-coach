#!/usr/bin/env python3
"""
Scrape English civilization games from pro players.

This script attempts to find pro players by:
1. Using known profile IDs from the database
2. Trying common player slug formats
3. Falling back to API queries

Usage:
  python3 scripts/scrape_pro_english_games.py
"""

import json
import re
import urllib.request
import urllib.parse
import ssl
import os
import time
from typing import List, Dict, Optional

# Fix macOS Python SSL cert issue
ssl_ctx = ssl.create_default_context()
try:
    import certifi
    ssl_ctx.load_verify_locations(certifi.where())
except ImportError:
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

HEADERS = {"User-Agent": "Mozilla/5.0 (AoE4Coach/1.0)"}
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reference_data")

# Known pro players with their profile IDs and Steam IDs
PRO_PLAYERS = [
    {"name": "VortiX", "profile_id": 60328, "steam_id": "76561198102723093"},
    {"name": "May", "profile_id": 10307814, "steam_id": "76561199070324001"},
    {"name": "燕子宇", "profile_id": 11018483, "steam_id": "76561198999425944"},  # YanZiYu
    {"name": "Starflark", "profile_id": 4703134, "steam_id": "76561199126113201"},
    {"name": "loueMT", "profile_id": 8354416, "steam_id": "76561198961787821"},
]


def try_find_profile_id(player_name: str, slugs: List[str]) -> Optional[Dict]:
    """Try to find a player's profile ID by attempting various slug formats."""

    # Try each slug
    for slug in slugs:
        # Try direct player page
        url = f"https://aoe4world.com/players/{slug}"
        print(f"    Trying: {url}")
        req = urllib.request.Request(url, headers=HEADERS)

        try:
            with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
                html = resp.read().decode()

                # Try to extract profile ID from the page
                # Look for patterns like "profile_id": 12345 or in the URL
                id_match = re.search(r'"profile_id":\s*(\d+)', html)
                if id_match:
                    profile_id = int(id_match.group(1))
                    # Try to get steam_id too
                    steam_match = re.search(r'"steam_id":\s*"(\d+)"', html)
                    steam_id = steam_match.group(1) if steam_match else ""

                    # Try to get the actual name
                    name_match = re.search(r'"name":\s*"([^"]+)"', html)
                    actual_name = name_match.group(1) if name_match else player_name

                    return {
                        "name": actual_name,
                        "profile_id": profile_id,
                        "steam_id": steam_id,
                        "slug": slug
                    }
        except Exception as e:
            # This URL didn't work, try next one
            continue

    return None


def get_player_info(profile_id: int) -> Optional[Dict]:
    """Get player info from AoE4 World API."""
    url = f"https://aoe4world.com/api/v0/players/{profile_id}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
            data = json.loads(resp.read())
            return {
                "name": data.get("name"),
                "profile_id": data.get("profile_id"),
                "steam_id": data.get("steam_id")
            }
    except Exception as e:
        print(f"    Error fetching player info: {e}")
        return None


def scrape_games_with_sigs(profile_id: int, steam_id: str, filter_civ: str = "english") -> List[Dict]:
    """Scrape game IDs and sigs from a player's games page on AoE4 World."""
    all_games = []
    page = 1

    # Try different slug formats
    slugs_to_try = [
        f"{profile_id}-{steam_id}" if steam_id else "",
        str(profile_id)
    ]

    for player_slug in slugs_to_try:
        if not player_slug:
            continue

        print(f"    Trying slug: {player_slug}")
        all_games = []
        page = 1

        while True:
            # URL encode the slug to handle special characters
            encoded_slug = urllib.parse.quote(player_slug, safe='')
            url = f"https://aoe4world.com/players/{encoded_slug}/games?page={page}"
            req = urllib.request.Request(url, headers=HEADERS)

            try:
                with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
                    html = resp.read().decode()

                # Extract game_id and sig pairs from href attributes
                pattern = re.compile(r'games/(\d+)\?sig=([a-f0-9]+)')
                matches = pattern.findall(html)

                if not matches:
                    # No more games found
                    break

                page_games = [{"game_id": int(gid), "sig": sig} for gid, sig in matches]

                # Fetch game details from API to get civ info
                if page_games:
                    api_url = f"https://aoe4world.com/api/v0/players/{profile_id}/games?limit=50&page={page}"
                    api_req = urllib.request.Request(api_url, headers=HEADERS)

                    try:
                        with urllib.request.urlopen(api_req, timeout=15, context=ssl_ctx) as api_resp:
                            api_data = json.loads(api_resp.read())

                        games_by_id = {}
                        for g in api_data.get("games", []):
                            games_by_id[g["game_id"]] = g

                        for game_data in page_games:
                            gid = game_data["game_id"]
                            if gid in games_by_id:
                                g = games_by_id[gid]
                                for team in g.get("teams", []):
                                    for m in team:
                                        p = m.get("player", {})
                                        if p.get("profile_id") == profile_id:
                                            if p.get("civilization") == filter_civ:
                                                all_games.append({
                                                    "game_id": gid,
                                                    "sig": game_data["sig"],
                                                    "url": f"https://aoe4world.com/players/{profile_id}/games/{gid}?sig={game_data['sig']}",
                                                    "map": g.get("map"),
                                                    "duration": g.get("duration"),
                                                    "result": p.get("result"),
                                                    "rating": p.get("rating"),
                                                    "player_id": profile_id
                                                })
                                            break
                    except Exception as e:
                        print(f"      Error fetching API data for page {page}: {e}")

                page += 1

                # Safety limit
                if page > 20:
                    print(f"      Reached page limit (20)")
                    break

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                print(f"      Error scraping page {page}: {e}")
                break

        if all_games:
            break  # Found games with this slug, don't try others

    return all_games


def save_games(games: List[Dict], profile_id: int, player_name: str) -> str:
    """Save games to JSON file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = os.path.join(OUTPUT_DIR, f"english_games_{profile_id}.json")

    with open(filename, 'w') as f:
        json.dump(games, f, indent=2)

    return filename


def main():
    results = []

    print("Scraping English games from pro players...")
    print("=" * 60)

    for player_data in PRO_PLAYERS:
        player_name = player_data["name"]
        profile_id = player_data["profile_id"]
        steam_id = player_data.get("steam_id", "")

        print(f"\nProcessing: {player_name} (Profile ID: {profile_id})")

        print(f"  Scraping English games...")

        # Scrape English games
        games = scrape_games_with_sigs(profile_id, steam_id, filter_civ="english")

        if games:
            # Save to file
            filepath = save_games(games, profile_id, player_name)
            print(f"  ✓ Found {len(games)} English games")
            print(f"  ✓ Saved to: {filepath}")

            results.append({
                "player": player_name,
                "profile_id": profile_id,
                "games_count": len(games),
                "filepath": filepath
            })
        else:
            print(f"  ❌ No English games found")

        # Rate limiting between players
        time.sleep(1)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_games = 0
    for r in results:
        total_games += r["games_count"]
        print(f"{r['player']}: {r['games_count']} games")
        print(f"  Profile ID: {r['profile_id']}")
        print(f"  File: {r['filepath']}")

    print("=" * 60)
    print(f"Total English games scraped: {total_games}")

    # Create combined file
    if results:
        all_games = []
        for r in results:
            filepath = r['filepath']
            with open(filepath, 'r') as f:
                games = json.load(f)
                all_games.extend(games)

        combined_file = os.path.join(OUTPUT_DIR, "english_pro_games.json")
        with open(combined_file, 'w') as f:
            json.dump(all_games, f, indent=2)

        print(f"\nCombined file saved to: {combined_file}")
        print(f"Total games in combined file: {len(all_games)}")


if __name__ == "__main__":
    main()
