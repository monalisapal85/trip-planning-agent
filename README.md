# Trip Planning Agent

An end-to-end AI agent that plans trips using real flight, hotel, and weather data — built from scratch with Claude, FastAPI, Firestore, and deployed on GCP.

**Live demo:** https://trip-agent-492405.web.app  
**API:** https://trip-planning-agent-evvvgwttwa-ue.a.run.app/docs

---

## What it does

You describe a trip in plain English. The agent searches real flights, hotels, and weather — then returns a structured plan with recommendations and a budget estimate.

```
You: Search flights ATL to NRT on 2026-08-10, hotels in Tokyo Aug 10-13, 2 people

Agent: Here's your Tokyo trip plan:
  ✈ American AA1567 | $1,560 | 17h 40m | 1 stop
  🏨 Shinjuku Granbell Hotel | $98/night | 4-star | Rating 4.0
  🌤 28°C, Humid, 71% humidity
  💰 Estimated total: $1,854 per person
```

---

## Architecture

```
Browser (Firebase Hosting)
    │
    ▼
FastAPI Backend (GCP Cloud Run)
    │
    ├── Claude Haiku (Anthropic API) — agent brain
    │
    ├── Tools
    │   ├── flight_search_tool.py  → Serpapi Google Flights
    │   ├── hotel_search_tool.py   → Serpapi Google Hotels
    │   └── weather_tool.py        → OpenWeatherMap API
    │
    └── memory.py → Firestore (GCP) — persistent conversation memory
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Agent brain | Claude Haiku (Anthropic API) |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Flight data | Serpapi Google Flights engine |
| Hotel data | Serpapi Google Hotels engine |
| Weather data | OpenWeatherMap API |
| Memory | Google Cloud Firestore |
| Hosting (API) | GCP Cloud Run (serverless, auto-scaling) |
| Hosting (UI) | Firebase Hosting |
| Secrets | GCP Secret Manager |
| Frontend | Vanilla HTML/CSS/JS |

---

## Project structure

```
trip-planning-agent/
├── api.py                  # FastAPI backend — 4 REST endpoints
├── agent.py                # Terminal agent loop (for local testing)
├── memory.py               # Firestore read/write for conversation history
├── flight_search_tool.py   # Serpapi flight search tool
├── hotel_search_tool.py    # Serpapi hotel search tool
├── weather_tool.py         # OpenWeatherMap current + forecast tool
├── index.html              # Frontend — split chat + dashboard UI
├── Dockerfile              # Container config for Cloud Run
├── requirements.txt        # Python dependencies
└── deploy.sh               # One-command GCP deployment script
```

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/chat` | Send a message, get agent response |
| GET | `/history/{session_id}` | Load conversation history |
| GET | `/trips/{session_id}` | Load saved trip plans |
| DELETE | `/history/{session_id}` | Clear a session |

**Example request:**
```bash
curl -X POST https://trip-planning-agent-evvvgwttwa-ue.a.run.app/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Plan me a 3 day trip to Tokyo in August from Atlanta"}'
```

---

## How the agent loop works

1. User sends a message to `/chat`
2. Claude reads the message + conversation history from Firestore
3. Claude decides which tools to call (flights, hotels, weather)
4. Tools call real APIs and return structured data
5. Claude synthesizes results into a human-readable response
6. Response + history saved back to Firestore
7. Answer returned to the user

The agent loops steps 3–5 until it has all the data it needs — this is the core agentic pattern.

---

## Running locally

```bash
# Clone
git clone https://github.com/monalisapal85/trip-planning-agent.git
cd trip-planning-agent

# Install dependencies
pip3 install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="your_key"
export SERPAPI_API_KEY="your_key"
export OPENWEATHER_API_KEY="your_key"

# Run the API
uvicorn api:app --reload

# Open in browser
open http://localhost:8000/docs
```

---

## Deployment

```bash
# One command deploys to GCP Cloud Run
chmod +x deploy.sh
./deploy.sh
```

The script:
1. Enables required GCP APIs
2. Stores secrets in Secret Manager
3. Builds and pushes Docker image via Cloud Build
4. Deploys to Cloud Run with secret injection

---

## Key design decisions

**Anthropic SDK directly over LangChain** — LangChain's agent layer has compatibility issues with Python 3.14. Using the Anthropic SDK directly gives full control over the tool-calling loop with no framework overhead.

**Firestore for memory** — Each conversation is stored by session ID. Loading history on every request gives the agent full context without any in-memory state on the server — critical for serverless Cloud Run deployments.

**Serpapi over Amadeus** — Amadeus shut down its self-service developer portal in 2026. Serpapi's Google Flights and Hotels engines provide equivalent real-time data with a simpler free-tier API.

**Cloud Run over Cloud Functions** — The agent loop can take 20–30 seconds for multi-tool calls. Cloud Run's configurable timeout (up to 5 minutes) handles this cleanly. Functions have a tighter limit.

---

## Built by

Monalisa Pal — Product Owner & Scrum Master  
Learning AI agent development hands-on alongside GCP Data Fabric migration work.
