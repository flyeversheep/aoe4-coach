"""
AoE IV AI Coach - Backend API
Uses AoE4 World API to fetch player data and generate AI coaching reports
"""
import os
import json
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import ssl
import certifi
import httpx
from openai import OpenAI

from aoe4world_client import AoE4WorldClient

# Config - Support multiple AI providers
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")
ZAI_BASE_URL = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4/")  # z.ai API endpoint
AI_PROVIDER = os.getenv("AI_PROVIDER", "auto")  # auto, openai, or zai
AI_MODEL = os.getenv("AI_MODEL", "")  # Optional: override default model
RUBRIC_LIBRARY_PATH = os.getenv("RUBRIC_LIBRARY_PATH", "/Users/feihan/clawd/youtube-rubric-extractor/rubric_library")

# Create SSL context for AoE4 World API (used in aoe4world_client)
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Initialize AI client with default settings (handles SSL automatically)
ai_client = None
active_provider = None

# Try to initialize based on preference
if AI_PROVIDER == "zai" or (AI_PROVIDER == "auto" and ZAI_API_KEY and not OPENAI_API_KEY):
    if ZAI_API_KEY:
        try:
            ai_client = OpenAI(api_key=ZAI_API_KEY, base_url=ZAI_BASE_URL)
            active_provider = "zai"
            print(f"INFO: z.ai client initialized successfully (endpoint: {ZAI_BASE_URL})")
        except Exception as e:
            print(f"ERROR: Failed to init z.ai client: {e}")

if not ai_client and OPENAI_API_KEY:
    try:
        ai_client = OpenAI(api_key=OPENAI_API_KEY)
        active_provider = "openai"
        print("INFO: OpenAI client initialized successfully")
    except Exception as e:
        print(f"ERROR: Failed to init OpenAI client: {e}")

if ai_client:
    print(f"INFO: Using AI provider: {active_provider}")
else:
    print("WARN: No AI provider configured. Set OPENAI_API_KEY or ZAI_API_KEY environment variable.")

