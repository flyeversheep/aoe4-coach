#!/usr/bin/env python3
"""
Test script for build order fetching
"""
import asyncio
from aoe4world_client import AoE4WorldClient

async def test_build_order():
    """Test fetching build order data"""
    print("Testing AoE4 World Build Order Integration...")
    print("-" * 50)

    # Test with the game from the user
    profile_id = "17689761"
    game_id = "182257348"
    sig = "8eba51c210b3028503102d874738eed0fe9493c1"

    async with AoE4WorldClient() as client:
        print(f"Fetching game {game_id} for profile {profile_id}...")

        summary = await client.get_game_summary(profile_id, game_id, sig)

        if not summary:
            print("❌ Failed to fetch game summary")
            return False

        print("✅ Successfully fetched game summary")
        print(f"   Game ID: {summary.get('gameId')}")
        print(f"   Map: {summary.get('mapName')}")
        print(f"   Duration: {summary.get('duration')} seconds")

        # Parse the summary
        game_summary = client.parse_game_summary(summary, profile_id)

        if not game_summary:
            print("❌ Failed to parse game summary")
            return False

        print("\n✅ Successfully parsed game summary")
        print("\nPlayer Information:")
        print(f"   Name: {game_summary.player_name}")
        print(f"   Civilization: {game_summary.player_civ}")
        print(f"   Result: {game_summary.player_result}")
        print(f"   APM: {game_summary.player_apm}")

        print("\nAge Up Timings:")
        if game_summary.feudal_age_time:
            mins = game_summary.feudal_age_time // 60
            secs = game_summary.feudal_age_time % 60
            print(f"   Feudal Age: {mins}:{secs:02d} ({game_summary.feudal_age_time}s)")
        if game_summary.castle_age_time:
            mins = game_summary.castle_age_time // 60
            secs = game_summary.castle_age_time % 60
            print(f"   Castle Age: {mins}:{secs:02d} ({game_summary.castle_age_time}s)")
        if game_summary.imperial_age_time:
            mins = game_summary.imperial_age_time // 60
            secs = game_summary.imperial_age_time % 60
            print(f"   Imperial Age: {mins}:{secs:02d} ({game_summary.imperial_age_time}s)")

        print("\nResources Gathered:")
        for resource, amount in game_summary.total_resources_gathered.items():
            print(f"   {resource.capitalize()}: {amount}")

        print(f"\nBuild Order Items: {len(game_summary.build_order)}")

        # Show first few build order items
        print("\nFirst 10 Build Order Items:")
        for i, item in enumerate(game_summary.build_order[:10]):
            item_type = item.get('type', 'Unknown')
            icon = item.get('icon', '').split('/')[-1]
            finished_times = item.get('finished', [])
            constructed_times = item.get('constructed', [])

            if finished_times:
                time_str = f"finished at {finished_times[0]}s"
            elif constructed_times:
                time_str = f"constructed at {constructed_times[0]}s"
            else:
                time_str = "no timing data"

            print(f"   {i+1}. {item_type}: {icon} ({time_str})")

        print("\n✅ Build order integration test successful!")
        return True

if __name__ == "__main__":
    success = asyncio.run(test_build_order())
    exit(0 if success else 1)
