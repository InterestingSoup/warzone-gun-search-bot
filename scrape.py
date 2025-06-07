#!/usr/bin/env python3
import os
import json
import re
from datetime import datetime
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# === Load Environment ===
load_dotenv()
ALL_GUNS_STORE = "all_guns_database.json"

# === Test Mode ===
TEST_MODE = False  # Set to False to scrape all categories
TEST_CATEGORY = {
    "mode": "Resurgence",
    "url": "https://wzstats.gg/warzone/meta/resurgence",
    "range": "Long Range",
    "selector": None
}

# === Config ===
MODES = {
    "Resurgence": "https://wzstats.gg/warzone/meta/resurgence",
    "Verdansk": "https://wzstats.gg/",
    "Multiplayer": "https://wzstats.gg/bo6/meta"  # Black Ops 6 multiplayer meta
}

# Warzone categories (range-based)
WARZONE_RANGES = {
    "Long Range": None,  # Default tab
    "Close Range": "a.menu-item:has-text('Close range')",
    "Sniper": "a.menu-item:has-text('Sniper')"
}

# Multiplayer categories (weapon-type based)
MULTIPLAYER_WEAPONS = {
    "Assault Rifle": "a.menu-item:has-text('Assault Rifle')",
    "SMG": "a.menu-item:has-text('SMG')",
    "Shotgun": "a.menu-item:has-text('Shotgun')",
    "LMG": "a.menu-item:has-text('LMG')",
    "Marksman Rifle": "a.menu-item:has-text('Marksman Rifle')",
    "Sniper": "a.menu-item:has-text('Sniper')",
    "Pistol": "a.menu-item:has-text('Pistol')"
}

# Image upload functions removed - will be replaced with Azure Storage Blob later

def scrape_all_guns(mode: str, url: str, range_label: str, selector: str):
    """Scrape ALL guns in a category"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("app-weapon-loadouts")
        page.wait_for_timeout(3000)

        if selector:
            page.locator(selector).first.click(force=True)
            page.wait_for_timeout(2000)

        # Get ALL gun containers
        gun_containers = page.query_selector_all("div.loadout-container")
        print(f"📊 Found {len(gun_containers)} guns in {mode} - {range_label}")
        
        all_guns = []
        
        for i, gun in enumerate(gun_containers):
            try:
                gun.scroll_into_view_if_needed()
                gun.click()
                page.wait_for_timeout(500)

                name_el = gun.query_selector("h3.loadout-content-name")
                gun_name = name_el.inner_text().strip() if name_el else f"Unknown Weapon {i+1}"

                class_block = gun.query_selector("div.loadout-detail")
                raw_lines = class_block.inner_text().strip().splitlines() if class_block else []

                class_lines = [
                    line for line in raw_lines
                    if not any(x in line.upper() for x in ["LEVEL", "CREATED ON", "UPDATED ON", "LOADOUTS"])
                ]

                date_line = next((line for line in raw_lines if "Created on" in line or "Updated on" in line), None)
                if date_line:
                    match = re.search(r"(Created|Updated) on[ -]+(.+)", date_line)
                    clean_date = match.group(2).strip() if match else date_line.split("on")[-1].strip()
                else:
                    fallback = class_lines[-1] if class_lines else ""
                    clean_date = fallback if re.search(r"\d{4}", fallback) else "Unknown"

                formatted_lines = []
                j = 0
                while j < len(class_lines):
                    name = class_lines[j]
                    if j + 1 < len(class_lines):
                        attachment_type = class_lines[j + 1]
                        formatted_lines.append(f"• {name} — {attachment_type}")
                        j += 2
                    else:
                        formatted_lines.append(f"• {name}")
                        j += 1

                image_container = gun.query_selector("div.weapon-image-rank-container img")
                gun_image = image_container.get_attribute("src") if image_container else None
                # Note: Original image URL stored for potential Azure Storage upload later

                gun_data = {
                    "rank": i + 1,
                    "mode": mode,
                    "range": range_label,
                    "gun": gun_name,
                    "class": formatted_lines,
                    "image": gun_image,
                    "updated": clean_date,
                }
                
                all_guns.append(gun_data)
                print(f"  ✅ {i+1}. {gun_name}")
                
            except Exception as e:
                print(f"  ⚠️ Error scraping gun {i+1}: {e}")
                continue

        browser.close()
        return all_guns

def save_all_guns_database(all_guns_data):
    """Save comprehensive database of all guns"""
    database = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_guns": sum(len(guns) for guns in all_guns_data.values()),
        "categories": all_guns_data
    }
    
    with open(ALL_GUNS_STORE, "w") as f:
        json.dump(database, f, indent=2)
    
    print(f"💾 Saved {database['total_guns']} guns to {ALL_GUNS_STORE}")

def load_all_guns_database():
    """Load the comprehensive guns database"""
    if os.path.exists(ALL_GUNS_STORE):
        try:
            with open(ALL_GUNS_STORE, "r") as f:
                return json.loads(f.read())
        except Exception as e:
            print(f"⚠️ Could not load all guns database: {e}")
    return {"categories": {}, "total_guns": 0}

if __name__ == "__main__":
    print("🚀 Starting gun database scraper...")
    
    all_guns_database = {}
    total_guns = 0
    
    if TEST_MODE:
        print("🧪 Running in TEST MODE - only scraping one category")
        mode = TEST_CATEGORY["mode"]
        url = TEST_CATEGORY["url"]
        category_label = TEST_CATEGORY["range"]
        selector = TEST_CATEGORY["selector"]
        
        category_key = f"{mode}_{category_label}"
        print(f"🔍 Scraping ALL guns in {mode} [{category_label}]...")
        
        try:
            all_guns = scrape_all_guns(mode, url, category_label, selector)
            all_guns_database[category_key] = all_guns
            total_guns += len(all_guns)
            print(f"✅ Successfully scraped {len(all_guns)} guns from {category_key}")
        except Exception as e:
            print(f"❌ Error scraping {category_key}: {e}")
            all_guns_database[category_key] = []
    else:
        print("🚀 Running in FULL MODE - scraping all categories")
        for mode, url in MODES.items():
            if mode == "Multiplayer":
                # Use weapon types for Multiplayer
                categories = MULTIPLAYER_WEAPONS
            else:
                # Use ranges for Warzone modes (Resurgence/Verdansk)
                categories = WARZONE_RANGES
            
            for category_label, selector in categories.items():
                category_key = f"{mode}_{category_label}"
                print(f"🔍 Scraping ALL guns in {mode} [{category_label}]...")
                
                try:
                    all_guns = scrape_all_guns(mode, url, category_label, selector)
                    all_guns_database[category_key] = all_guns
                    total_guns += len(all_guns)
                    print(f"✅ Successfully scraped {len(all_guns)} guns from {category_key}")
                except Exception as e:
                    print(f"❌ Error scraping {category_key}: {e}")
                    all_guns_database[category_key] = []

    # Save comprehensive database
    save_all_guns_database(all_guns_database)
    
    print(f"\n📊 SCRAPING COMPLETE!")
    print(f"🎯 Total weapons scraped: {total_guns}")
    print(f"💾 Database saved to: {ALL_GUNS_STORE}")
    print(f"🤖 Run Discord search bot with: python discord_search_bot.py")
    
    # Print summary
    print(f"\n📈 CATEGORY BREAKDOWN:")
    for category, guns in all_guns_database.items():
        cat_name = category.replace("_", " - ")
        print(f"  {cat_name}: {len(guns)} weapons")
