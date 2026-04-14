"""
Flight Search Tool — Serpapi (Google Flights)
-----------------------------------------------
Uses Serpapi to search Google Flights and return real
flight options your agent can read and reason over.

Setup:
  1. Sign up free at https://serpapi.com
  2. Copy your API key from the dashboard
  3. pip3 install google-search-results langchain
  4. export SERPAPI_API_KEY="your_key_here"
"""

import os
from serpapi import GoogleSearch
from langchain.tools import tool


# ── Core tool function ─────────────────────────────────────────────────────────

def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = None,
    adults: int = 1,
    max_results: int = 3,
) -> list[dict]:
    """
    Search Google Flights for real flight options.

    Args:
        origin:         IATA code e.g. "ATL"
        destination:    IATA code e.g. "NRT"
        departure_date: Date string in YYYY-MM-DD format
        return_date:    Optional return date for round trips
        adults:         Number of passengers
        max_results:    How many options to return (default 3)
    """

    params = {
        "engine":        "google_flights",
        "departure_id":  origin,
        "arrival_id":    destination,
        "outbound_date": departure_date,
        "adults":        adults,
        "currency":      "USD",
        "hl":            "en",
        "api_key":       os.environ["SERPAPI_API_KEY"],
        "type":          "1" if return_date else "2",
    }

    if return_date:
        params["return_date"] = return_date

    try:
        search      = GoogleSearch(params)
        data        = search.get_dict()
        best        = data.get("best_flights", [])
        other       = data.get("other_flights", [])
        all_options = (best + other)[:max_results]

        flights = []
        for option in all_options:
            legs = option.get("flights", [])
            if not legs:
                continue

            first_leg = legs[0]
            last_leg  = legs[-1]
            stops     = len(legs) - 1

            # Serpapi nests airport info inside departure_airport / arrival_airport
            dep_airport  = first_leg.get("departure_airport", {})
            arr_airport  = last_leg.get("arrival_airport", {})
            carbon       = option.get("carbon_emissions", {})

            flights.append({
                "price":         f"${option.get('price', 'N/A')}",
                "airline":       first_leg.get("airline", "Unknown"),
                "flight_number": first_leg.get("flight_number", ""),
                "departure":     dep_airport.get("name", origin),
                "arrival":       arr_airport.get("name", destination),
                "departs_at":    dep_airport.get("time", ""),
                "arrives_at":    arr_airport.get("time", ""),
                "duration":      _format_duration(option.get("total_duration", 0)),
                "stops":         stops,
                "stops_label":   "Nonstop" if stops == 0 else f"{stops} stop{'s' if stops > 1 else ''}",
                "carbon_kg":     carbon.get("this_flight"),
            })

        return flights if flights else [{"error": "No flights found for this route and date."}]

    except Exception as e:
        return [{"error": str(e)}]


# ── Helper ─────────────────────────────────────────────────────────────────────

def _format_duration(minutes: int) -> str:
    if not minutes:
        return "N/A"
    h, m = divmod(minutes, 60)
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    return " ".join(parts)


# ── LangChain tool wrapper ─────────────────────────────────────────────────────

@tool
def flight_search_tool(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = None,
) -> str:
    """
    Search for real flights using Google Flights data.
    Use this when the user wants to find flights between two cities.
    Provide IATA airport codes and a departure date in YYYY-MM-DD format.
    Optionally provide a return_date for round trips.
    Returns up to 3 real flight options with prices, duration, and stops.
    """
    flights = search_flights(origin, destination, departure_date, return_date)

    if not flights or "error" in flights[0]:
        return f"No flights found: {flights[0].get('error', 'Unknown error')}"

    lines = []
    for i, f in enumerate(flights, 1):
        co2 = f" | CO2 {f['carbon_kg']}kg" if f.get("carbon_kg") else ""
        lines.append(
            f"{i}. {f['airline']} {f['flight_number']} | {f['price']} | "
            f"{f['duration']} | {f['stops_label']} | "
            f"Departs {f['departs_at']} -> Arrives {f['arrives_at']}{co2}"
        )
    return "\n".join(lines)


# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Serpapi Google Flights search...\n")

    results = search_flights("ATL", "NRT", "2026-08-10")
    for f in results:
        print(f)

    print("\nLangChain tool output:")
    print(flight_search_tool.run({
        "origin":         "ATL",
        "destination":    "NRT",
        "departure_date": "2026-08-10",
    }))
