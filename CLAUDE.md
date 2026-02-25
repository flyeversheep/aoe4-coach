# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AoE4 Coach is an AI-powered post-game analysis tool for Age of Empires IV. It fetches player data from the AoE4 World API, generates AI coaching reports (via OpenAI GPT-4o or z.ai GLM-5), and analyzes build orders against professional rubric templates.

**Tech stack:** Python 3 / FastAPI backend, vanilla JavaScript SPA frontend, aiohttp for async HTTP, Chart.js for visualizations.

---

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app (serves API + frontend on port 8000)
python backend/main.py

# Dev mode with auto-reload
cd backend && uvicorn main:app --reload

# Run build order integration test
python backend/test_build_order.py

# Run example analysis script
python backend/example_build_order_analysis.py
```

**No formal test framework** — only manual scripts (`test_build_order.py`, `example_build_order_analysis.py`). There are no pytest/unittest suites.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ZAI_API_KEY` | — | z.ai API key (tried first when `AI_PROVIDER=auto`) |
| `ZAI_BASE_URL` | `https://api.z.ai/api/paas/v4/` | z.ai endpoint |
| `AI_PROVIDER` | `auto` | `auto`, `openai`, or `zai` |
| `AI_MODEL` | — | Override model ID (defaults to `glm-5` for z.ai, `gpt-4o-mini` for OpenAI) |
| `RUBRIC_LIBRARY_PATH` | — | Path to rubric JSON files directory |

**AI provider selection logic (`auto` mode):** Tries z.ai first if `ZAI_API_KEY` is set, then falls back to OpenAI. If no keys are present, returns a template-generated report without AI.

---

## Architecture

**Single-process app:** FastAPI backend serves both REST API and the static frontend (`frontend/index.html`) on port 8000.

```
┌─────────────────────────────────────────────────────────┐
│                  Frontend (index.html)                   │
│         Vanilla JS SPA + Chart.js Visualizations        │
└──────────────────────┬──────────────────────────────────┘
                       │ fetch() calls
                       ▼
┌─────────────────────────────────────────────────────────┐
│               FastAPI Backend (main.py)                  │
│  GET  /api/player/{profile_id}      → player analysis   │
│  GET  /api/game/{pid}/{gid}         → build order data  │
│  POST /api/game/{pid}/{gid}/coaching → rubric coaching  │
│  GET  /api/rubrics                  → list rubrics      │
└────────┬───────────────┬────────────────┬───────────────┘
         │               │                │
   ┌─────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
   │AoE4World   │ │ AI Provider │ │  aoe4_data  │
   │API Client  │ │ OpenAI/z.ai │ │ Entity names│
   └────────────┘ └─────────────┘ └─────────────┘
```

### Directory Structure

```
aoe4-coach/
├── backend/
│   ├── main.py                         # FastAPI app — all endpoints, AI logic
│   ├── aoe4world_client.py             # Async AoE4 World API client + data classes
│   ├── aoe4_data.py                    # Entity name lookup (pbgid → name)
│   ├── test_build_order.py             # Manual integration test
│   └── example_build_order_analysis.py # Analysis example with benchmark output
├── frontend/
│   └── index.html                      # SPA (~1600 lines inline CSS + JS)
├── rubric_library/                     # Symlink to rubric JSON files (external)
├── requirements.txt
├── package.json
├── BUILD_ORDER_API.md                  # Build order API documentation
├── INTEGRATION_SUMMARY.md             # Integration guide
└── CLAUDE.md                          # This file
```

---

## Backend Modules

### `main.py` — FastAPI Core (≈943 lines)

All HTTP endpoints plus AI integration logic. Key areas:

**Startup:**
- Calls `aoe4_data.load()` on startup to populate entity name cache
- Configures CORS (all origins allowed)
- Mounts `/static` → `frontend/` directory

**AI Provider Initialization:**
```python
# Determined at startup from env vars:
# - AI_PROVIDER=auto → try z.ai first, then OpenAI
# - AI_PROVIDER=zai  → z.ai only
# - AI_PROVIDER=openai → OpenAI only
```

**Key Functions:**

