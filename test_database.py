#!/usr/bin/env python3
"""
Simple test script to verify the gun database is working correctly.
Run this after scraping to check your database.
"""
import json
import os

def test_database():
    database_file = "all_guns_database.json"
    
    print("🔍 Testing gun database...")
    
    # Check if database exists
    if not os.path.exists(database_file):
        print("❌ Database not found!")
        print("   Run 'python scrape.py' first to create the database.")
        return False
    
    # Load and check database
    try:
        with open(database_file, 'r') as f:
            db = json.load(f)
    except Exception as e:
        print(f"❌ Error loading database: {e}")
        return False
    
    # Verify structure
    if "total_guns" not in db or "categories" not in db:
        print("❌ Invalid database structure!")
        return False
    
    total_guns = db["total_guns"]
    categories = db["categories"]
    last_updated = db.get("last_updated", "Unknown")
    
    print(f"✅ Database loaded successfully!")
    print(f"📊 Total weapons: {total_guns}")
    print(f"📅 Last updated: {last_updated}")
    print(f"📂 Categories found: {len(categories)}")
    
    # Show breakdown by category
    print("\n📈 Category breakdown:")
    for category, guns in categories.items():
        cat_name = category.replace("_", " - ")
        print(f"   {cat_name}: {len(guns)} weapons")
    
    # Test a few sample searches
    print("\n🔍 Testing sample searches...")
    
    # Find all guns and test fuzzy search
    all_guns = []
    for guns in categories.values():
        all_guns.extend(guns)
    
    if all_guns:
        sample_gun = all_guns[0]["gun"]
        print(f"   Sample gun found: '{sample_gun}'")
        
        # Test partial search
        partial = sample_gun[:3].lower()
        matches = [g for g in all_guns if partial in g["gun"].lower()]
        print(f"   Partial search '{partial}': {len(matches)} matches")
    else:
        print("   ⚠️ No guns found in database!")
    
    print(f"\n🎯 Database test complete!")
    print(f"🤖 Ready to run Discord bot: python discord_search_bot.py")
    
    return True

if __name__ == "__main__":
    test_database() 