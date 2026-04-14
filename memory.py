"""
Memory Module — Firestore Persistent Memory
---------------------------------------------
Saves and loads conversation history and trip plans
to Firestore so your agent remembers across sessions.

Usage:
  from memory import save_message, load_history, save_trip, load_trips
"""

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timezone


# ── Firestore client ───────────────────────────────────────────────────────────
db = firestore.Client(database="tripagent")


# ── Conversation memory ────────────────────────────────────────────────────────

def save_message(session_id: str, role: str, content: str):
    """
    Save a single message to Firestore.

    Args:
        session_id: Unique ID for the conversation e.g. "user_123"
        role:       "user" or "assistant"
        content:    The message text
    """
    db.collection("conversations") \
      .document(session_id) \
      .collection("messages") \
      .add({
          "role":      role,
          "content":   content,
          "timestamp": datetime.now(timezone.utc),
      })


def load_history(session_id: str, limit: int = 20) -> list[dict]:
    """
    Load the last N messages for a session.

    Args:
        session_id: The conversation ID to load
        limit:      Max number of messages to load (default 20)

    Returns:
        List of {"role": ..., "content": ...} dicts
        ready to pass straight into the Anthropic messages list.
    """
    docs = (
        db.collection("conversations")
          .document(session_id)
          .collection("messages")
          .order_by("timestamp")
          .limit_to_last(limit)
          .get()
    )

    history = []
    for doc in docs:
        data = doc.to_dict()
        history.append({
            "role":    data["role"],
            "content": data["content"],
        })
    return history


def clear_history(session_id: str):
    """Delete all messages for a session (start fresh)."""
    msgs = (
        db.collection("conversations")
          .document(session_id)
          .collection("messages")
          .get()
    )
    for doc in msgs:
        doc.reference.delete()
    print(f"Cleared history for session: {session_id}")


# ── Trip plan memory ───────────────────────────────────────────────────────────

def save_trip(session_id: str, trip: dict):
    """
    Save a trip plan to Firestore.

    Args:
        session_id: Links the trip to a conversation
        trip:       Dict with trip details
    """
    trip["saved_at"]   = datetime.now(timezone.utc)
    trip["session_id"] = session_id
    db.collection("trips").add(trip)
    print(f"Trip to {trip.get('destination', 'unknown')} saved.")


def load_trips(session_id: str) -> list[dict]:
    """
    Load all saved trips for a session, most recent first.
    """
    docs = (
        db.collection("trips")
          .where(filter=FieldFilter("session_id", "==", session_id))
          .order_by("saved_at", direction=firestore.Query.DESCENDING)
          .get()
    )

    trips = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        trips.append(data)
    return trips
