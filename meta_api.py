#!/usr/bin/env python3
"""
JSON query API over meta_store, meant to be called as tools by an AI.

  GET /api                                     endpoint index + how to drill down
  GET /api/games                               games with modes
  GET /api/games/{game}                        modes, categories, weapon types, tiers
  GET /api/games/{game}/tier-list?mode=&category=&type=&tier=
  GET /api/games/{game}/meta?mode=&category=&type=&limit=5   top weapons + best build
  GET /api/games/{game}/weapons/{name}?mode=   one weapon, all builds/placements
  GET /api/search?q=&game=                     fuzzy weapon search across games

Serve standalone:  python meta_api.py   (PORT, default 10000)
start.py mounts the same handler next to /health.
"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from meta_store import store

REFRESH_HOURS = float(os.getenv("META_REFRESH_HOURS", os.getenv("MW4_REFRESH_HOURS", "6")))

INDEX = {
    "service": "game meta query API",
    "how_to_use": [
        "1. GET /api/games to see which games exist (mw4, warzone, bo6, bo7).",
        "2. GET /api/games/{game} to get its modes, categories and weapon types. "
        "If the user didn't say which mode/category they want, ask them using these options.",
        "3. GET /api/games/{game}/meta?mode=...&category=... for the meta class (top weapons with best build).",
        "4. GET /api/games/{game}/weapons/{name}?mode=... for every build of a specific gun.",
        "Mode/category/type params accept ids or loose names ('dmz pvp', 'long range', 'smg').",
    ],
    "endpoints": {
        "/api/games": "list games",
        "/api/games/{game}": "modes, categories, weapon types, tiers, notes",
        "/api/games/{game}/tier-list": "ordered weapons; params: mode, category, type, tier",
        "/api/games/{game}/meta": "top weapons + recommended build; params: mode, category, type, limit",
        "/api/games/{game}/weapons/{name}": "weapon detail + builds; params: mode",
        "/api/search": "fuzzy weapon search; params: q (required), game",
    },
}


def handle(path: str, query: str):
    """Return (status, payload) for an /api path."""
    params = {k: v[-1] for k, v in parse_qs(query).items()}
    parts = [unquote(p) for p in path.strip("/").split("/")][1:]  # drop "api"
    try:
        if not parts:
            return 200, INDEX
        if parts == ["games"]:
            return 200, {"games": store.list_games()}
        if parts == ["search"]:
            if not params.get("q"):
                return 400, {"error": "q is required"}
            return 200, {"results": store.search(params["q"], params.get("game"))}
        if parts[0] == "games" and len(parts) >= 2:
            game = parts[1]
            if len(parts) == 2:
                return 200, store.game_info(game)
            if parts[2] == "tier-list" and len(parts) == 3:
                return 200, store.tier_list(game, params.get("mode"), params.get("category"),
                                            params.get("type"), params.get("tier"))
            if parts[2] == "meta" and len(parts) == 3:
                return 200, store.meta(game, params.get("mode"), params.get("category"),
                                       params.get("type"), params.get("limit", 5))
            if parts[2] == "weapons" and len(parts) == 4:
                return 200, store.weapon(game, parts[3], params.get("mode"))
        return 404, {"error": f"No route for {path}", "see": "/api"}
    except LookupError as e:
        return 404, {"error": str(e.args[0])}
    except Exception as e:
        return 500, {"error": f"{type(e).__name__}: {e}"}


def write_json(handler: BaseHTTPRequestHandler, status: int, payload):
    body = json.dumps(payload, indent=1).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def start_refresher():
    """Re-scrape every wzstats game on an interval (plain HTTP, so it runs in-container)."""
    from games import wzstats

    def loop():
        while True:
            try:
                wzstats.refresh()
                store.reload()
            except Exception as e:
                print(f"⚠️ Meta refresh failed: {e}")
            time.sleep(REFRESH_HOURS * 3600)

    if REFRESH_HOURS > 0:
        threading.Thread(target=loop, daemon=True, name="meta-refresh").start()


class ApiHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/health":
            return write_json(self, 200, {"status": "ok", "games": [g["id"] for g in store.list_games()]})
        if url.path == "/api" or url.path.startswith("/api/"):
            return write_json(self, *handle(url.path, url.query))
        write_json(self, 404, {"error": "not found", "see": "/api"})

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    start_refresher()
    port = int(os.getenv("PORT", 10000))
    print(f"🌐 Meta API on :{port}/api")
    ThreadingHTTPServer(("0.0.0.0", port), ApiHandler).serve_forever()
