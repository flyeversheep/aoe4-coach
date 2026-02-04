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
import openai

from aoe4world_client import AoE4WorldClient

# Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

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
            "coaching_report": coaching_report
        }

async def generate_coaching_report(player_data: dict, analysis: dict, games: list) -> dict:
    """
    Generate AI-powered coaching report using OpenAI
    """
    if not OPENAI_API_KEY:
        # Return template report without AI
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

Provide a coaching report with:
1. Overall performance rating (S/A/B/C/D)
2. Key strengths based on the data (2-3 points)
3. Areas for improvement (3-4 specific points)
4. Civilization recommendations (which civs to focus on)
5. Map-specific advice
6. Actionable training plan for next 5 games

Format as JSON with these keys: rating, strengths, improvements, civ_recommendations, map_advice, training_plan"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert AoE IV coach providing data-driven, actionable advice."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_analysis": content, "error": "Failed to parse AI response"}
            
    except Exception as e:
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
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
