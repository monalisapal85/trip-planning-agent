"""
Trip Planning Agent — FastAPI Backend
---------------------------------------
Wraps the agent in a REST API so it can be accessed
from any frontend, mobile app, or browser.

Usage:
  pip3 install fastapi uvicorn
  uvicorn api:app --reload

Endpoints:
  POST /chat              — send a message to the agent
  GET  /history/{session} — load conversation history
  GET  /trips/{session}   — load saved trips
  DELETE /history/{session} — clear a session
"""

import os
import json
import uuid
import anthropic

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from flight_search_tool import search_flights
from hotel_search_tool  import search_hotels
from weather_tool       import get_current_weather, get_forecast
from memory             import save_message, load_history, save_trip, load_trips, clear_history


# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Trip Planning Agent API",
    description="AI-powered trip planning with real flights, hotels and weather.",
    version="1.0.0",
)

# Allow requests from any frontend (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Anthropic client ───────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ── Request / Response models ──────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message:    str
    session_id: str | None = None   # if None, a new session is created


class ChatResponse(BaseModel):
    answer:     str
    session_id: str


class TripSaveRequest(BaseModel):
    session_id:  str
    destination: str
    dates:       str
    notes:       str | None = None


# ── Tool definitions ───────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "search_flights",
        "description": "Search for real flights between two cities. Use IATA airport codes. Dates in YYYY-MM-DD format.",
        "input_schema": {
            "type": "object",
            "properties": {
                "origin":         {"type": "string", "description": "Departure IATA code e.g. ATL"},
                "destination":    {"type": "string", "description": "Arrival IATA code e.g. NRT"},
                "departure_date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "return_date":    {"type": "string", "description": "Optional return date"},
            },
            "required": ["origin", "destination", "departure_date"],
        },
    },
    {
        "name": "search_hotels",
        "description": "Search for real hotels at a destination. Use city names. Dates in YYYY-MM-DD format.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string", "description": "City name e.g. Tokyo"},
                "check_in":    {"type": "string", "description": "Check-in date YYYY-MM-DD"},
                "check_out":   {"type": "string", "description": "Check-out date YYYY-MM-DD"},
                "adults":      {"type": "integer", "description": "Number of guests"},
            },
            "required": ["destination", "check_in", "check_out"],
        },
    },
    {
        "name": "get_current_weather",
        "description": "Get current weather at a destination city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name e.g. Tokyo"},
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_forecast",
        "description": "Get a 5-day weather forecast for a destination city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name e.g. Tokyo"},
                "days": {"type": "integer", "description": "Number of days (max 5)"},
            },
            "required": ["city"],
        },
    },
]


# ── Tool dispatcher ────────────────────────────────────────────────────────────
def run_tool(name: str, inputs: dict) -> str:
    if name == "search_flights":
        return json.dumps(search_flights(**inputs))
    elif name == "search_hotels":
        return json.dumps(search_hotels(**inputs))
    elif name == "get_current_weather":
        return json.dumps(get_current_weather(**inputs))
    elif name == "get_forecast":
        return json.dumps(get_forecast(**inputs))
    return json.dumps({"error": f"Unknown tool: {name}"})


# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM = """You are a smart, friendly trip planning assistant with memory.
You have tools to search real flights, hotels, and weather.
When a user asks about a trip, use the tools to get real data.
Always search flights AND hotels AND weather when planning a full trip.
Guidelines:
- Use IATA codes for flights (ATL, NRT, JFK, LHR, CDG etc.)
- Use city names for hotels and weather
- Dates must be YYYY-MM-DD
- Summarize results clearly with a recommendation
- Be concise and friendly
"""


# ── Agent logic ────────────────────────────────────────────────────────────────
def run_agent(user_message: str, session_id: str) -> str:
    """Run the agent loop and return the final answer."""

    # Save user message
    save_message(session_id, "user", user_message)

    # Load full history from Firestore
    history = load_history(session_id)

    # Agentic loop
    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=SYSTEM,
            tools=TOOLS,
            messages=history,
        )

        if response.stop_reason == "tool_use":
            history.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     result,
                    })

            history.append({"role": "user", "content": tool_results})

        else:
            answer = " ".join(
                block.text for block in response.content
                if hasattr(block, "text")
            )
            # Save assistant response
            save_message(session_id, "assistant", answer)
            return answer


# ── API endpoints ──────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Trip Planning Agent API is running"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Send a message to the agent and get a response.
    If no session_id is provided, a new one is created.
    """
    session_id = req.session_id or str(uuid.uuid4())[:8]

    try:
        answer = run_agent(req.message, session_id)
        return ChatResponse(answer=answer, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{session_id}")
def get_history(session_id: str):
    """Load full conversation history for a session."""
    try:
        history = load_history(session_id, limit=50)
        return {"session_id": session_id, "messages": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trips/{session_id}")
def get_trips(session_id: str):
    """Load all saved trips for a session."""
    try:
        trips = load_trips(session_id)
        return {"session_id": session_id, "trips": trips, "count": len(trips)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history/{session_id}")
def delete_history(session_id: str):
    """Clear all messages for a session."""
    try:
        clear_history(session_id)
        return {"status": "cleared", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
