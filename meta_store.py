#!/usr/bin/env python3
"""
Game-agnostic query layer over every scraped meta dataset.

Each game is loaded into the same shape so an AI (or the Discord bot) can drill
down step by step:  game -> mode -> category / weapon type -> weapon -> build.

Games (data/<game>.json, scraped by games/wzstats.py): mw4, warzone, bo6, bo7.
warzone / bo6 fall back to the legacy all_guns_database.json (scrape.py) if
their data file is missing.

Adding a wzstats game = add it to games.wzstats.GAMES. Other sources: write a
loader that returns a Game and register it in LOADERS.
"""
import difflib
import json
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LEGACY_FILE = os.path.join(BASE_DIR, "all_guns_database.json")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


@dataclass
class Game:
    id: str
    name: str
    source: str
    updated: Optional[str]
    modes: list                      # [{id, name}]
    weapons: dict                    # weapon_id -> weapon dict (includes builds)
    # Ordered placements: one row per (mode, weapon[, category]) in rank order
    rows: list = field(default_factory=list)
    tiers: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def categories(self, mode=None):
        seen = {}
        for r in self.rows:
            if mode is None or r["mode"] == mode:
                seen.setdefault(r["category_id"], r["category"])
        return [{"id": k, "name": v} for k, v in seen.items()]

    def weapon_types(self):
        seen = {}
        for w in self.weapons.values():
            seen.setdefault(w["type_id"], w["type"])
        return [{"id": k, "name": v} for k, v in seen.items() if k]


# ---------------------------------------------------------------- loaders

GAME_NOTES = {
    "mw4": ["MW4 has two modes: Multiplayer and DMZ (split into DMZ PvP and DMZ PvE tier lists).",
            "DMZ PvE has tier placements but few/no published builds; meta falls back to the "
            "weapon's DMZ PvP or Multiplayer build (see build_from_mode)."],
    "warzone": ["Builds are shared across Warzone modes; best_for_modes says which mode each is tuned for."],
}


