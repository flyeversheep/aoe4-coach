# Build Order API Documentation

## Overview

The AoE4 Coach now supports fetching detailed build order data from AoE4 World, including:
- Complete build order timeline
- Age up timings
- Resource gathering statistics
- Unit/building production with timestamps
- Technology upgrades

## API Endpoint

### Get Game Build Order

```
GET /api/game/{profile_id}/{game_id}?sig={signature}
```

**Parameters:**
- `profile_id` (required): Player's AoE4 World profile ID or Steam ID
- `game_id` (required): Game ID from AoE4 World
- `sig` (optional): Signature for accessing private/protected games

**Example Request:**
```bash
curl "http://localhost:8000/api/game/17689761/182257348?sig=8eba51c210b3028503102d874738eed0fe9493c1"
```

**Response Structure:**
```json
{
  "success": true,
  "game": {
    "game_id": 182257348,
    "map": "Carmel",
    "duration": 1694,
    "duration_formatted": "28:14",
    "win_reason": "Surrender"
  },
  "player": {
    "name": "flyeversheep",
    "civilization": "english",
    "result": "loss",
    "apm": 171,
    "final_score": {
      "total": 2221,
      "military": 122,
      "economy": 884,
      "technology": 735,
      "society": 480
    },
    "resources_gathered": {
      "food": 16935,
      "gold": 6710,
      "stone": 0,
      "wood": 9520,
      "total": 33165
    },
    "resources_spent": {
      "food": 14375,
      "gold": 5650,
      "stone": 0,
      "wood": 9000,
      "total": 29025
    }
  },
  "opponent": {
    "name": "SecretBeef",
    "civilization": "abbasid_dynasty"
  },
  "timings": {
    "feudal_age": {
      "seconds": 322,
      "formatted": "5:22"
    },
    "castle_age": {
      "seconds": 1055,
      "formatted": "17:35"
    },
    "imperial_age": {
      "seconds": null,
      "formatted": null
    }
  },
  "build_order": [
    {
      "id": "11141780",
      "icon": "icons/races/common/units/scout",
      "pbgid": 166412,
      "type": "Unit",
      "finished": [0],
      "constructed": [],
      "destroyed": [557]
    },
    {
      "id": "11119068",
      "icon": "icons/races/common/units/villager",
      "pbgid": 166425,
      "type": "Unit",
      "finished": [0, 22, 42, 62, ...],
      "constructed": [],
      "destroyed": [1500, 1501, ...]
    },
    ...
  ],
  "raw_data": { ... }
}
```

## Build Order Item Types

Each build order item contains:
- `id`: Unique identifier
- `icon`: Icon path for the unit/building/upgrade
- `pbgid`: Game data ID
- `type`: One of: "Unit", "Building", "Age", "Upgrade", "Animal"
- `finished`: Array of timestamps (in seconds) when units/buildings were finished
- `constructed`: Array of timestamps when buildings started construction
- `destroyed`: Array of timestamps when units/buildings were destroyed

## Python Client Usage

```python
from aoe4world_client import AoE4WorldClient

async with AoE4WorldClient() as client:
    # Fetch game summary
    summary = await client.get_game_summary(
        profile_id="17689761",
        game_id="182257348",
        sig="8eba51c210b3028503102d874738eed0fe9493c1"
    )

    # Parse summary
    game_summary = client.parse_game_summary(summary, profile_id="17689761")

    print(f"Player: {game_summary.player_name}")
    print(f"Civilization: {game_summary.player_civ}")
    print(f"Feudal Age: {game_summary.feudal_age_time}s")
    print(f"Build Order Items: {len(game_summary.build_order)}")
```

## Getting the Signature

The signature (`sig`) parameter can be found in the AoE4 World game URL:
```
https://aoe4world.com/players/{profile_id}/games/{game_id}?sig={signature}
```

For public games of players with public match history, the signature may not be required.

## Testing

Run the test script to verify the integration:

```bash
cd backend
python3 test_build_order.py
```

## Use Cases

1. **Build Order Analysis**: Analyze player build orders to identify inefficiencies
2. **Timing Benchmarks**: Compare age up timings with optimal benchmarks
3. **Coaching**: Provide specific feedback on build order execution
4. **Build Order Replays**: Create visual representations of build orders
5. **Meta Analysis**: Track popular build orders and strategies

## Rate Limiting

Be mindful of AoE4 World's rate limits when making requests. Implement appropriate caching and throttling in production applications.
