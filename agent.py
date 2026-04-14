"""
Trip Planning Agent — with Persistent Memory
----------------------------------------------
Every conversation is saved to Firestore and reloaded
automatically so the agent remembers across sessions.

Usage:
  python3 agent.py                        ← starts a new session
  python3 agent.py --session my_session   ← resumes a saved session

Prerequisites:
  pip3 install anthropic google-search-results requests google-cloud-firestore
  export SERPAPI_API_KEY="your_key"
  export OPENWEATHER_API_KEY="your_key"
  export ANTHROPIC_API_KEY="your_key"
"""

import os
import sys
import json
import uuid
import anthropic

from flight_search_tool import search_flights
from hotel_search_tool  import search_hotels
from weather_tool       import get_current_weather, get_forecast
from memory             import save_message, load_history, save_trip, load_trips


# ── Anthropic client ───────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ── Tool definitions ───────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "search_flights",
        "description": "Search for real flights between two cities. Use IATA airport codes (e.g. ATL, NRT, JFK). Dates in YYYY-MM-DD format.",
        "input_schema": {
            "type": "object",
            "properties": {
                "origin":         {"type": "string", "description": "Departure IATA code e.g. ATL"},
                "destination":    {"type": "string", "description": "Arrival IATA code e.g. NRT"},
                "departure_date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "return_date":    {"type": "string", "description": "Optional return date for round trips"},
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
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM = """You are a smart, friendly trip planning assistant with memory.

You have tools to search real flights, hotels, and weather.
When a user asks about a trip, use the tools to get real data — don't guess.
Always search flights AND hotels AND weather when planning a full trip.

You remember previous conversations — reference past trips when relevant.
For example: "Last time you flew to Tokyo from Atlanta — want the same route?"

Guidelines:
- Use IATA codes for flights (ATL, NRT, JFK, LHR, CDG etc.)
- Use city names for hotels and weather
- Dates must be YYYY-MM-DD
- Summarize results clearly with a recommendation
- Be concise and friendly
"""


# ── Agent chat function ────────────────────────────────────────────────────────
def chat(user_message: str, session_id: str, history: list) -> tuple[str, list]:
    """
    Send a message to the agent and get a response.
    Automatically saves every message to Firestore.
    """

    # Save user message to Firestore
    save_message(session_id, "user", user_message)
    history.append({"role": "user", "content": user_message})

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
                    print(f"  [calling {block.name}({block.input})]")
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

            # Save assistant response to Firestore
            save_message(session_id, "assistant", answer)
            history.append({"role": "assistant", "content": answer})
            return answer, history


# ── Main chat interface ────────────────────────────────────────────────────────
def run():
    # Parse optional --session argument
    session_id = None
    if "--session" in sys.argv:
        idx = sys.argv.index("--session")
        if idx + 1 < len(sys.argv):
            session_id = sys.argv[idx + 1]

    # Generate a new session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())[:8]

    print("\n" + "="*55)
    print("  Trip Planning Agent  (with memory)")
    print(f"  Session ID: {session_id}")
    print("  Type 'history' to see past trips")
    print("  Type 'quit' to exit")
    print("="*55 + "\n")

    # Load existing conversation from Firestore
    history = load_history(session_id)
    if history:
        print(f"  Resuming session — {len(history)} messages loaded from memory.\n")
    else:
        print("  Starting fresh session.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\nSession saved. Resume with: python3 agent.py --session {session_id}")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "bye"):
            print(f"Agent: Safe travels! Resume anytime with: python3 agent.py --session {session_id}")
            break

        if user_input.lower() == "history":
            trips = load_trips(session_id)
            if trips:
                print(f"\n  Your saved trips ({len(trips)}):")
                for t in trips:
                    print(f"  - {t.get('destination', 'Unknown')} on {t.get('dates', 'N/A')}")
            else:
                print("\n  No saved trips yet.")
            print()
            continue

        print()
        answer, history = chat(user_input, session_id, history)
        print(f"Agent: {answer}\n")


if __name__ == "__main__":
    run()
