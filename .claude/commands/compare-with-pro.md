# Compare With Pro

Compare a player's game against a higher-ranked player's game with the same civilization, identifying pattern differences and generating improvement suggestions.

## Inputs

- **Game URL**: $ARGUMENTS
  - First argument: AoE4 World game URL for the player's game (required)
  - Optional flag `--pro <name>`: specific pro player name to compare against (e.g., `--pro Beasty`)
  - If no `--pro` specified, find a player 1-2 rank tiers above the current player who won with the same civ

## AoE4 World API Reference

Base URL: `https://aoe4world.com/api/v0`

```
GET /players/search?query={name}          → Find player by name
GET /players/{id}/games?civilization={civ}&leaderboard=rm_solo&limit=10  → List games filtered by civ
GET /players/{id}/games/{game_id}         → Basic game info (no build order)
GET /players/{id}/games/{game_id}/summary?camelize=true&sig={sig}  → Detailed build order (needs sig)
```

**Important:** The `/summary` endpoint requires a `sig` parameter. For the current player's game, the sig comes from their AoE4 World URL. For pro players' games, you need to obtain the sig by:

1. **Option A (preferred):** Visit the AoE4 World game page in a browser and extract the sig from the URL or page source
2. **Option B:** Check if the game is from a tournament (tournament games often have public summaries)
3. **Option C (fallback):** If no build order is available, compare using basic game stats (duration, result) and known pro build order rubrics from `rubric_library/`

## Rank Tier Reference

```
Bronze    < 600
Silver    600-800
Gold      800-1000
Platinum  1000-1200
Diamond   1200-1400
Conqueror 1  1400-1600
Conqueror 2  1600-1800
Conqueror 3  1800+
```

## Steps

### 1. Fetch Player's Game Data

Parse the AoE4 World URL to get profile_id, game_id, sig.
Fetch the player's game summary (build order, timings, resources).
Identify:
- Civilization played
- Strategy archetype (from build order pattern)
- Current rating/rank tier

### 2. Find Reference Game

**If `--pro` specified:**
```bash
# Search for the pro player
curl "https://aoe4world.com/api/v0/players/search?query={pro_name}"

# Get their recent games with the same civilization, wins only
curl "https://aoe4world.com/api/v0/players/{pro_id}/games?civilization={civ}&leaderboard=rm_solo&limit=20"

# Filter for wins, pick a game with similar duration (±5 min) if possible
```

**If no pro specified (auto-select):**
```python
# Calculate target rating: player_rating + 200 to +400 (1-2 tiers up)
target_min = player_rating + 200
target_max = player_rating + 400

# Strategy: Search for well-known players in that rating range
# Or use the leaderboard API to find players at target rating
# Then find their recent wins with the same civ
```

**Well-known pro players for reference (fallback list):**
| Player | Profile ID | Rating Range | Main Civs |
|--------|-----------|-------------|-----------|
| Beasty | 8139502 | 2200+ | All |
| MarineLorD | 4950751 | 2100+ | French, English |
| Leenock | 6894498 | 2000+ | Mongols, Chinese |
| TheViper | 2917924 | 2000+ | All |
| Hera | 3408911 | 2000+ | All |

### 3. Fetch Reference Game Data

Try to get the build order summary for the reference game.
If sig is unavailable:
- Try accessing the AoE4 World page via browser to get sig
- If that fails, use a rubric from `rubric_library/` as the reference instead
- Clearly state in the report that a rubric was used instead of an actual game

### 4. Compare & Analyze

**Side-by-side comparison:**

| Metric | You | Pro | Delta |
|--------|-----|-----|-------|
| Feudal Age | | | |
| Castle Age | | | |
| Imperial Age | | | |
| APM | | | |
| Total Resources | | | |
| Duration | | | |

**Deep analysis (when build orders available):**

a) **Timing Differences**
- Age-up timing gaps
- First military unit timing
- Key tech upgrade timing
- Second TC timing (if applicable)

b) **Build Order Pattern Differences**
- What units/buildings do they prioritize differently?
- Resource allocation differences (food/wood/gold ratios)
- When does the pro start military production vs you?

c) **Economy Differences**
- Villager production consistency (gaps)
- Resource gathering rate comparison
- Resource floating (unspent resources)

d) **Military Differences**
- Unit composition choices
- Production timing and volume
- Army size at key moments

### 5. Generate Report

Write to `analysis/` directory. Format:

```markdown
# 🏰 Pro Comparison Report

## Match Summary
| | You | {Pro Name} |
|---|---|---|
| Game | {your_game_url} | {pro_game_url} |
| Civ | {civ} | {civ} |
| Rating | {your_rating} | {pro_rating} |
| Result | {your_result} | {pro_result} |
| Map | {map} | {map} |
| Duration | {duration} | {duration} |
| APM | {apm} | {apm} |

## ⏱️ Timing Comparison
...

## 🔍 Key Differences
### 1. [Biggest difference]
**You:** ...
**Pro:** ...
**Why it matters:** ...
**How to fix:** ...

### 2. [Second difference]
...

### 3. [Third difference]
...

## 💡 What You Can Learn
1. ...
2. ...
3. ...

## ✅ What You're Already Doing Well
...
```

### 6. Summary

Print top 3 differences and actionable takeaways to console.

## Notes

- Use Chinese (中文) for the coaching report
- Be specific: "Pro builds 2nd TC at 8:30, you build at 11:00" not "build TC faster"
- Acknowledge rating difference — don't expect identical execution
- Focus on learnable patterns, not mechanical speed
- If comparing against a much higher rated player (>500 rating diff), note which differences are due to mechanics vs strategy
- When build order data is unavailable for the pro, be transparent about it and use rubrics as supplementary reference
- Include the Twitch VOD link if available (some AoE4 World entries include twitch_video_url)
