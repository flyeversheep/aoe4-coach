"""
AoE IV AI Coach - Backend API
"""
import os
import json
import tempfile
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import openai

from parser import AoE4ReplayParser

# Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

app = FastAPI(title="AoE IV AI Coach", version="0.1.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AoE IV AI Coach API", "version": "0.1.0"}

@app.post("/api/analyze")
async def analyze_replay(file: UploadFile = File(...)):
    """
    Upload and analyze an AoE IV replay file
    """
    # Validate file type
    if not file.filename.endswith('.aoe2record'):
        raise HTTPException(status_code=400, detail="File must be .aoe2record format")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.aoe2record') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Parse replay
        parser = AoE4ReplayParser(tmp_path)
        parsed_data = parser.parse()
        
        # Generate AI coaching report
        coaching_report = await generate_coaching_report(parsed_data)
        
        return {
            "success": True,
            "filename": file.filename,
            "game_info": parsed_data['game_info'],
            "players": parsed_data['players'],
            "summary": parsed_data['summary'],
            "coaching_report": coaching_report
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

async def generate_coaching_report(game_data: dict) -> dict:
    """
    Generate AI-powered coaching report using OpenAI
    """
    if not OPENAI_API_KEY:
        return {
            "error": "OpenAI API key not configured",
            "tips": ["API key needed for AI coaching features"]
        }
    
    # Prepare prompt for AI
    game_summary = json.dumps(game_data['summary'], indent=2)
    players_info = json.dumps([
        {"name": p.name, "civ": p.civ} for p in game_data['players']
    ])
    
    prompt = f"""You are an expert Age of Empires IV coach. Analyze this game and provide specific improvement tips.

Game Summary:
{game_summary}

Players:
{players_info}

Provide a coaching report with:
1. Overall performance rating (S/A/B/C/D)
2. Key strengths (2-3 points)
3. Areas for improvement (3-4 specific points with timestamps if relevant)
4. Actionable training recommendations for next games
5. Civilization-specific tips

Format as JSON with these keys: rating, strengths, improvements, training_plan, civ_tips"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert AoE IV coach providing concise, actionable advice."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Try to parse as JSON, fallback to text
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_analysis": content}
            
    except Exception as e:
        return {
            "error": f"AI analysis failed: {str(e)}",
            "tips": ["Check your OpenAI API key"]
        }

@app.get("/api/sample-report")
async def sample_report():
    """Return a sample coaching report for demo purposes"""
    return {
        "rating": "B+",
        "strengths": [
            "Good early game economy management",
            "Effective unit composition in mid-game"
        ],
        "improvements": [
            {
                "issue": "Late Castle Age (16:30 vs optimal 14:30)",
                "impact": "Lost map control early",
                "fix": "Focus on constant villager production, aim for 14:00 Castle Age"
            },
            {
                "issue": "No scout for 3 minutes (8:00-11:00)",
                "impact": "Missed enemy military building placement",
                "fix": "Set a timer for scout rotation every 2 minutes"
            },
            {
                "issue": "Resource floating at 20:00",
                "impact": "Had 2000+ wood unspent",
                "fix": "Add more production buildings when resources exceed 1000"
            }
        ],
        "training_plan": [
            "Practice Fast Castle build order in scenario editor",
            "Play 3 games focusing on constant villager production",
            "Watch your own replay at 10:00 mark for scout awareness"
        ],
        "civ_tips": [
            "English: Consider Council Hall timing - you went up at 15:00, optimal is 13:00",
            "Use network of castles for defense in late game"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