| Function | Purpose |
|---|---|
| `generate_coaching_report(player_data, analysis, games)` | Builds prompt, calls AI, cleans/parses JSON, returns coaching dict |
| `generate_template_report(analysis)` | AI-free fallback; computes rating from win rate, identifies best/worst civs |
| `normalize_coaching_report(report)` | Ensures consistent types: strings→arrays, improvements→`{issue, fix}` dicts |
| `clean_json_response(text)` | Strips markdown fences (` ```json ` blocks), fixes trailing commas before `}` or `]` |
| `generate_rubric_coaching(rubric, game_summary, profile_id)` | Compares game vs rubric benchmarks, rates performance, identifies mistakes |
| `calculate_villager_count(build_order, at_time)` | Counts villagers completed by `at_time` seconds |
| `load_rubric(rubric_id)` | Reads rubric JSON from `RUBRIC_LIBRARY_PATH/<rubric_id>.json` |

**AI Prompt Pattern:** The coaching prompt requests a specific JSON schema. The response is run through `clean_json_response()` then `json.loads()`, then `normalize_coaching_report()`. If any step fails, `generate_template_report()` is used.

**z.ai specifics:** Requires `"thinking": "disabled"` parameter in API call (GLM-5 model quirk).

---

### `aoe4world_client.py` — API Client (≈377 lines)

Async HTTP client using `aiohttp` with SSL via `certifi`. Use as an async context manager.

**Base URL:** `https://aoe4world.com/api/v0`

**Data Classes:**

```python
@dataclass
class Player:
    profile_id: int
    name: str
    steam_id: str | None
    country: str | None
    avatar_url: str | None

@dataclass
class Game:
    game_id: str
    started_at: datetime
    duration: int          # seconds
    map: str
    kind: str              # "rm_solo", "rm_team", "qm_1v1", etc.
    player_civ: str
    player_result: str     # "win" or "loss"
    player_rating: int
    player_rating_diff: int
    opponent_name: str
    opponent_civ: str
    opponent_rating: int

@dataclass
class BuildOrderItem:
    id: str
    icon: str              # e.g. "icons/races/common/units/villager"
    pbgid: int             # lookup key for display name
    type: str              # "Unit", "Building", "Age", "Upgrade", "Animal"
    finished: List[int]    # timestamps (seconds) when produced/built
    constructed: List[int] # timestamps when construction started
    destroyed: List[int]   # timestamps when destroyed

@dataclass
class GameSummary:
    game_id: int
    duration: int
    map_name: str
    win_reason: str            # "Surrender", "Elimination", etc.
    player_name: str
    player_civ: str
    player_result: str
    player_apm: int
    build_order: List          # List of BuildOrderItem dicts
    feudal_age_time: int | None   # seconds
    castle_age_time: int | None
    imperial_age_time: int | None
    total_resources_gathered: dict
    total_resources_spent: dict
    final_score: dict          # {total, military, economy, technology, society}
    opponent_name: str
    opponent_civ: str
    opponent_apm: int
    opponent_build_order: List
    # ...opponent age timings
```

**Key Methods:**

| Method | Endpoint | Notes |
|---|---|---|
| `get_player(profile_id)` | `/api/v0/players/{id}` | Returns raw dict or None |
| `get_player_games(profile_id, limit, leaderboard)` | `/api/v0/players/{id}/games` | Returns list of raw game dicts |
| `get_game_summary(profile_id, game_id, sig)` | `aoe4world.com/players/{id}/games/{gid}/summary?camelize=true` | Uses `camelize=true` for camelCase fields |
| `parse_game(game_data, profile_id)` | — | Parses raw game into `Game` dataclass |
| `parse_game_summary(summary_data, profile_id)` | — | Parses raw summary into `GameSummary`, extracts age timings from actions |
| `analyze_performance(games)` | — | Returns dict with win_rate, civ_stats, map_stats, avg_rating_change |

**SSL pattern:**
```python
ssl_context = ssl.create_default_context(cafile=certifi.where())
connector = aiohttp.TCPConnector(ssl=ssl_context)
```

---

### `aoe4_data.py` — Entity Lookup (≈160 lines)

Loads unit/building/technology display names from `data.aoe4world.com` on app startup.

**Global singleton:** `aoe4_data = AoE4DataLookup()` — imported and used in `main.py`.

**Data sources (fetched in parallel):**
- `https://data.aoe4world.com/units/all.json`
- `https://data.aoe4world.com/buildings/all.json`
- `https://data.aoe4world.com/technologies/all.json`

**Key methods:**

| Method | Purpose |
|---|---|
| `load()` | Async; fetches and caches all entity data |
| `get_name(pbgid, fallback)` | Returns display name for a pbgid, or fallback |
| `get_entity(pbgid)` | Returns full `EntityData` object |
| `enrich_build_order(build_order)` | Adds `"name"` field to each build order item |

**Name fallback chain:** pbgid lookup → extract from icon path (replace `_` with spaces) → `"Unknown ({pbgid})"`.

---

## API Endpoints

### `GET /api/player/{profile_id}`

Fetches player profile + recent games + AI coaching.

