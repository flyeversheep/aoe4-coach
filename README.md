# AoE IV AI Coach - MVP

AI-powered post-game analysis for Age of Empires IV using AoE4 World API.

## Features

- Input your Steam ID / Profile ID to fetch match history
- Automatic game analysis using AoE4 World API data
- AI-generated coaching report with specific improvement tips
- Progress tracking over time

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key (optional, for AI features)
export OPENAI_API_KEY="your-key-here"

# Run backend
python backend/main.py

# Open frontend/index.html in browser
```

## How to Use

1. Find your AoE IV Profile ID or Steam ID
2. Enter it in the web interface
3. The app fetches your recent match history from AoE4 World
4. AI analyzes your performance and generates coaching tips

## Tech Stack

- **Backend**: Python FastAPI
- **Data Source**: [AoE4 World API](https://aoe4world.com/api)
- **AI**: OpenAI GPT-4o for coaching insights
- **Frontend**: Vanilla HTML/JS with Chart.js

## Future Plans

- [ ] Real-time game data via -dev mode
- [ ] Detailed replay analysis
- [ ] Build Order training mode
- [ ] Live coaching overlay

## License

MIT
