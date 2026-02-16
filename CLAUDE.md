# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AoE4 Coach is an AI-powered post-game analysis tool for Age of Empires IV. It fetches player data from the AoE4 World API, generates AI coaching reports (via OpenAI GPT-4o or z.ai GLM-5), and analyzes build orders against professional rubric templates.

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

There is no formal test framework (pytest/unittest) — only manual test scripts.

## Environment Variables

- `OPENAI_API_KEY` — OpenAI API key
- `ZAI_API_KEY` — z.ai API key (tried first when `AI_PROVIDER=auto`)
- `ZAI_BASE_URL` — z.ai endpoint (default: `https://api.z.ai/api/paas/v4/`)
- `AI_PROVIDER` — `auto` (default), `openai`, or `zai`
- `AI_MODEL` — override model ID
- `RUBRIC_LIBRARY_PATH` — path to rubric JSON files for build order coaching

## Architecture

**Single-process app:** FastAPI backend serves both the REST API and the static frontend (`frontend/index.html`) on port 8000.

### Backend (`backend/`)

- **`main.py`** — FastAPI app with all API endpoints. Handles AI provider auto-detection (z.ai → OpenAI fallback), prompt construction, JSON response cleaning, and template report generation.
- **`aoe4world_client.py`** — Async HTTP client for the AoE4 World API. Defines data classes (`Player`, `Game`, `BuildOrderItem`, `GameSummary`) and contains `analyze_performance()` for computing win rates, civ stats, rating trends. Uses `certifi` for SSL.
- **`aoe4_data.py`** — Entity lookup service. Loads unit/building/technology names from `data.aoe4world.com` on startup. Singleton `aoe4_data` instance used to enrich build orders by resolving `pbgid` → display name.

### Frontend (`frontend/`)

- **`index.html`** — Single-page app with inline CSS and JS (~1600 lines). Vanilla JavaScript, no framework. Uses Chart.js for visualization. Parses AoE4 World URLs to extract profile/game IDs.

### Key API Endpoints

```
GET  /api/player/{profile_id}                         — Player analysis + AI coaching
GET  /api/game/{profile_id}/{game_id}?sig={signature}  — Game details with build order
POST /api/game/{profile_id}/{game_id}/coaching          — AI rubric-based coaching
GET  /api/rubrics                                       — List available rubrics
```

### Data Flow

1. Frontend sends profile ID or parsed AoE4 World URL to backend
2. Backend fetches data from AoE4 World API (player, games, build orders)
3. `aoe4_data` enriches build order items with human-readable names
4. Backend constructs prompts and calls AI provider for coaching analysis
5. AI returns JSON coaching report; backend cleans/parses it
6. Frontend renders results with charts and build order timelines

## Rubric Library

`rubric_library/` contains professional build order rubrics in JSON format. Each rubric includes:
- `phases[]` — Dark Age, Feudal, Castle, Imperial with key_actions and timings
- `benchmarks` — target timings (feudal_age, castle_age, villager counts)
- `common_mistakes[]` — mistake, consequence, fix
- `success_criteria[]` — what "good" looks like per phase

Available rubrics (English civ):
- `fast_castle_boom_english.json` — Safe economic FC build
- `longbow_rush_standard_english_valdy.json` — Aggressive Feudal longbow
- `longbow_rush_castle_timing_english_valdy_2026.json` — Longbow into Castle
- `2tc_standard_english_valdy.json` — 2 TC Feudal boom
- `2tc_white_tower_english_valdy_2026.json` — White Tower 2 TC variant
- `stable_king_opener_english_valdy.json` — Stable King opener

## Claude Code Coaching Commands

Custom slash commands in `.claude/commands/`:

- `/analyze-build-order` — Compare a player's game against a pro rubric. Fetches game data from AoE4 World API, parses build order, and generates detailed coaching feedback.
- `/compare-with-pro` — Compare a player's game against a higher-ranked player's game with the same civ. Optionally specify a pro with `--pro Beasty`. Auto-finds reference games 1-2 tiers above.

### Player Info

- **Primary player:** flyeversheep (Profile ID: 17689761)
- **AoE4 World profile:** https://aoe4world.com/players/17689761

## AoE4 Domain Knowledge

### Key Metrics for Coaching
- **Age-up timings** — Feudal (optimal ~5:00), Castle (~13:00), Imperial (~25:00)
- **Villager production** — Zero TC idle time is the #1 priority for low-mid ELO
- **APM** — Effective actions matter more than raw APM. Gold/Plat avg 50-100, Diamond+ 150+
- **Resource balance** — Food/Wood/Gold allocation should match strategy
- **Build order adherence** — How closely execution matches the intended strategy

### Common Weakness Patterns
- TC idle time (villager production gaps)
- Late age-ups (resource floating or wrong allocation)
- Population blocked (forgetting houses)
- No scouting (blind to enemy strategy)
- Over-committing to one plan (not adapting)
- Resource floating (>500 unspent resources)
