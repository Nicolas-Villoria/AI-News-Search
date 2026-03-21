import requests
import streamlit as st
from datetime import datetime, timezone
from dateutil import parser as dateutil_parser

API_URL = "http://127.0.0.1:8000"



def api_get(endpoint: str) -> dict | None:
    try:
        r = requests.get(f"{API_URL}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server. Start it with: `python -m uvicorn api.main:app --port 8000`")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(endpoint: str, data: dict, timeout: int = 30) -> dict | None:
    try:
        r = requests.post(f"{API_URL}{endpoint}", json=data, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server. Start it with: `python -m uvicorn api.main:app --port 8000`")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def format_time_ago(published: str | None) -> str:
    if not published:
        return "Unknown date"
    try:
        dt = dateutil_parser.parse(published)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        hours = delta.total_seconds() / 3600
        if hours < 1:
            return f"{int(delta.total_seconds() / 60)}m ago"
        if hours < 24:
            return f"{int(hours)}h ago"
        return f"{int(hours / 24)}d ago"
    except Exception:
        return published