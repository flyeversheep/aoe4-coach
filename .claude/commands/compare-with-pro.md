# Compare With Pro

Compare a player's game against a professional/high-rated player's game with the same civilization and strategy, identifying pattern differences and generating improvement suggestions.

## Inputs

- **Game URL**: $ARGUMENTS
  - AoE4 World game URL for the player's game (required)
  - Optional flag `--pro <name>`: specific pro to compare against (e.g., `--pro 燕子宇`, `--pro loueMT`)

## Available Pro Reference Data

Pre-scraped games with sigs from players with public match history:

| Player | Profile ID | Rating | Civs | English Games |
|--------|-----------|--------|------|---------------|
| EL.loueMT | 8354416 | 2366 | Ayyubids, Rus | 1 |
| 燕子宇 | 11018483 | 2242 | Chinese, English | 18 |

**Reference file:** `reference_data/english_pro_games.json`

```bash
# View available pro games
cat reference_data/english_pro_games.json | python3 -m json.tool | head -50
```

## Helper Script

`scripts/fetch_game_data.py` handles all data fetching:

```bash
# Compare both players' build orders from YOUR game (includes opponent data)
python3 scripts/fetch_game_data.py --url "<your_game_url>" --compare

# Fetch a pro's game summary
python3 scripts/fetch_game_data.py --url "<pro_game_url_with_sig>" --json
```

## Steps

### 0. Confirm Game URL (REQUIRED)

**If user provided complete game URL (with sig)**: Use it directly.

**If user only provided profile URL or no URL**:
1. Query latest game: `curl "https://aoe4world.com/api/v0/players/{id}/games?limit=1"`
2. Try to fetch sig from games page
3. **If sig cannot be fetched → STOP and ask user**:
   > "I found your latest game (Game {id}), but I need the complete URL with sig to fetch detailed data. Please open this game on aoe4world and send me the full URL (including ?sig=xxx)."

**❌ FORBIDDEN ACTIONS**:
- NEVER assume user's match history is private
- NEVER skip to older games
- NEVER proceed with analysis without sig

### 1. Parse Player's Game

Extract profile_id, game_id, sig from the URL. Fetch the player's game data:

```bash
python3 scripts/fetch_game_data.py --url "<player_game_url>" --compare --json > /tmp/player_game.json
```

Identify:
- **Civilization** played
- **Rating** at time of game
- **Result** (win/loss)
- **Map**
- **Duration**

### 2. Find Reference Games (Multiple)

**Fetch multiple Pro games for statistical comparison:**

1. Load `reference_data/english_pro_games.json`
2. Filter by:
   - Same civilization
   - Preferably **wins** (shows good execution)
   - **Top 3-5 games** by rating or most recent

**If `--pro` specified:**
Use that player's games only.

**If no pro specified (auto-select):**
Use all available games from the reference file.

```bash
# Load and get top pro games
python3 -c "
import json
player_civ = 'english'  # from step 1

with open('reference_data/english_pro_games.json') as f:
    games = json.load(f)

# Filter: wins only, sort by rating (highest first)
wins = [g for g in games if g.get('result') == 'win']
wins.sort(key=lambda x: x.get('rating', 0), reverse=True)

# Get top 3-5 games for comparison
top_games = wins[:5]
for i, g in enumerate(top_games, 1):
    print(f'{i}. Rating: {g.get(\"rating\")}, Map: {g.get(\"map\")}, URL: {g.get(\"url\")}')
"
```

**Goal:** Compare player against **3-5 Pro games** and show:
- Average values (e.g., average feudal time)
- Best/Worst case ranges
- Consistent patterns across Pro games

### 3. Fetch Multiple Pro Games' Build Orders

```bash
# Player's game (already fetched in step 1)
python3 scripts/fetch_game_data.py --url "<player_url>" --compare --json > /tmp/player_game.json

# Pro's games (fetch 3-5 for statistical comparison)
for game_url in "<pro_game1_url>" "<pro_game2_url>" "<pro_game3_url>"; do
    python3 scripts/fetch_game_data.py --url "$game_url" --compare --json > /tmp/pro_game_$(date +%s).json
done
```

Each `--compare` output includes both players' build orders.

### 4. Compare & Analyze (Across Multiple Pro Games)

**Extract key metrics and calculate statistics:**

| Metric | You | Pro Avg | Pro Best | Pro Range | Delta | Status |
|--------|-----|---------|----------|-----------|-------|--------|
| Feudal Age | X:XX | Y:YY | Best:Y:YY | Y:YY-Y:YY | +Zs | 🔴/🟡/🟢 |
| Castle Age | X:XX | Y:YY | Best:Y:YY | Y:YY-Y:YY | +Zs | 🔴/🟡/🟢 |
| Villagers @10min | N | M | Best:M | M-M | -P | 🔴/🟡/🟢 |
| TC idle time | Xs | Ys | Best:Ys | Ys-Ys | +Zs | 🔴/🟡/🟢 |
| Total Villagers | N | M | Best:M | M-M | -P | 🔴/🟡/🟢 |

**Status indicators:**
- 🔴 Significant issue (delta > 60s or >20%)
- 🟡 Minor issue (delta 30-60s)
- 🟢 Good (delta < 30s)

**Key Analysis Points:**

1. **TC Idle Time** — Most important for Gold/Plat players
   - Extract villager `finished` timestamps
   - Find gaps > 25s between consecutive villagers
   - Calculate: Total idle time, Number of incidents, Longest gap

2. **Age-up Timing**
   - Extract age upgrade times from build order
   - Compare to benchmarks: Feudal 4:30-5:00, Castle 12:00-14:00

3. **Villager Production**
   - Total villager count
   - Villagers at key timestamps (10min, 15min, 20min)

4. **Military Production**
   - First military unit timing
   - Total unit count
   - Unit composition

### 5. Generate Report

Write to `analysis/compare_vs_pros_{date}.md` with Chinese coaching content.

### 6. Output Summary

Print to console with key findings and actionable suggestions.

## Notes

- Use Chinese for the coaching report (user-facing)
- Be specific with numbers and comparisons
- Focus on learnable patterns, not mechanical speed
- Include actionable practice suggestions
- Reference game URLs for user review