app = FastAPI(title="AoE IV AI Coach", version="0.2.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
import os
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def root():
    # Serve index.html if it exists, otherwise return API info
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AoE IV AI Coach API", "version": "0.2.0", "data_source": "AoE4 World", "frontend": "Place frontend/index.html next to backend folder"}

@app.get("/api/player/{profile_id}")
async def get_player_analysis(
    profile_id: str,
    limit: int = Query(10, ge=1, le=50),
    leaderboard: str = Query("rm_solo", regex="^(rm_solo|rm_team|qm_1v1|qm_2v2|qm_3v3|qm_4v4)$")
):
    """
    Fetch player data and generate AI coaching analysis
    
    - profile_id: Steam ID or AoE4 World Profile ID
    - limit: Number of recent games to analyze (1-50)
    - leaderboard: Game mode to analyze
    """
    print(f"DEBUG: Fetching data for profile_id={profile_id}, limit={limit}, leaderboard={leaderboard}")
    
    async with AoE4WorldClient() as client:
        # Get player profile
        player_data = await client.get_player(profile_id)
        print(f"DEBUG: Player data: {player_data is not None}")
        
        if not player_data:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Get recent games
        games_data = await client.get_player_games(profile_id, limit=limit, leaderboard=leaderboard)
        print(f"DEBUG: Got {len(games_data)} games from API, type: {type(games_data)}")
        
        # Debug first game structure
        if games_data and len(games_data) > 0:
            print(f"DEBUG: First game type: {type(games_data[0])}")
            if isinstance(games_data[0], dict):
                print(f"DEBUG: First game keys: {list(games_data[0].keys())}")
        
        # Parse games
        games = []
        for i, game_data in enumerate(games_data):
            game = client.parse_game(game_data, profile_id)
            if game:
                games.append(game)
                print(f"DEBUG: Successfully parsed game {game.game_id}")
            else:
                print(f"DEBUG: Failed to parse game {i+1}")
        
        print(f"DEBUG: Successfully parsed {len(games)} games")
        
        # Analyze performance
        analysis = client.analyze_performance(games)
        print(f"DEBUG: Analysis: {analysis}")
        
        # Generate AI coaching report
        coaching_report = await generate_coaching_report(player_data, analysis, games)
        
        return {
            "success": True,
            "player": {
                "profile_id": player_data.get("profile_id"),
                "name": player_data.get("name"),
                "steam_id": player_data.get("steam_id"),
                "country": player_data.get("country"),
                "avatar_url": player_data.get("avatar_url")
            },
            "analysis": analysis,
            "recent_games": [
                {
                    "game_id": g.game_id,
                    "map": g.map,
                    "civilization": g.player_civ,
                    "result": g.player_result,
                    "rating": g.player_rating,
                    "rating_diff": g.player_rating_diff,
                    "opponent": {
                        "name": g.opponent_name,
                        "civilization": g.opponent_civ,
                        "rating": g.opponent_rating
                    },
                    "duration": g.duration
                }
                for g in games[:5]  # Include last 5 games in detail
            ],
            "coaching_report": {
                **coaching_report,
                "ai_generated": bool(ai_client and "error" not in coaching_report),
                "ai_provider": active_provider if (ai_client and "error" not in coaching_report) else None,
                "disclaimer": f"🤖 AI-Generated Coaching Advice ({active_provider})" if ai_client and "error" not in coaching_report else "📋 Template Report (Configure OPENAI_API_KEY or ZAI_API_KEY for AI coaching)"
            }
        }

def normalize_coaching_report(report: dict) -> dict:
    """Normalize AI coaching report to ensure correct data types"""
    # Ensure arrays for fields that should be arrays
    array_fields = ['strengths', 'improvements', 'civ_recommendations', 'map_advice', 'training_plan']

    for field in array_fields:
        if field in report:
            value = report[field]
            # If it's a string, split it or wrap it in an array
            if isinstance(value, str):
                # Try to split by newlines or bullet points
                if '\n' in value:
                    report[field] = [line.strip('- •*') for line in value.split('\n') if line.strip()]
                else:
                    report[field] = [value]
            # If it's a dict, convert values to list
            elif isinstance(value, dict):
                report[field] = list(value.values())
            # Ensure it's a list
            elif not isinstance(value, list):
                report[field] = [str(value)]

    # Ensure improvements is an array of objects with proper structure
    if 'improvements' in report and isinstance(report['improvements'], list):
        normalized_improvements = []
        for imp in report['improvements']:
            if isinstance(imp, str):
                # Convert string to object format
                normalized_improvements.append({"issue": imp, "fix": "See coaching notes"})
            elif isinstance(imp, dict):
                normalized_improvements.append(imp)
        report['improvements'] = normalized_improvements

    return report

async def generate_coaching_report(player_data: dict, analysis: dict, games: list) -> dict:
    """
    Generate AI-powered coaching report using OpenAI
    """
    print(f"DEBUG: AI provider: {active_provider}")
    print(f"DEBUG: AI client initialized: {ai_client is not None}")

    if not ai_client:
        # Return template report without AI
        print("DEBUG: No AI client available, using template report")
        return generate_template_report(analysis)
    
    # Prepare data for AI
    player_name = player_data.get("name", "Player")
    
    prompt = f"""You are an expert Age of Empires IV coach analyzing a player's recent performance.

Player: {player_name}

Performance Summary:
- Total Games: {analysis.get('total_games', 0)}
- Win Rate: {analysis.get('win_rate', 0)}%
- Current Rating: {analysis.get('current_rating', 0)}
- Average Rating Change per game: {analysis.get('avg_rating_change', 0)}

Civilization Performance:
{json.dumps(analysis.get('civilization_stats', {}), indent=2)}

Map Performance:
{json.dumps(analysis.get('map_stats', {}), indent=2)}

IMPORTANT:
- Respond in ENGLISH only
- Output ONLY valid JSON, no additional text
- Do not include reasoning or explanations outside the JSON structure

Provide a coaching report with:
1. Overall performance rating (S/A/B/C/D)
2. Key strengths based on the data (2-3 points)
3. Areas for improvement (3-4 specific points)
4. Civilization recommendations (which civs to focus on)
5. Map-specific advice
6. Actionable training plan for next 5 games

Format as JSON with these keys: rating, strengths, improvements, civ_recommendations, map_advice, training_plan"""

    # Determine model to use
    if AI_MODEL:
        model = AI_MODEL
    elif active_provider == "zai":
        model = "glm-4.6"  # z.ai flagship model (GLM-4.6, not 4.7)
    else:
        model = "gpt-4o-mini"  # OpenAI default model

    try:
        print(f"DEBUG: Calling {active_provider} API with model {model}...")

        # Prepare API call parameters
        api_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert AoE IV coach providing data-driven, actionable advice in English. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 4000  # Increased for longer responses
        }

        # GLM models support additional parameters
        if active_provider == "zai":
            # Disable extended thinking mode to get direct output
            api_params["extra_body"] = {"thinking": {"type": "disabled"}}

        response = ai_client.chat.completions.create(**api_params)

        print(f"DEBUG: {active_provider} API call successful")
        message = response.choices[0].message

        # GLM models may use reasoning_content instead of content
        content = message.content
        if not content and hasattr(message, 'reasoning_content'):
            content = message.reasoning_content
            print(f"DEBUG: Using reasoning_content instead of content")

        print(f"DEBUG: AI response length: {len(content) if content else 0}")
        print(f"DEBUG: Finish reason: {response.choices[0].finish_reason}")

        if not content:
            print("DEBUG: Empty response from AI")
            return {"error": "Empty response from AI", "fallback": generate_template_report(analysis)}

        try:
            parsed_response = json.loads(content)
            # Normalize response format to ensure arrays where expected
            return normalize_coaching_report(parsed_response)
        except json.JSONDecodeError:
            print("DEBUG: Failed to parse AI response as JSON")
            return {"raw_analysis": content, "error": "Failed to parse AI response"}

    except Exception as e:
        print(f"DEBUG: OpenAI API error: {str(e)}")
        print(f"DEBUG: Error type: {type(e).__name__}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return {
            "error": f"AI analysis failed: {str(e)}",
            "fallback": generate_template_report(analysis)
        }