**Query params:**
- `limit` (int 1–50, default 10): number of games to analyze
- `leaderboard` (str, default `rm_solo`): `rm_solo`, `rm_team`, `qm_1v1`, `qm_2v2`, `qm_3v3`, `qm_4v4`

**Response:**
```json
{
  "success": true,
  "player": { "profile_id": "...", "name": "...", "steam_id": "...", "country": "...", "avatar_url": "..." },
  "analysis": {
    "total_games": 10, "wins": 6, "losses": 4, "win_rate": 60.0,
    "civilization_stats": { "english": { "games": 4, "wins": 3, "win_rate": 75.0 } },
    "map_stats": { "arabia": { "games": 5, "wins": 4, "win_rate": 80.0 } },
    "avg_rating_change": 18.5, "current_rating": 1520
  },
  "recent_games": [ { "game_id": "...", "map": "...", "civilization": "...", "result": "...", "rating": 1520, "rating_diff": 25, "opponent": { ... }, "duration": 1694 } ],
  "coaching_report": {
    "rating": "A",
    "strengths": ["..."],
    "improvements": [{ "issue": "...", "fix": "..." }],
    "civ_recommendations": ["..."],
    "map_advice": ["..."],
    "training_plan": ["..."],
    "ai_generated": true,
    "ai_provider": "openai",
    "disclaimer": "🤖 AI-Generated Coaching Advice (openai)"
  }
}
```

---

### `GET /api/game/{profile_id}/{game_id}`

Fetches detailed build order for a specific game.

**Query params:**
- `sig` (optional): signature for private games (from AoE4 World URL)

**Response:**
```json
{
  "success": true,
  "game": { "game_id": "...", "map": "...", "duration": 1694, "duration_formatted": "28:14", "win_reason": "Surrender" },
  "player": { "name": "...", "civilization": "...", "result": "...", "apm": 171, "final_score": { "total": 2221, "military": 122, "economy": 884, "technology": 735, "society": 480 }, "resources_gathered": { "food": 16935, "wood": 9520, "gold": 6710, "stone": 0, "total": 33165 }, "resources_spent": { ... } },
  "opponent": { "name": "...", "civilization": "..." },
  "timings": {
    "player": { "feudal_age": { "seconds": 322, "formatted": "5:22" }, "castle_age": { "seconds": 1055, "formatted": "17:35" }, "imperial_age": { "seconds": null, "formatted": null } },
    "opponent": { ... }
  },
  "build_order": [
    { "id": "...", "icon": "icons/races/common/units/villager", "pbgid": 166425, "type": "Unit", "finished": [0, 22, 42], "constructed": [], "destroyed": [1500], "name": "Villager" }
  ],
  "opponent_build_order": [ ... ]
}
```

---

### `POST /api/game/{profile_id}/{game_id}/coaching`

Generates AI coaching comparing game execution to a rubric.

**Query params:**
- `rubric_id` (required): rubric file ID (without `.json` extension)
- `sig` (optional): game signature

**Response:** Rubric coaching analysis with benchmark comparisons, execution mistakes, success criteria evaluation, and strategic advice.

---

### `GET /api/rubrics`

Lists all available rubrics from `RUBRIC_LIBRARY_PATH`.

**Response:**
```json
{
  "success": true,
  "rubrics": [
    { "id": "...", "title": "...", "difficulty": "...", "civilizations": ["eng"], "archetype": "...", "overview": "..." }
  ]
}
```

---

### `GET /api/sample-report`

Returns a hardcoded sample coaching report for demo purposes.

---

## Rubric System

Rubrics are JSON files stored in `RUBRIC_LIBRARY_PATH/` (configured via env var). Each rubric defines a professional build order with benchmarks.

**Rubric JSON structure:**
```json
{
  "id": "rubric_id",
  "title": "Build Order Name",
  "difficulty": "intermediate",
  "civilizations": ["english"],
  "archetype": "feudal_aggression",
  "overview": "Brief description",
  "phases": [
    {
      "name": "Dark Age",
      "benchmarks": {
        "feudal_age_seconds": 390,
        "villager_count_at_feudal": 22
      },
      "success_criteria": ["22 villagers at feudal age up"],
      "common_mistakes": ["Idling villagers before 1:00"]
    }
  ]
}
```

**Coaching generation (`generate_rubric_coaching`):**
1. Compares actual vs expected timings, computes deltas
2. Rates each benchmark: `excellent` / `good` / `average` / `poor` / `very_poor`
3. Identifies execution mistakes using build order evidence
4. Evaluates success criteria
5. Calls AI for 2–3 paragraph strategic advice

---

## Frontend (`frontend/index.html`)

Single file, ~1600 lines of inline CSS + JS. No build step, no framework.

**Libraries:** Chart.js (CDN), no other dependencies.