def load_wzstats(game_id: str) -> Optional[Game]:
    path = os.path.join(DATA_DIR, f"{game_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)

    weapons = {w["id"]: w for w in data["weapons"]}
    rows = []
    for mode in data["modes"]:
        placed = [w for w in data["weapons"] if w["by_mode"].get(mode["id"], {}).get("rank")]
        placed.sort(key=lambda w: w["by_mode"][mode["id"]]["rank"])
        for w in placed:
            p = w["by_mode"][mode["id"]]
            rows.append({
                "mode": mode["id"], "weapon_id": w["id"],
                "category": w["category"], "category_id": w["category_id"],
                "tier": p["tier"], "rank": p["rank"],
            })
    return Game(
        id=game_id, name=data["name"], source=data["source"], updated=data["scraped_at"],
        modes=data["modes"], weapons=weapons, rows=rows, tiers=data["tiers"],
        notes=["Tier lists rank every weapon per mode; categories are Long range / Close range / Sniper."]
              + GAME_NOTES.get(game_id, []),
    )


_LEGACY_GAMES = {
    "warzone": {"name": "Warzone (BO6 era)", "modes": ["Resurgence", "Verdansk"],
                "source": "https://wzstats.gg/warzone/meta"},
    "bo6": {"name": "Black Ops 6", "modes": ["Multiplayer"], "source": "https://wzstats.gg/bo6/meta"},
}


def load_legacy(game_id: str) -> Optional[Game]:
    if not os.path.exists(LEGACY_FILE):
        return None
    with open(LEGACY_FILE) as f:
        data = json.load(f)
    cfg = _LEGACY_GAMES[game_id]

    weapons, rows = {}, []
    for key, guns in data.get("categories", {}).items():
        mode_name, _, category = key.partition("_")
        if mode_name not in cfg["modes"]:
            continue
        mode_id = slug(mode_name)
        for g in guns:
            name = g["gun"].split("\n")[0].strip()
            attachments = _legacy_attachments(g.get("class", []))
            if not attachments:
                continue  # broken scrape rows with no loadout
            wid = slug(name)
            w = weapons.setdefault(wid, {
                "id": wid, "name": name,
                # BO6 categories are weapon types; Warzone categories are ranges
                "type": category if game_id == "bo6" else None,
                "type_id": slug(category) if game_id == "bo6" else None,
                "category": None if game_id == "bo6" else category,
                "category_id": None if game_id == "bo6" else slug(category),
                "is_new": "NEW" in g["gun"], "builds": [],
            })
            w["builds"].append({
                "id": f"{wid}-{mode_id}-{slug(category)}",
                "modes": [mode_id], "best_for_modes": [mode_id], "playstyle": category,
                "attachments": attachments,
                "updated_at": g.get("updated") or None, "image": g.get("image"),
            })
            rows.append({
                "mode": mode_id, "weapon_id": wid, "category": category,
                "category_id": slug(category), "tier": None, "rank": g.get("rank"),
            })
    if not weapons:
        return None
    return Game(
        id=game_id, name=cfg["name"], source=cfg["source"], updated=data.get("last_updated"),
        modes=[{"id": slug(m), "name": m} for m in cfg["modes"]], weapons=weapons, rows=rows,
        notes=["Legacy scrape: ranks only (no tiers); one build per weapon per category."],
    )


def _legacy_attachments(lines):
    out = []
    for line in lines:
        text = line.lstrip("• ").strip()
        name, sep, slot = text.partition(" — ")
        if not sep or re.search(r"\d{4}|Season", text):
            continue
        out.append({"slot": slot.strip().lower().replace(" ", "_"), "name": name.strip()})
    return out


LOADERS = {
    "mw4": lambda: load_wzstats("mw4"),
    "warzone": lambda: load_wzstats("warzone") or load_legacy("warzone"),
    "bo6": lambda: load_wzstats("bo6") or load_legacy("bo6"),
    "bo7": lambda: load_wzstats("bo7"),
}


# ---------------------------------------------------------------- store

class MetaStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._games = {}
        self._mtimes = {}
        self.reload()

    def reload(self):
        games = {}
        for gid, loader in LOADERS.items():
            try:
                g = loader()
            except Exception as e:
                print(f"⚠️ Failed to load {gid}: {e}")
                g = self._games.get(gid)  # keep last good copy
            if g:
                games[gid] = g
        with self._lock:
            self._games = games
            self._mtimes = self._current_mtimes()

    def _current_mtimes(self):
        paths = [LEGACY_FILE] + [os.path.join(DATA_DIR, f"{gid}.json") for gid in LOADERS]
        return {p: os.path.getmtime(p) for p in paths if os.path.exists(p)}

    def _maybe_reload(self):
        if self._current_mtimes() != self._mtimes:
            self.reload()

    def game(self, game_id: str) -> Game:
        self._maybe_reload()
        g = self._games.get((game_id or "").lower())
        if not g:
            raise LookupError(f"Unknown game '{game_id}'. Available: {', '.join(self._games)}")
        return g

    # ---- resolvers (accept ids or loose names) ----

    ALIASES = {"br": "battleroyale", "wz": "battleroyale", "mp": "multiplayer", "rez": "resurgence",
               "ranked": "ranked", "dmz": "dmzpvp", "pvp": "dmzpvp", "pve": "dmzpve", "ar": "assaultrifle", "lmg": "lmg", "sr": "sniper",
               "marksman": "marksmanrifle", "short": "closerange", "shortrange": "closerange"}

    def _resolve(self, value, options, kind):
        if value is None:
            return None
        key = norm(value)
        key = self.ALIASES.get(key, key)
        for o in options:
            if key in (norm(o["id"]), norm(o["name"])):
                return o["id"]
        for o in options:
            if key and (key in norm(o["name"]) or norm(o["name"]).startswith(key)):
                return o["id"]
        raise LookupError(f"Unknown {kind} '{value}'. Options: {', '.join(o['id'] for o in options)}")

    def _weapon(self, g: Game, query: str) -> dict:
        key = norm(query)
        if key in {norm(w["id"]) for w in g.weapons.values()}:
            return next(w for w in g.weapons.values() if norm(w["id"]) == key)
        exact = [w for w in g.weapons.values() if norm(w["name"]) == key]
        if exact:
            return exact[0]
        partial = [w for w in g.weapons.values() if key in norm(w["name"])]
        if len(partial) == 1:
            return partial[0]
        if len(partial) > 1:
            raise LookupError(f"'{query}' is ambiguous: {', '.join(w['name'] for w in partial)}")
        close = difflib.get_close_matches(key, {norm(w["name"]): w for w in g.weapons.values()}, n=3, cutoff=0.6)
        names = [w["name"] for w in g.weapons.values() if norm(w["name"]) in close]
        raise LookupError(f"No weapon '{query}' in {g.id}." + (f" Did you mean: {', '.join(names)}?" if names else ""))

    # ---- public queries ----

    def list_games(self):
        self._maybe_reload()
        return [{
            "id": g.id, "name": g.name, "updated": g.updated, "source": g.source,
            "weapon_count": len(g.weapons), "modes": g.modes,
        } for g in self._games.values()]

    def game_info(self, game_id):
        g = self.game(game_id)
        return {
            "id": g.id, "name": g.name, "updated": g.updated, "source": g.source,
            "modes": [dict(m, categories=g.categories(m["id"])) for m in g.modes],
            "weapon_types": g.weapon_types(), "tiers": g.tiers,
            "weapon_count": len(g.weapons), "notes": g.notes,
        }

    def tier_list(self, game_id, mode=None, category=None, weapon_type=None, tier=None):
        g = self.game(game_id)
        mode = self._resolve(mode, g.modes, "mode") or g.modes[0]["id"]
        category = self._resolve(category, g.categories(mode), "category")
        weapon_type = self._resolve(weapon_type, g.weapon_types(), "weapon type")
        out = []
        for r in g.rows:
            if r["mode"] != mode or (category and r["category_id"] != category):
                continue
            w = g.weapons[r["weapon_id"]]
            if weapon_type and w.get("type_id") != weapon_type:
                continue
            if tier and (r["tier"] or "").upper() != tier.upper():
                continue
            out.append({
                "rank": r["rank"], "tier": r["tier"], "weapon_id": w["id"], "name": w["name"],
                "type": w.get("type"), "category": r["category"],
                "build_count": sum(1 for b in w["builds"] if mode in b["modes"]),
            })
        return {"game": g.id, "mode": mode, "category": category, "weapon_type": weapon_type, "weapons": out}

    def meta(self, game_id, mode=None, category=None, weapon_type=None, limit=5):
        """Top weapons for a mode with their recommended build ('give me the meta class')."""
        tl = self.tier_list(game_id, mode, category, weapon_type)
        g = self.game(game_id)
        picks = []
        for row in tl["weapons"]:
            w = g.weapons[row["weapon_id"]]
            build, fallback = _best_build(w, tl["mode"], None if g.tiers else row["category"])
            if not build:
                continue
            picks.append(dict(row, build=build, build_from_mode=fallback))
            if len(picks) >= int(limit):
                break
        return {k: tl[k] for k in ("game", "mode", "category", "weapon_type")} | {"meta": picks}

    def weapon(self, game_id, name, mode=None):
        g = self.game(game_id)
        w = self._weapon(g, name)
        mode = self._resolve(mode, g.modes, "mode")
        placements = [{"mode": r["mode"], "category": r["category"], "tier": r["tier"], "rank": r["rank"]}
                      for r in g.rows if r["weapon_id"] == w["id"] and (not mode or r["mode"] == mode)]
        builds = [b for b in w["builds"] if not mode or mode in b["modes"]]
        result = {k: v for k, v in w.items() if k not in ("builds", "by_mode")}
        result.update(game=g.id, placements=placements, builds=builds)
        if mode and not builds and w["builds"]:
            result["note"] = f"No {mode} builds published; showing builds from other modes."
            result["builds"] = w["builds"]
        return result

    def search(self, query, game_id=None):
        self._maybe_reload()
        key = norm(query)
        games = [self.game(game_id)] if game_id else list(self._games.values())
        hits = []
        for g in games:
            for w in g.weapons.values():
                n = norm(w["name"])
                score = 1.0 if n == key else 0.9 if key in n else difflib.SequenceMatcher(None, key, n).ratio()
                if score >= 0.6:
                    hits.append({"game": g.id, "weapon_id": w["id"], "name": w["name"],
                                 "type": w.get("type"), "score": round(score, 2)})
        return sorted(hits, key=lambda h: -h["score"])[:20]


def _best_build(weapon, mode, category=None):
    """Return (build, fallback_mode). Prefers this mode's recommended build, then any build."""
    in_mode = [b for b in weapon["builds"] if mode in b["modes"]]
    if category:  # legacy games keep one build per category
        in_cat = [b for b in in_mode if b.get("playstyle") == category]
        in_mode = in_cat or in_mode
    best = next((b for b in in_mode if mode in b["best_for_modes"]), None) or (in_mode[0] if in_mode else None)
    if best:
        return best, None
    # No build for this mode: borrow the weapon's recommended build from another mode
    pool = weapon["builds"]
    best = next((b for b in pool if b["best_for_modes"]), None) or (pool[0] if pool else None)
    return (best, best["modes"][0]) if best else (None, None)


store = MetaStore()