def generate_template_report(analysis: dict) -> dict:
    """Generate a template coaching report without AI"""
    win_rate = analysis.get("win_rate", 0)
    
    # Determine rating
    if win_rate >= 70:
        rating = "S"
    elif win_rate >= 60:
        rating = "A"
    elif win_rate >= 50:
        rating = "B"
    elif win_rate >= 40:
        rating = "C"
    else:
        rating = "D"
    
    # Find best/worst civs
    civ_stats = analysis.get("civilization_stats", {})
    best_civ = max(civ_stats.items(), key=lambda x: x[1].get("win_rate", 0))[0] if civ_stats else "Unknown"
    worst_civ = min(civ_stats.items(), key=lambda x: x[1].get("win_rate", 0))[0] if civ_stats else "Unknown"
    
    return {
        "rating": rating,
        "note": "AI coaching requires OpenAI API key. Using template analysis.",
        "strengths": [
            f"Strong performance with {best_civ}" if best_civ != "Unknown" else "Consistent civ selection",
            f"Maintaining {analysis.get('current_rating', 0)} rating" if analysis.get('current_rating', 0) > 0 else "Active ranked play"
        ],
        "improvements": [
            {
                "issue": f"Lower win rate with {worst_civ}",
                "fix": f"Practice {worst_civ} build orders in skirmish mode"
            } if worst_civ != "Unknown" else {
                "issue": "Win rate below 50%",
                "fix": "Focus on one civilization to master"
            },
            {
                "issue": "Review recent losses",
                "fix": "Watch your own replays to identify mistakes"
            }
        ],
        "civ_recommendations": [
            f"Focus on {best_civ} - your strongest civilization" if best_civ != "Unknown" else "Try English or French for beginners"
        ],
        "map_advice": [
            "Practice on Arabia and Arabia-like open maps",
            "Learn walling patterns for closed maps"
        ],
        "training_plan": [
            f"Play 5 games with {best_civ}" if best_civ != "Unknown" else "Pick one civ and play 5 games",
            "Focus on consistent build order execution",
            "Practice scouting in first 5 minutes",
            "Review one loss replay after each session"
        ]
    }