**URL parsing — `parseAoE4WorldUrl(input)`:**
Accepts multiple input formats:
- AoE4 World game URL with signature: `aoe4world.com/players/{id}/games/{gid}?sig={sig}`
- AoE4 World game URL without signature
- AoE4 World profile URL
- Plain numeric profile ID

Returns: `{ type: "player"|"game", profileId, gameId?, signature? }`

**Main flow functions:**

| Function | Trigger | API Call |
|---|---|---|
| `analyzePlayer()` | Analyze button (player URL) | `GET /api/player/{id}` |
| `analyzeGame(pid, gid, sig)` | Analyze button (game URL) or game click | `GET /api/game/{pid}/{gid}` |
| `analyzeWithRubric()` | Rubric selector change | `POST /api/game/{pid}/{gid}/coaching` |
| `loadDemo()` | Demo button | `GET /api/sample-report` |

**Rendering functions:**

| Function | Purpose |
|---|---|
| `renderBuildOrderTimeline(elementId, buildOrder)` | Renders item list with icons and timestamps |
| `updateTimingComparison(timings)` | Shows player vs opponent age timings with color-coded deltas |
| `displayRubricCoaching(coaching)` | Renders benchmark ratings, mistakes, success criteria |
| `formatTime(seconds)` | Converts seconds → `MM:SS` string |

**API base URL detection:**
```javascript
const API_BASE = window.location.port === '8000'
  ? ''          // integrated mode (same origin)
  : 'http://localhost:8000';  // separate frontend server
```

**Civilization mismatch warning:** Frontend warns when selected rubric civilizations don't match the game's player civilization.

---

## Key Conventions

### Data Types to Watch

- **Profile IDs** can be numeric strings or Steam IDs — treat as strings throughout
- **Game IDs** are numeric strings — the API accepts both string and int
- **`pbgid`** is the AoE4 game's internal entity ID, used as a lookup key in `aoe4_data`
- **Timestamps** are in seconds (int); use `formatTime(seconds)` for display
- **`timings` response format changed** between the build order API (flat `{feudal_age, castle_age, imperial_age}`) and the older coaching format (nested `{player: {...}, opponent: {...}}`) — check which format you're reading

### AI Response Handling

The AI is asked to return JSON but often returns markdown-wrapped JSON or has trailing commas. Always pipe through:
1. `clean_json_response(text)` — removes fences, fixes trailing commas
2. `json.loads()` with try/except
3. `normalize_coaching_report(report)` — enforces expected types

### Async Patterns

All external API calls are async. When adding new endpoints, use `async def` and `await` with the `AoE4WorldClient` context manager:
```python
async with AoE4WorldClient() as client:
    data = await client.get_player(profile_id)
```

### Error Handling

Endpoints return `{"success": false, "error": "message"}` on failure. The frontend checks `data.success` before rendering.

### Adding a New Endpoint

1. Add the route in `main.py` with `@app.get(...)` or `@app.post(...)`
2. Use `AoE4WorldClient` for external data
3. Use `aoe4_data.enrich_build_order()` if returning build order items
4. Return `{"success": true, ...}` or `{"success": false, "error": "..."}`
5. Add frontend handling in `index.html` if needed

---

## Data Flow Summaries

### Player Analysis Flow

```
User input → parseAoE4WorldUrl() → GET /api/player/{id}
  → AoE4WorldClient.get_player()           (profile data)
  → AoE4WorldClient.get_player_games()     (recent games)
  → AoE4WorldClient.parse_game() × N       (Game dataclass)
  → analyze_performance(games)             (win rates, civ stats)
  → generate_coaching_report()             (AI or template)
  → JSON response → Frontend renders
```

### Build Order Flow

```
User clicks game → GET /api/game/{pid}/{gid}
  → AoE4WorldClient.get_game_summary()     (raw summary)
  → AoE4WorldClient.parse_game_summary()   (GameSummary dataclass)
  → aoe4_data.enrich_build_order()         (add "name" fields)
  → JSON response → Frontend renderBuildOrderTimeline()
  → User selects rubric → POST /api/game/{pid}/{gid}/coaching
  → load_rubric() + generate_rubric_coaching()
  → AI analysis → Frontend displayRubricCoaching()
```

---

## Known Limitations

- No formal test framework — only manual scripts with hardcoded game IDs
- `rubric_library/` is a symlink to an external directory; may not exist in fresh clones
- SSL uses `certifi` bundle — may need updates if AoE4 World changes certificates
- Single-process (no clustering/workers); not production-hardened
- CORS allows all origins — suitable for local/demo use only
- `example_build_order_analysis.py` uses hardcoded English civilization benchmarks
