# Analyze Build Order

Compare a player's actual game execution against a professional build order rubric and generate coaching feedback.

## Inputs

- **Game URL or IDs**: $ARGUMENTS (AoE4 World game URL, or "profile_id game_id")
- If no rubric specified, auto-select the best matching rubric from `rubric_library/` based on the player's civilization and detected strategy.

## Steps

### 1. Fetch Game Data

Use the backend client to fetch game data:

```bash
cd backend
python3 -c "
import asyncio
from aoe4world_client import AoE4WorldClient

async def fetch():
    async with AoE4WorldClient() as client:
        # Parse the game URL or IDs from arguments
        summary = await client.get_game_summary(profile_id='PROFILE_ID', game_id='GAME_ID', sig='SIG')
        game = client.parse_game_summary(summary, profile_id='PROFILE_ID')
        # Print key data
        import json
        print(json.dumps({
            'player': game.player_name,
            'civ': game.player_civ,
            'result': game.result,
            'apm': game.apm,
            'duration': game.duration,
            'feudal': game.feudal_age_time,
            'castle': game.castle_age_time,
            'imperial': game.imperial_age_time,
            'build_order': [{'icon': b.icon, 'type': b.type, 'finished': b.finished} for b in game.build_order],
            'resources_gathered': game.resources_gathered,
            'resources_spent': game.resources_spent,
            'scores': game.final_scores,
        }, indent=2, default=str))

asyncio.run(fetch())
"
```

Parse the URL from $ARGUMENTS to extract profile_id, game_id, and sig. AoE4 World URL format:
`https://aoe4world.com/players/{profile_id}/games/{game_id}?sig={sig}`

### 2. Load Matching Rubric

Read the appropriate rubric JSON from `rubric_library/`. Match based on:
1. Player's civilization
2. Detected strategy (look at age-up timings and early build order to infer)

If unclear, list available rubrics and pick the closest match.

### 3. Analyze & Compare

For each phase in the rubric, compare:

**Timing Analysis:**
- Age-up timings vs rubric benchmarks
- Key building placement timings
- Military production start time

**Execution Analysis:**
- Did the player follow the rubric's key_actions in order?
- Were critical actions done on time?
- Which actions were missed or delayed?

**Economy Analysis:**
- Resource gathering balance (food/wood/gold/stone)
- Total resources gathered vs game duration (gather rate)
- Resource floating (gathered - spent)

**Pattern Detection:**
- Identify recurring issues across the build order
- Look for TC idle time (gaps in villager production timestamps)
- Look for population blocks (gaps in all production)
- Detect strategic pivots (where player deviated from rubric)

### 4. Generate Coaching Report

Write the report to `analysis/` directory. Format:

```markdown
# 🏰 Build Order Coaching Report

## Game Summary
- Player: {name} ({civ}) vs {opponent} ({opp_civ})
- Map: {map} | Duration: {duration} | Result: {result}
- APM: {apm}

## Rubric: {rubric_title}

## ⏱️ Timing Comparison
| Milestone | Your Time | Rubric Target | Diff | Rating |
|-----------|-----------|---------------|------|--------|
| Feudal Age | X:XX | X:XX | +/-Xs | ✅/⚠️/❌ |
| Castle Age | X:XX | X:XX | +/-Xs | ✅/⚠️/❌ |

## 📋 Phase-by-Phase Analysis

### Dark Age
- What you did well: ...
- What to improve: ...
- Specific actions missed: ...

### Feudal Age
...

## 🔍 Pattern Analysis
- **Biggest issue:** ...
- **Second issue:** ...
- **Hidden strength:** ...

## 🎯 Top 3 Actionable Tips
1. ...
2. ...
3. ...

## 📊 Economy Breakdown
- Gather rate: X resources/min
- Resource floating: X (food/wood/gold)
- Efficiency: X%
```

### 5. Summary

Print a brief summary to the console highlighting the top 3 things to improve.

## Notes

- Be specific and actionable. Not "improve your economy" but "you had 3 gaps in villager production between 4:00-6:00, costing you ~6 villagers"
- Compare against the rubric, not abstract ideals
- Acknowledge what the player did well
- Consider the player's ELO context — don't expect pro-level execution from a Gold player
- If the game was a win, still find improvement areas
- Use Chinese (中文) for the coaching report since the primary user is Chinese-speaking