@app.get("/api/game/{profile_id}/{game_id}")
async def get_game_build_order(
    profile_id: str,
    game_id: str,
    sig: Optional[str] = Query(None, description="Optional signature for private games")
):
    """
    Fetch detailed game summary including build order

    - profile_id: Steam ID or AoE4 World Profile ID
    - game_id: Game ID to fetch
    - sig: Optional signature for authentication (from game URL)
    """
    print(f"DEBUG: Fetching build order for game {game_id}, profile {profile_id}")

    async with AoE4WorldClient() as client:
        # Get game summary
        summary_data = await client.get_game_summary(profile_id, game_id, sig)

        if not summary_data:
            raise HTTPException(status_code=404, detail="Game not found or not accessible")

        # Parse the summary
        game_summary = client.parse_game_summary(summary_data, profile_id)

        if not game_summary:
            raise HTTPException(status_code=500, detail="Failed to parse game data")

        # Helper function to format time
        def format_time(seconds):
            if seconds is None:
                return None
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}:{secs:02d}"

        # Return structured data
        return {
            "success": True,
            "game": {
                "game_id": game_summary.game_id,
                "map": game_summary.map_name,
                "duration": game_summary.duration,
                "duration_formatted": format_time(game_summary.duration),
                "win_reason": game_summary.win_reason
            },
            "player": {
                "name": game_summary.player_name,
                "civilization": game_summary.player_civ,
                "result": game_summary.player_result,
                "apm": game_summary.player_apm,
                "final_score": game_summary.final_score,
                "resources_gathered": game_summary.total_resources_gathered,
                "resources_spent": game_summary.total_resources_spent
            },
            "opponent": {
                "name": game_summary.opponent_name,
                "civilization": game_summary.opponent_civ,
                "apm": game_summary.opponent_apm
            },
            "timings": {
                "player": {
                    "feudal_age": {
                        "seconds": game_summary.feudal_age_time,
                        "formatted": format_time(game_summary.feudal_age_time)
                    },
                    "castle_age": {
                        "seconds": game_summary.castle_age_time,
                        "formatted": format_time(game_summary.castle_age_time)
                    },
                    "imperial_age": {
                        "seconds": game_summary.imperial_age_time,
                        "formatted": format_time(game_summary.imperial_age_time)
                    }
                },
                "opponent": {
                    "feudal_age": {
                        "seconds": game_summary.opponent_feudal_age_time,
                        "formatted": format_time(game_summary.opponent_feudal_age_time)
                    },
                    "castle_age": {
                        "seconds": game_summary.opponent_castle_age_time,
                        "formatted": format_time(game_summary.opponent_castle_age_time)
                    },
                    "imperial_age": {
                        "seconds": game_summary.opponent_imperial_age_time,
                        "formatted": format_time(game_summary.opponent_imperial_age_time)
                    }
                }
            },
            "build_order": game_summary.build_order,
            "opponent_build_order": game_summary.opponent_build_order,
            "raw_data": summary_data  # Include raw data for debugging/future use
        }

@app.get("/api/sample-report")
async def sample_report():
    """Return a sample coaching report for demo purposes"""
    return {
        "rating": "B+",
        "strengths": [
            "Strong English civilization performance (65% win rate)",
            "Good rating trend (+15 avg per game)",
            "Consistent play on open maps"
        ],
        "improvements": [
            {
                "issue": "Low win rate on water maps (30%)",
                "impact": "Losing free ELO on maps like Archipelago",
                "fix": "Practice English Dock into Fast Castle build"
            },
            {
                "issue": "Struggling against French rush",
                "impact": "0-3 record vs French in last 10 games",
                "fix": "Learn early defensive build orders, practice walling"
            },
            {
                "issue": "Inconsistent late game (40+ min games)",
                "impact": "Win rate drops to 35% after 40 minutes",
                "fix": "Focus on trade and eco upgrades in Imperial"
            }
        ],
        "civ_recommendations": [
            "English: Your best civ (65% WR) - keep playing it",
            "French: Consider learning it (strong meta civ)",
            "Avoid: Delhi Sultanate (20% WR in your games)"
        ],
        "map_advice": [
            "Arabia: Strong performance, keep it up",
            "Black Forest: Practice booming into Imperial",
            "Water maps: Need significant improvement"
        ],
        "training_plan": [
            "Play 5 English games focusing on consistent Dark Age",
            "Practice French rush defense in skirmish (AI Hardest)",
            "Watch one pro game on a water map",
            "Learn 2 late-game unit compositions for English"
        ],
        "ai_generated": True,
        "disclaimer": "🤖 AI-Generated Coaching Advice (Sample)"
    }

