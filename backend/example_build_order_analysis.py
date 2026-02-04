#!/usr/bin/env python3
"""
Example: Build Order Analysis
Analyzes a player's build order and provides timing benchmarks
"""
import asyncio
from aoe4world_client import AoE4WorldClient
from typing import Dict, List

# Benchmark timings (in seconds) for different civilizations
BENCHMARKS = {
    "english": {
        "feudal_age": {
            "optimal": 300,  # 5:00
            "good": 330,     # 5:30
            "average": 360   # 6:00
        },
        "castle_age": {
            "optimal": 780,  # 13:00
            "good": 840,     # 14:00
            "average": 900   # 15:00
        }
    },
    "default": {
        "feudal_age": {
            "optimal": 300,
            "good": 330,
            "average": 360
        },
        "castle_age": {
            "optimal": 900,
            "good": 960,
            "average": 1020
        }
    }
}

def format_time(seconds: int) -> str:
    """Format seconds as MM:SS"""
    if seconds is None:
        return "N/A"
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"

def analyze_age_timing(actual: int, civ: str, age: str) -> Dict:
    """Analyze age up timing vs benchmarks"""
    civ_benchmarks = BENCHMARKS.get(civ, BENCHMARKS["default"])
    benchmarks = civ_benchmarks.get(age, {})

    if not benchmarks:
        return {"rating": "N/A", "feedback": "No benchmarks available"}

    diff = actual - benchmarks["optimal"]

    if actual <= benchmarks["optimal"]:
        rating = "Excellent"
        emoji = "🌟"
        feedback = f"Outstanding timing! {abs(diff)}s ahead of optimal."
    elif actual <= benchmarks["good"]:
        rating = "Good"
        emoji = "✅"
        diff_from_optimal = actual - benchmarks["optimal"]
        feedback = f"Solid timing. {diff_from_optimal}s slower than optimal."
    elif actual <= benchmarks["average"]:
        rating = "Average"
        emoji = "⚠️"
        diff_from_optimal = actual - benchmarks["optimal"]
        feedback = f"Room for improvement. {diff_from_optimal}s slower than optimal."
    else:
        rating = "Slow"
        emoji = "❌"
        diff_from_optimal = actual - benchmarks["optimal"]
        feedback = f"Significantly delayed. {diff_from_optimal}s slower than optimal."

    return {
        "rating": rating,
        "emoji": emoji,
        "feedback": feedback,
        "benchmarks": benchmarks
    }

def analyze_build_order(game_summary) -> Dict:
    """Analyze build order and provide insights"""
    print("\n" + "="*70)
    print("BUILD ORDER ANALYSIS")
    print("="*70)

    # Basic info
    print(f"\nGame: {game_summary.map_name}")
    print(f"Player: {game_summary.player_name} ({game_summary.player_civ})")
    print(f"Result: {game_summary.player_result.upper()}")
    print(f"APM: {game_summary.player_apm}")
    print(f"Duration: {format_time(game_summary.duration)}")

    # Age up analysis
    print("\n" + "-"*70)
    print("AGE UP TIMINGS")
    print("-"*70)

    if game_summary.feudal_age_time:
        analysis = analyze_age_timing(
            game_summary.feudal_age_time,
            game_summary.player_civ,
            "feudal_age"
        )
        print(f"\n{analysis['emoji']} Feudal Age: {format_time(game_summary.feudal_age_time)}")
        print(f"   Rating: {analysis['rating']}")
        print(f"   {analysis['feedback']}")
        if 'benchmarks' in analysis:
            print(f"   Optimal: {format_time(analysis['benchmarks']['optimal'])}")

    if game_summary.castle_age_time:
        analysis = analyze_age_timing(
            game_summary.castle_age_time,
            game_summary.player_civ,
            "castle_age"
        )
        print(f"\n{analysis['emoji']} Castle Age: {format_time(game_summary.castle_age_time)}")
        print(f"   Rating: {analysis['rating']}")
        print(f"   {analysis['feedback']}")
        if 'benchmarks' in analysis:
            print(f"   Optimal: {format_time(analysis['benchmarks']['optimal'])}")

    # Economy analysis
    print("\n" + "-"*70)
    print("ECONOMY")
    print("-"*70)

    resources = game_summary.total_resources_gathered
    print(f"\nResources Gathered:")
    print(f"   Food:  {resources.get('food', 0):,}")
    print(f"   Wood:  {resources.get('wood', 0):,}")
    print(f"   Gold:  {resources.get('gold', 0):,}")
    print(f"   Stone: {resources.get('stone', 0):,}")
    print(f"   TOTAL: {resources.get('total', 0):,}")

    # Calculate gather rate
    if game_summary.duration > 0:
        gather_rate_per_min = (resources.get('total', 0) / game_summary.duration) * 60
        print(f"\nGather Rate: {gather_rate_per_min:.0f} resources/min")

    # Build order breakdown
    print("\n" + "-"*70)
    print("BUILD ORDER BREAKDOWN")
    print("-"*70)

    # Count units/buildings by type
    type_counts = {}
    for item in game_summary.build_order:
        item_type = item.get('type', 'Unknown')
        type_counts[item_type] = type_counts.get(item_type, 0) + 1

    print("\nItems by Type:")
    for item_type, count in sorted(type_counts.items()):
        print(f"   {item_type}: {count}")

    # Key buildings timeline
    print("\n" + "-"*70)
    print("KEY BUILDINGS TIMELINE")
    print("-"*70)

    key_buildings = ["barracks", "archery_range", "stable", "blacksmith", "market"]

    for item in game_summary.build_order:
        if item.get('type') == 'Building':
            icon = item.get('icon', '').lower()
            if any(building in icon for building in key_buildings):
                constructed_times = item.get('constructed', [])
                if constructed_times:
                    building_name = icon.split('/')[-1].replace('_', ' ').title()
                    print(f"   {format_time(constructed_times[0])}: {building_name}")

    # Combat score
    print("\n" + "-"*70)
    print("COMBAT PERFORMANCE")
    print("-"*70)

    scores = game_summary.final_score
    print(f"\nFinal Scores:")
    print(f"   Military:   {scores.get('military', 0):,}")
    print(f"   Economy:    {scores.get('economy', 0):,}")
    print(f"   Technology: {scores.get('technology', 0):,}")
    print(f"   Society:    {scores.get('society', 0):,}")
    print(f"   TOTAL:      {scores.get('total', 0):,}")

    print("\n" + "="*70)

async def main():
    """Main function"""
    # Example game data (replace with actual values)
    profile_id = "17689761"
    game_id = "182257348"
    sig = "8eba51c210b3028503102d874738eed0fe9493c1"

    print("Fetching game data from AoE4 World...")

    async with AoE4WorldClient() as client:
        # Fetch game summary
        summary = await client.get_game_summary(profile_id, game_id, sig)

        if not summary:
            print("❌ Failed to fetch game data")
            return

        # Parse summary
        game_summary = client.parse_game_summary(summary, profile_id)

        if not game_summary:
            print("❌ Failed to parse game data")
            return

        # Analyze build order
        analyze_build_order(game_summary)

if __name__ == "__main__":
    asyncio.run(main())
