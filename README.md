# AoE IV AI Coach - MVP

AI-powered post-game analysis for Age of Empires IV.

## Features

- Upload AoE IV replay files (`.aoe2record`)
- Automatic game analysis (economy, military, tech)
- AI-generated coaching report with specific improvement tips
- Progress tracking over time

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run backend
python backend/main.py

# Open frontend/index.html in browser
```

## Tech Stack

- **Backend**: Python FastAPI, Celery (async processing)
- **Parser**: Custom AoE IV replay parser (based on aoede)
- **AI**: OpenAI GPT-4o for coaching insights
- **Frontend**: Vanilla HTML/JS with Chart.js

## License

MIT