# ============================================================================
# Rubric-Based Coaching Endpoints
# ============================================================================

def load_rubric(rubric_id: str) -> Optional[dict]:
    """Load a rubric JSON file by ID"""
    try:
        rubric_path = os.path.join(RUBRIC_LIBRARY_PATH, f"{rubric_id}.json")
        if not os.path.exists(rubric_path):
            print(f"DEBUG: Rubric file not found: {rubric_path}")
            return None

        with open(rubric_path, 'r', encoding='utf-8') as f:
            rubric = json.load(f)

        print(f"DEBUG: Successfully loaded rubric: {rubric_id}")
        return rubric
    except Exception as e:
        print(f"ERROR: Failed to load rubric {rubric_id}: {e}")
        return None

def extract_all_success_criteria(phases: list) -> list:
    """Extract all success criteria from rubric phases"""
    criteria = []
    for phase in phases:
        phase_name = phase.get("name", "Unknown")
        for criterion in phase.get("success_criteria", []):
            criteria.append(f"{phase_name}: {criterion}")
    return criteria

def extract_all_common_mistakes(phases: list) -> list:
    """Extract all common mistakes from rubric phases"""
    mistakes = []
    for phase in phases:
        for mistake_obj in phase.get("common_mistakes", []):
            mistakes.append({
                "phase": phase.get("name", "Unknown"),
                "mistake": mistake_obj.get("mistake", ""),
                "consequence": mistake_obj.get("consequence", ""),
                "fix": mistake_obj.get("fix", "")
            })
    return mistakes

