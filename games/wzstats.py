#!/usr/bin/env python3
"""
wzstats.gg meta scraper for every game it covers (MW4, Warzone, BO6, BO7).

Pure HTTP, no browser: each meta page embeds weapons + tier lists in its Angular
transfer state, and builds come from wzstats' JSON builds endpoint.

Refresh data/<game>.json:  python -m games.wzstats [mw4 warzone bo6 bo7]
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

BUILDS_URL = "https://app.wzstats.gg/wz2/weapons/builds/wzstats/with-attachments/weapon/{weapon_id}/"
# Loadout-builder context: full attachment catalog + recommended attachment sets per playstyle.
# The site uses it to render builds whose stored build has no attachments.
BUILDER_URL = "https://app.wzstats.gg/wz2/loadout-builder/context"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TIER_ORDER = ["META", "A", "B", "C", "D"]
ATTACHMENT_SLOTS = ["optic", "muzzle", "barrel", "underbarrel", "laser", "magazine", "ammunition",
                    "rearGrip", "stock", "fireMods", "apex", "bolt", "comb", "guard", "triggerAction"]

# Per game:
#   store       ng-state key suffix (store:weapons-and-tier-lists-<store>)
#   modes       wzstats tier list key -> our mode (first = default mode)
#   build_types buildTypes[] sent to the builds endpoint, and the mode each type belongs to
#   best_flags  build flag -> mode it marks the build as recommended for
GAMES = {
    "mw4": {
        "name": "Modern Warfare 4",
        "url": "https://wzstats.gg/mw4/meta",
        "store": "mw4",
        "modes": {
            "mw4": {"id": "multiplayer", "name": "Multiplayer"},
            "dmzPvp": {"id": "dmz-pvp", "name": "DMZ PvP"},
            "dmzPve": {"id": "dmz-pve", "name": "DMZ PvE"},
        },
        "build_types": {"mw4": "multiplayer", "dmzPvp": "dmz-pvp", "dmzPve": "dmz-pve"},
        "best_flags": {"isMW4BestBuild": "multiplayer", "isDMZPvpBestBuild": "dmz-pvp", "isDMZPveBestBuild": "dmz-pve"},
    },
    "warzone": {
        "name": "Warzone",
        "url": "https://wzstats.gg/",
        "store": "wz2",
        # wzstats reuses old map keys: alMazrah = Battle Royale, ashikaIsland = Resurgence
        "modes": {
            "alMazrah": {"id": "battle-royale", "name": "Battle Royale"},
            "ashikaIsland": {"id": "resurgence", "name": "Resurgence"},
            "wz2Ranked": {"id": "ranked", "name": "Ranked Play"},
            "rankedResurgence": {"id": "ranked-resurgence", "name": "Ranked Resurgence"},
            "ironGauntlet": {"id": "iron-gauntlet", "name": "Iron Gauntlet"},
            "blackOpsRoyale": {"id": "black-ops-royale", "name": "Black Ops Royale"},
        },
        "build_types": {"wz2": "battle-royale"},
        "best_flags": {"isBestBuild": "battle-royale", "isAshikaBuild": "resurgence",
                       "isWarzoneRankedBuild": "ranked", "isResurgenceRankedBestBuild": "ranked-resurgence"},
    },
    "bo6": {
        "name": "Black Ops 6",
        "url": "https://wzstats.gg/bo6/meta",
        "store": "bo6",
        "modes": {
            "bo6": {"id": "multiplayer", "name": "Multiplayer"},
            "bo6Ranked": {"id": "ranked", "name": "Ranked Play"},
        },
        "build_types": {"bo6": "multiplayer", "bo6Ranked": "ranked"},
        "best_flags": {"isBO6BestBuild": "multiplayer", "isBO6RankedBestBuild": "ranked"},
    },
    "bo7": {
        "name": "Black Ops 7",
        "url": "https://wzstats.gg/bo7/meta",
        "store": "bo7",
        "modes": {
            "bo7": {"id": "multiplayer", "name": "Multiplayer"},
            "bo7Ranked": {"id": "ranked", "name": "Ranked Play"},
        },
        "build_types": {"bo7": "multiplayer", "bo7Ranked": "ranked"},
        "best_flags": {"isBO7BestBuild": "multiplayer", "isBO7RankedBestBuild": "ranked"},
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Origin": "https://wzstats.gg",
    "Referer": "https://wzstats.gg/",
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def data_file(game_id: str) -> str:
    return os.path.join(DATA_DIR, f"{game_id}.json")


def fetch_store(session: requests.Session, cfg: dict) -> dict:
    """Return the store:weapons-and-tier-lists-<store> blob from the SSR page."""
    resp = session.get(cfg["url"], timeout=30)
    resp.raise_for_status()
    match = re.search(r'<script id="ng-state" type="application/json">(.*?)</script>', resp.text, re.S)
    if not match:
        raise RuntimeError(f"ng-state not found on {cfg['url']} (site layout changed?)")
    store = json.loads(match.group(1)).get(f"store:weapons-and-tier-lists-{cfg['store']}")
    if not store or "weapons" not in store:
        raise RuntimeError(f"{cfg['store']} weapons store missing from ng-state")
    return store


def fetch_builds(session: requests.Session, cfg: dict, weapon_id: str) -> list:
    params = [("game", cfg["store"]), ("addConversionKit", "true"), ("language", "en"), ("addNewBuilds", "true")]
    params += [("buildTypes[]", t) for t in cfg["build_types"]]
    resp = session.get(BUILDS_URL.format(weapon_id=weapon_id), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("builds", [])


def fetch_recommended(session: requests.Session, cfg: dict, weapon_id: str) -> list:
    """Return recommended attachments [{slot, name, ...}] from the loadout builder, or []."""
    params = {"weaponId": weapon_id, "tierlist": next(iter(cfg["modes"])), "game": cfg["store"],
              "addAttachmentsLockedByDefault": "true"}
    resp = session.get(BUILDER_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data") or {}
    catalog = {}
    for a in data.get("attachments", []):
        catalog[a["id"]] = a
        catalog.setdefault(a.get("attachmentId"), a)
    mods = [m for m in data.get("modifiers", []) if m.get("status") == "published" and m.get("bestAttachmentIds")]
    best = next((m for m in mods if m.get("isBestPlaystyleForTierList")), mods[0] if mods else None)
    if not best:
        return []
    out = []
    for att_id in best["bestAttachmentIds"]:
        a = catalog.get(att_id)
        if a:
            out.append({"slot": a.get("slot"), "name": a.get("name") or a.get("attachmentName"),
                        "unlock_weapon_level": a.get("unlockedAtWeaponLevel")})
    return out


def normalize_build(raw: dict, cfg: dict) -> dict:
    attachments = []
    for slot in ATTACHMENT_SLOTS:
        att = raw.get(slot)
        if isinstance(att, dict) and att.get("name"):
            attachments.append(_attachment(slot, att))
    # Pick up any slot not in our list so new slots aren't silently dropped
    for key, att in raw.items():
        if key not in ATTACHMENT_SLOTS and isinstance(att, dict) and att.get("slot") and att.get("name"):
            attachments.append(_attachment(key, att))

    type_mode = cfg["build_types"].get(raw.get("type"), raw.get("type"))
    best_for = [m for flag, m in cfg["best_flags"].items() if raw.get(flag)]
    modes = list(dict.fromkeys([type_mode] + best_for))

    return {
        "id": raw["id"],
        "modes": modes,                # modes this build is meant for
        "best_for_modes": best_for,    # modes where wzstats marks it the recommended build
        "playstyle": (raw.get("playstyle") or "").replace("_", " ").title() or None,
        "title": raw.get("title") or None,
        "description": raw.get("description") or None,
        "attachments": attachments,
        "pros": raw.get("pros") or [],
        "cons": raw.get("cons") or [],
        "author": raw.get("authorDisplayName"),
        "updated_at": raw.get("updatedAt"),
    }


def _attachment(slot: str, att: dict) -> dict:
    out = {"slot": slot, "name": att["name"], "unlock_weapon_level": att.get("unlockedAtWeaponLevel")}
    if att.get("verticalTuning") or att.get("horizontalTuning"):
        out["tuning"] = {"vertical": att.get("verticalTuning"), "horizontal": att.get("horizontalTuning")}
    if att.get("dmzCost") is not None:
        out["dmz_cost"] = att["dmzCost"]
    return out


def scrape(game_id: str) -> dict:
    cfg = GAMES[game_id]
    session = requests.Session()
    session.headers.update(HEADERS)

    store = fetch_store(session, cfg)
    tier_lists_raw = store.get("wzStatsTierList", {})

    # tier + rank per mode, derived from the ordered tier lists
    placement = {}  # (mode_id, weapon_id) -> (tier, rank)
    tier_lists = {}
    for key, mode in cfg["modes"].items():
        tiers = tier_lists_raw.get(key)
        if not isinstance(tiers, dict):
            continue
        rank = 0
        ordered = {}
        for tier in TIER_ORDER + [t for t in tiers if t not in TIER_ORDER]:
            ids = tiers.get(tier) or []
            ordered[tier] = ids
            for wid in ids:
                rank += 1
                placement[(mode["id"], wid)] = (tier, rank)
        tier_lists[mode["id"]] = ordered

    # Warzone's store holds weapons from several games; keep the ones it ranks
    placed_ids = {wid for _, wid in placement}
    raw_weapons = [w for w in store["weapons"] if w["id"] in placed_ids]
    print(f"📊 {game_id}: {len(raw_weapons)} weapons, modes: {list(tier_lists)}")

    with ThreadPoolExecutor(max_workers=6) as pool:
        builds_by_weapon = dict(zip(
            [w["id"] for w in raw_weapons],
            pool.map(lambda w: _safe_builds(session, cfg, w["id"]), raw_weapons),
        ))

    weapons = []
    for w in raw_weapons:
        builds = [normalize_build(b, cfg) for b in builds_by_weapon.get(w["id"], [])]
        if any(not b["attachments"] for b in builds):
            recommended = _safe_recommended(session, cfg, w["id"])
            for b in builds:
                if not b["attachments"] and recommended:
                    b["attachments"] = recommended
                    b["attachments_source"] = "loadout-builder recommended"
        by_mode = {}
        for mode in cfg["modes"].values():
            tier, rank = placement.get((mode["id"], w["id"]), (None, None))
            by_mode[mode["id"]] = {"tier": tier, "rank": rank}
        wtype = (w.get("type") or {}).get("fullName") or ""
        weapons.append({
            "id": w["id"],
            "name": w["name"],
            "type": wtype or None,
            "type_id": slug(wtype) or None,
            "category": w.get("category"),
            "category_id": slug(w.get("category") or "other"),
            "origin_game": w.get("game"),
            "is_new": bool(w.get("isNew")),
            "unlock_player_level": w.get("unlockedAtPlayerLevel"),
            "by_mode": by_mode,
            "builds": builds,
            "updated_at": w.get("mostRecentUpdatedAt"),
        })

    return {
        "game": game_id,
        "name": cfg["name"],
        "source": cfg["url"],
        "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modes": [m for m in cfg["modes"].values() if m["id"] in tier_lists],
        "tiers": TIER_ORDER,
        "tier_lists": tier_lists,
        "weapons": weapons,
    }


def _safe_builds(session, cfg, weapon_id):
    try:
        return fetch_builds(session, cfg, weapon_id)
    except Exception as e:
        print(f"  ⚠️ builds failed for {weapon_id}: {e}")
        return []


def _safe_recommended(session, cfg, weapon_id):
    try:
        return fetch_recommended(session, cfg, weapon_id)
    except Exception as e:
        print(f"  ⚠️ loadout builder failed for {weapon_id}: {e}")
        return []


def save(data: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def refresh(game_ids=None) -> list:
    """Scrape and save each game; a failing game keeps its previous file. Returns failures."""
    failed = []
    for game_id in game_ids or GAMES:
        try:
            data = scrape(game_id)
            if not data["weapons"]:
                raise RuntimeError("no weapons scraped")
            save(data, data_file(game_id))
            builds = sum(len(w["builds"]) for w in data["weapons"])
            print(f"💾 {game_id}: saved {len(data['weapons'])} weapons / {builds} builds")
        except Exception as e:
            print(f"❌ {game_id}: {e} (keeping previous data)")
            failed.append(game_id)
    return failed


if __name__ == "__main__":
    sys.exit(1 if refresh(sys.argv[1:] or None) else 0)
