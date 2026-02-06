# 🏰 AoE IV AI Coach

AI-powered post-game analysis for Age of Empires IV using AoE4 World API.

**Live Demo:** https://jarvis-turfiest-soon.ngrok-free.dev/

---

## 🎬 Demo

![AoE IV AI Coach Demo](docs/demo.gif)

*AI-powered post-game analysis with build order coaching*

---

## ✨ Features

- **Player Profile Analysis** - Input Steam ID / Profile ID to fetch match history
- **AI Coaching Reports** - GPT-4o powered personalized improvement tips
- **Build Order Analysis** - View detailed build sequences with timestamps
- **Rubric-Based Coaching** - Compare execution against professional build orders from [youtube-rubric-extractor](https://github.com/flyeversheep/youtube-rubric-extractor)
- **Performance Tracking** - Win rates, rating trends, civilization stats
- **Age Up Timing Comparison** - Compare your timings vs opponents

### AI Providers
- **OpenAI** - GPT-4o-mini (default)
- **z.ai** - GLM-4.7 support for Chinese users
- **Auto-fallback** - Automatically switches based on available API keys

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- OpenAI API key (optional, for AI features)
- z.ai API key (optional, alternative AI provider)

### Installation

```bash
# Clone the repository
git clone https://github.com/flyeversheep/aoe4-coach.git
cd aoe4-coach

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Option 1: OpenAI (recommended)
export OPENAI_API_KEY="sk-..."

# Option 2: z.ai (Chinese alternative)
export ZAI_API_KEY="your-zai-key"
export ZAI_BASE_URL="https://api.z.ai/api/paas/v4/"

# Optional: Rubric library path
export RUBRIC_LIBRARY_PATH="/path/to/rubric_library"
```

### Run

```bash
# Start backend
python backend/main.py

# Open in browser
# Backend serves frontend automatically at http://localhost:8000
```

---

## 📖 How to Use

### 1. Analyze Your Profile
1. Find your AoE IV Profile ID on [AoE4 World](https://aoe4world.com)
2. Enter it in the web interface
3. Select game mode (Ranked Solo, Team, etc.)
4. Click **Analyze**

### 2. View Match Details
1. Click on any game in the recent matches list
2. See detailed build orders and age up timings
3. Compare your performance vs opponent

### 3. Get Rubric Coaching
1. Open a specific game
2. Select a build order rubric from the dropdown
3. Click **Generate Coaching**
4. AI compares your execution against the rubric and provides feedback

### 4. URL Shortcuts
You can paste AoE4 World URLs directly:
- Profile: `https://aoe4world.com/players/12345`
- Game: `https://aoe4world.com/players/12345/games/67890?sig=abc...`

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python FastAPI |
| Frontend | Vanilla HTML/JS, Chart.js |
| Data Source | [AoE4 World API](https://aoe4world.com/api) |
| AI | OpenAI GPT-4o / z.ai GLM-4.7 |
| SSL | certifi for secure API calls |

---

## 📡 API Endpoints

### Player Analysis
```
GET /api/player/{profile_id}?leaderboard=rm_solo&limit=10
```
Returns player profile, match history, and AI coaching report.

### Game Details
```
GET /api/game/{profile_id}/{game_id}?sig={signature}
```
Returns detailed game data including build orders and timings.

### Rubric Coaching
```
POST /api/game/{profile_id}/{game_id}/coaching?rubric_id={rubric_id}
```
Generates AI coaching comparing game execution against a rubric.

### List Rubrics
```
GET /api/rubrics
```
Returns available build order rubrics for coaching.

---

## 🔗 Related Projects

- **[youtube-rubric-extractor](https://github.com/flyeversheep/youtube-rubric-extractor)** - Generate build order rubrics from YouTube videos
- **[AoE4 World](https://aoe4world.com)** - Data source and player profiles

---

## 🗺️ Future Plans

- [ ] Real-time game data via `-dev` mode
- [ ] Detailed replay analysis
- [ ] Build Order training mode
- [ ] Live coaching overlay
- [ ] Replay file upload support

---

## 📝 License

MIT

---

## 🙏 Acknowledgments

- [AoE4 World](https://aoe4world.com) for the excellent API
- Age of Empires IV community for build order knowledge