@app.get("/api/rubrics")
async def list_rubrics():
    """List all available rubrics with metadata"""
    try:
        if not os.path.exists(RUBRIC_LIBRARY_PATH):
            raise HTTPException(status_code=500, detail=f"Rubric library not found at {RUBRIC_LIBRARY_PATH}")

        rubrics = []
        for filename in os.listdir(RUBRIC_LIBRARY_PATH):
            if filename.endswith('.json'):
                rubric_id = filename[:-5]  # Remove .json extension
                rubric = load_rubric(rubric_id)
                if rubric:
                    rubrics.append({
                        "id": rubric.get("id", rubric_id),
                        "title": rubric.get("title", rubric_id),
                        "difficulty": rubric.get("difficulty", "unknown"),
                        "civilizations": rubric.get("civilizations", []),
                        "archetype": rubric.get("archetype", ""),
                        "overview": rubric.get("overview", "")
                    })

        print(f"DEBUG: Found {len(rubrics)} rubrics")
        return {
            "success": True,
            "rubrics": rubrics
        }
    except Exception as e:
        print(f"ERROR: Failed to list rubrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_rubric_coaching(rubric: dict, game_summary: dict, profile_id: str) -> dict:
    """Generate AI coaching analysis comparing game execution to rubric"""
    if not ai_client:
        return {
            "error": "AI client not configured",
            "overall_assessment": "AI coaching requires API key configuration."
        }

    try:
        # Extract game metrics
        player = game_summary.get("player", {})
        game = game_summary.get("game", {})
        timings = game_summary.get("timings", {}).get("player", {})
        build_order = game_summary.get("build_order", [])[:20]  # First 20 items

        # Extract rubric data
        benchmarks = rubric.get("benchmarks", {})
        phases = rubric.get("phases", [])
        success_criteria = extract_all_success_criteria(phases)
        common_mistakes = extract_all_common_mistakes(phases)

        # Format build order for prompt
        build_order_str = "\n".join([
            f"  - {item.get('icon', 'Unknown').split('/')[-1].replace('_', ' ')} at {(item.get('finished') or item.get('constructed') or ['-'])[0]}s"
            for item in build_order[:20]
        ])

        # Construct comprehensive prompt
        prompt = f"""You are an expert Age of Empires IV coach. Compare the player's actual game execution against this professional build order rubric.

RUBRIC: {rubric.get('title', 'Unknown')}
Overview: {rubric.get('overview', '')}
Archetype: {rubric.get('archetype', '')}
Difficulty: {rubric.get('difficulty', '')}

RUBRIC BENCHMARKS:
- Feudal Age: {benchmarks.get('feudal_age', 'N/A')}s ({benchmarks.get('feudal_age', 0) // 60}:{benchmarks.get('feudal_age', 0) % 60:02d})
- Castle Age: {benchmarks.get('castle_age', 'N/A')}s ({benchmarks.get('castle_age', 0) // 60}:{benchmarks.get('castle_age', 0) % 60:02d})
- Imperial Age: {benchmarks.get('imperial_age', 'N/A')}s
- Villagers at 10min: {benchmarks.get('villagers_at_10min', 'N/A')}
- Villagers at Castle: {benchmarks.get('villagers_at_castle', 'N/A')}

RUBRIC SUCCESS CRITERIA:
{chr(10).join(f"- {c}" for c in success_criteria[:10])}

RUBRIC COMMON MISTAKES:
{chr(10).join(f"- {m['mistake']} → {m['consequence']}" for m in common_mistakes[:5])}

PLAYER'S ACTUAL EXECUTION:
Player: {player.get('name', 'Unknown')}
Civilization: {player.get('civilization', 'Unknown')}
Map: {game.get('map', 'Unknown')}
Result: {player.get('result', 'Unknown')}
Duration: {game.get('duration_formatted', 'Unknown')}

ACTUAL TIMINGS:
- Feudal Age: {timings.get('feudal_age', {}).get('formatted', 'N/A')} ({timings.get('feudal_age', {}).get('seconds', 0)}s)
- Castle Age: {timings.get('castle_age', {}).get('formatted', 'N/A')} ({timings.get('castle_age', {}).get('seconds', 0)}s)
- Imperial Age: {timings.get('imperial_age', {}).get('formatted', 'N/A')} ({timings.get('imperial_age', {}).get('seconds', 0)}s)

PERFORMANCE:
- APM: {player.get('apm', 'N/A')}
- Resources Gathered: {player.get('resources_gathered', 'N/A')}
- Resources Spent: {player.get('resources_spent', 'N/A')}

BUILD ORDER (first 20 items):
{build_order_str}

TASK:
Compare the player's execution against the rubric and provide:

1. Overall Assessment (2-3 sentences summarizing execution quality)
2. Benchmark Comparison (compare expected vs actual timings with ratings)
3. Execution Mistakes (specific errors with evidence from the game data)
4. Success Criteria Evaluation (which criteria were met/missed)
5. Improvement Suggestions (3-5 prioritized actionable items)
6. Open-ended Strategic Advice (2-3 paragraphs of deeper insights)

IMPORTANT:
- Respond in ENGLISH only
- Output ONLY valid JSON, no additional text
- Be specific and use evidence from the game data
- Rate benchmarks as "excellent", "good", "average", "poor", or "very_poor"
- If civilization doesn't match rubric, note it but still provide useful analysis

JSON FORMAT:
{{
  "overall_assessment": "2-3 sentences...",
  "benchmark_comparison": [
    {{
      "metric": "Feudal Age",
      "expected": "5:00",
      "actual": "5:15",
      "delta_seconds": 15,
      "rating": "good"
    }}
  ],
  "execution_mistakes": [
    {{
      "mistake": "Specific mistake...",
      "evidence": "Evidence from game data...",
      "consequence": "What this caused...",
      "fix": "How to fix it..."
    }}
  ],
  "success_criteria_evaluation": [
    {{
      "criterion": "Zero TC idle time",
      "met": true,
      "notes": "Explanation..."
    }}
  ],
  "improvement_suggestions": ["Suggestion 1...", "Suggestion 2...", "Suggestion 3..."],
  "open_ended_advice": "2-3 paragraphs of strategic advice..."
}}"""

        # Determine model
        if AI_MODEL:
            model = AI_MODEL
        elif active_provider == "zai":
            model = "glm-4.6"
        else:
            model = "gpt-4o-mini"

        print(f"DEBUG: Calling {active_provider} API for rubric coaching with model {model}")

        # Prepare API call
        api_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert AoE IV coach providing detailed, data-driven analysis in English. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 4000
        }

        if active_provider == "zai":
            api_params["extra_body"] = {"thinking": {"type": "disabled"}}

        response = ai_client.chat.completions.create(**api_params)

        content = response.choices[0].message.content
        if not content and hasattr(response.choices[0].message, 'reasoning_content'):
            content = response.choices[0].message.reasoning_content

        print(f"DEBUG: AI response length: {len(content) if content else 0}")

        if not content:
            return {
                "error": "Empty AI response",
                "overall_assessment": "Failed to generate coaching analysis."
            }

        # Parse JSON response
        try:
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse AI response as JSON: {e}")
            return {
                "error": "Failed to parse AI response",
                "overall_assessment": "AI returned invalid response format.",
                "raw_response": content[:500]
            }

    except Exception as e:
        print(f"ERROR: Rubric coaching generation failed: {e}")
        import traceback
        print(traceback.format_exc())
        return {
            "error": f"Coaching generation failed: {str(e)}",
            "overall_assessment": "An error occurred during analysis."
        }

