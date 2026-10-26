#!/usr/bin/env python3
"""
MW4 meta scraper (https://wzstats.gg/mw4/meta).

Pure HTTP, no browser: the meta page embeds weapons + tier lists in its Angular
transfer state, and builds come from wzstats' JSON builds endpoint.

Run directly to refresh data/mw4.json:  python -m games.mw4
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

GAME_ID = "mw4"
GAME_NAME = "Modern Warfare 4"
META_URL = "https://wzstats.gg/mw4/meta"
BUILDS_URL = "https://app.wzstats.gg/wz2/weapons/builds/wzstats/with-attachments/weapon/{weapon_id}/"
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mw4.json")

# wzstats build type -> our mode id / display name
MODES = {
    "mw4": {"id": "multiplayer", "name": "Multiplayer"},
    "mw4Resurgence": {"id": "resurgence", "name": "Resurgence"},
    "dmzPvp": {"id": "dmz-pvp", "name": "DMZ PvP"},
    "dmzPve": {"id": "dmz-pve", "name": "DMZ PvE"},
}
TIER_ORDER = ["META", "A", "B", "C", "D"]
ATTACHMENT_SLOTS = ["optic", "muzzle", "barrel", "underbarrel", "laser",
                    "magazine", "ammunition", "rearGrip", "stock", "fireMods"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Origin": "https://wzstats.gg",
    "Referer": "https://wzstats.gg/",
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def fetch_meta_state(session: requests.Session) -> dict:
    """Return the store:weapons-and-tier-lists-mw4 blob from the SSR page."""
    resp = session.get(META_URL, timeout=30)
    resp.raise_for_status()
    match = re.search(r'<script id="ng-state" type="application/json">(.*?)</script>', resp.text, re.S)
    if not match:
        raise RuntimeError("ng-state not found on MW4 meta page (site layout changed?)")
    state = json.loads(match.group(1))
    store = state.get("store:weapons-and-tier-lists-mw4")
    if not store or "weapons" not in store:
        raise RuntimeError("MW4 weapons store missing from ng-state")
    return store


def fetch_builds(session: requests.Session, weapon_id: str) -> list:
    params = [("game", GAME_ID), ("addConversionKit", "true"), ("language", "en"), ("addNewBuilds", "true")]
    params += [("buildTypes[]", t) for t in MODES]
    resp = session.get(BUILDS_URL.format(weapon_id=weapon_id), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("builds", [])


def normalize_build(raw: dict) -> dict:
    attachments = []
    for slot in ATTACHMENT_SLOTS:
        att = raw.get(slot)
        if isinstance(att, dict) and att.get("name"):
            attachments.append(_attachment(slot, att))
    # Pick up any slot not in our list so new slots aren't silently dropped
    for key, att in raw.items():
        if key not in ATTACHMENT_SLOTS and isinstance(att, dict) and att.get("slot") and att.get("name"):
            attachments.append(_attachment(key, att))

    return {
        "id": raw["id"],
        "mode": MODES.get(raw.get("type"), {}).get("id", raw.get("type")),
        "playstyle": (raw.get("playstyle") or "").replace("_", " ").title() or None,
        "title": raw.get("title") or None,
        "description": raw.get("description") or None,
        "is_best_build": any(k.startswith("is") and k.endswith("BestBuild") and v for k, v in raw.items()),
        "is_best_for_playstyle": bool(raw.get("isBestPlaystyleVariant")),
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


def scrape() -> dict:
    session = requests.Session()
    session.headers.update(HEADERS)

    store = fetch_meta_state(session)
    tier_lists_raw = store.get("wzStatsTierList", {})
    raw_weapons = store["weapons"]
    print(f"📊 MW4: {len(raw_weapons)} weapons, tier lists: {list(tier_lists_raw)}")

    with ThreadPoolExecutor(max_workers=6) as pool:
        builds_by_weapon = dict(zip(
            [w["id"] for w in raw_weapons],
            pool.map(lambda w: _safe_builds(session, w["id"]), raw_weapons),
        ))

    # tier + rank per mode, derived from the ordered tier lists
    placement = {}  # (mode_id, weapon_id) -> (tier, rank)
    tier_lists = {}
    for build_type, tiers in tier_lists_raw.items():
        mode_id = MODES.get(build_type, {}).get("id", build_type)
        rank = 0
        ordered = {}
        for tier in TIER_ORDER + [t for t in tiers if t not in TIER_ORDER]:
            ids = tiers.get(tier) or []
            ordered[tier] = ids
            for wid in ids:
                rank += 1
                placement[(mode_id, wid)] = (tier, rank)
        tier_lists[mode_id] = ordered

    weapons = []
    for w in raw_weapons:
        builds = [normalize_build(b) for b in builds_by_weapon.get(w["id"], [])]
        by_mode = {}
        for mode in MODES.values():
            tier, rank = placement.get((mode["id"], w["id"]), (None, None))
            by_mode[mode["id"]] = {"tier": tier, "rank": rank}
        weapons.append({
            "id": w["id"],
            "name": w["name"],
            "type": w["type"]["fullName"],
            "type_id": slug(w["type"]["fullName"]),
            "category": w.get("category"),
            "category_id": slug(w.get("category") or "other"),
            "is_new": bool(w.get("isNew")),
            "unlock_player_level": w.get("unlockedAtPlayerLevel"),
            "by_mode": by_mode,
            "builds": builds,
            "updated_at": w.get("mostRecentUpdatedAt"),
        })

    return {
        "game": GAME_ID,
        "name": GAME_NAME,
        "source": META_URL,
        "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modes": list(MODES.values()),
        "tiers": TIER_ORDER,
        "tier_lists": tier_lists,
        "weapons": weapons,
    }


def _safe_builds(session, weapon_id):
    try:
        return fetch_builds(session, weapon_id)
    except Exception as e:
        print(f"  ⚠️ builds failed for {weapon_id}: {e}")
        return []


def save(data: dict, path: str = DATA_FILE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def main():
    data = scrape()
    builds = sum(len(w["builds"]) for w in data["weapons"])
    if not data["weapons"]:
        print("❌ No weapons scraped, keeping previous data")
        sys.exit(1)
    save(data)
    print(f"💾 Saved {len(data['weapons'])} weapons / {builds} builds to {DATA_FILE}")


if __name__ == "__main__":
    main()
