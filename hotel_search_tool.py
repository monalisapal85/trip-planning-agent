"""
Hotel Search Tool — Serpapi (Google Hotels)
---------------------------------------------
Uses Serpapi to search Google Hotels and return real
hotel options your agent can read and reason over.

No new API key needed — uses the same SERPAPI_API_KEY
you already set up for the flight tool.

Usage:
  python3 hotel_search_tool.py
"""

import os
from serpapi import GoogleSearch
from langchain.tools import tool


# ── Core tool function ─────────────────────────────────────────────────────────

def search_hotels(
    destination: str,
    check_in: str,          # format: "YYYY-MM-DD"
    check_out: str,         # format: "YYYY-MM-DD"
    adults: int = 1,
    max_results: int = 3,
) -> list[dict]:
    """
    Search Google Hotels for real hotel options.

    Args:
        destination: City or area name e.g. "Tokyo"
        check_in:    Check-in date in YYYY-MM-DD format
        check_out:   Check-out date in YYYY-MM-DD format
        adults:      Number of guests
        max_results: How many hotels to return (default 3)

    Returns:
        List of hotel dicts with name, price, rating, and amenities.

    Example:
        >>> hotels = search_hotels("Tokyo", "2026-08-10", "2026-08-13")
        >>> print(hotels[0]["name"])
        'Park Hyatt Tokyo'
    """

    params = {
        "engine":       "google_hotels",
        "q":            destination + " hotels",
        "check_in_date":  check_in,
        "check_out_date": check_out,
        "adults":       adults,
        "currency":     "USD",
        "hl":           "en",
        "gl":           "us",
        "api_key":      os.environ["SERPAPI_API_KEY"],
    }

    try:
        search  = GoogleSearch(params)
        data    = search.get_dict()
        results = data.get("properties", [])[:max_results]

        if not results:
            return [{"error": "No hotels found for this destination and dates."}]

        hotels = []
        for h in results:
            # Price — Serpapi returns rate info nested under "rate_per_night"
            rate       = h.get("rate_per_night", {})
            price      = rate.get("lowest", "N/A")

            # Rating and reviews
            rating     = h.get("overall_rating", "N/A")
            reviews    = h.get("reviews", "N/A")

            # Amenities — top 4 only to keep it concise
            amenities  = h.get("amenities", [])[:4]

            # Hotel class (stars)
            stars      = h.get("hotel_class", "")

            hotels.append({
                "name":       h.get("name", "Unknown"),
                "price":      price,
                "rating":     rating,
                "reviews":    f"{reviews} reviews" if isinstance(reviews, int) else reviews,
                "stars":      stars,
                "amenities":  amenities,
                "link":       h.get("link", ""),
                "thumbnail":  h.get("images", [{}])[0].get("thumbnail", ""),
            })

        return hotels

    except Exception as e:
        return [{"error": str(e)}]


# ── LangChain tool wrapper ─────────────────────────────────────────────────────

@tool
def hotel_search_tool(
    destination: str,
    check_in: str,
    check_out: str,
    adults: int = 1,
) -> str:
    """
    Search for real hotels using Google Hotels data.
    Use this when the user wants to find accommodation for their trip.
    Provide the destination city, check-in and check-out dates in YYYY-MM-DD format.
    Returns up to 3 hotel options with prices, ratings, and amenities.
    """
    hotels = search_hotels(destination, check_in, check_out, adults)

    if not hotels or "error" in hotels[0]:
        return f"No hotels found: {hotels[0].get('error', 'Unknown error')}"

    lines = []
    for i, h in enumerate(hotels, 1):
        amenities = ", ".join(h["amenities"]) if h["amenities"] else "N/A"
        lines.append(
            f"{i}. {h['name']} | {h['price']}/night | "
            f"Rating: {h['rating']} ({h['reviews']}) | "
            f"{h['stars']} | Amenities: {amenities}"
        )
    return "\n".join(lines)


# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Serpapi Google Hotels search...\n")

    results = search_hotels("Tokyo", "2026-08-10", "2026-08-13")
    for h in results:
        print(h)

    print("\nLangChain tool output:")
    print(hotel_search_tool.run({
        "destination": "Tokyo",
        "check_in":    "2026-08-10",
        "check_out":   "2026-08-13",
    }))