@app.post("/api/game/{profile_id}/{game_id}/coaching")
async def generate_game_coaching(
    profile_id: str,
    game_id: str,
    rubric_id: str = Query(..., description="Rubric ID to use for coaching"),
    sig: Optional[str] = Query(None, description="Optional signature for private games")
):
    """
    Generate AI coaching for a specific game using a rubric

    - profile_id: Player's profile ID
    - game_id: Game ID to analyze
    - rubric_id: ID of rubric to use for comparison
    - sig: Optional signature for authentication
    """
    print(f"DEBUG: Generating coaching for game {game_id} with rubric {rubric_id}")

    # Load rubric
    rubric = load_rubric(rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail=f"Rubric not found: {rubric_id}")

    # Fetch game data
    async with AoE4WorldClient() as client:
        summary_data = await client.get_game_summary(profile_id, game_id, sig)

        if not summary_data:
            raise HTTPException(status_code=404, detail="Game not found or not accessible")

        game_summary_obj = client.parse_game_summary(summary_data, profile_id)

        if not game_summary_obj:
            raise HTTPException(status_code=500, detail="Failed to parse game data")

        # Format game summary for AI
        def format_time(seconds):
            if seconds is None:
                return None
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}:{secs:02d}"

        game_summary = {
            "game": {
                "game_id": game_summary_obj.game_id,
                "map": game_summary_obj.map_name,
                "duration": game_summary_obj.duration,
                "duration_formatted": format_time(game_summary_obj.duration),
                "win_reason": game_summary_obj.win_reason
            },
            "player": {
                "name": game_summary_obj.player_name,
                "civilization": game_summary_obj.player_civ,
                "result": game_summary_obj.player_result,
                "apm": game_summary_obj.player_apm,
                "resources_gathered": game_summary_obj.total_resources_gathered,
                "resources_spent": game_summary_obj.total_resources_spent
            },
            "timings": {
                "player": {
                    "feudal_age": {
                        "seconds": game_summary_obj.feudal_age_time,
                        "formatted": format_time(game_summary_obj.feudal_age_time)
                    },
                    "castle_age": {
                        "seconds": game_summary_obj.castle_age_time,
                        "formatted": format_time(game_summary_obj.castle_age_time)
                    },
                    "imperial_age": {
                        "seconds": game_summary_obj.imperial_age_time,
                        "formatted": format_time(game_summary_obj.imperial_age_time)
                    }
                }
            },
            "build_order": game_summary_obj.build_order
        }

        # Generate coaching
        coaching = await generate_rubric_coaching(rubric, game_summary, profile_id)

        # Check for civilization mismatch
        player_civ = game_summary_obj.player_civ.lower() if game_summary_obj.player_civ else ""
        rubric_civs = [c.lower() for c in rubric.get("civilizations", [])]
        civ_mismatch = player_civ and rubric_civs and player_civ not in rubric_civs

        return {
            "success": True,
            "rubric": {
                "id": rubric.get("id"),
                "title": rubric.get("title"),
                "difficulty": rubric.get("difficulty"),
                "civilizations": rubric.get("civilizations")
            },
            "game": {
                "player_civilization": game_summary_obj.player_civ,
                "result": game_summary_obj.player_result
            },
            "civ_mismatch": civ_mismatch,
            "coaching": coaching,
            "ai_provider": active_provider if ai_client else None
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
