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
