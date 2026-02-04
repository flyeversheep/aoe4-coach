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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
