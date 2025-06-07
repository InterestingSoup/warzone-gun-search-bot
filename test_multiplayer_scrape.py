#!/usr/bin/env python3
"""
Test script to verify multiplayer scraping works
"""
import sys
import os
sys.path.append('.')

from scrape import scrape_all_guns

def test_multiplayer_scraping():
    print("🧪 Testing Multiplayer scraping...")
    
    # Test with Assault Rifle category
    mode = "Multiplayer"
    url = "https://wzstats.gg/bo6/meta"
    category = "Assault Rifle"
    selector = "a.menu-item:has-text('Assault Rifle')"
    
    print(f"🔍 Testing: {mode} - {category}")
    print(f"📡 URL: {url}")
    print(f"🎯 Selector: {selector}")
    print()
    
    try:
        guns = scrape_all_guns(mode, url, category, selector)
        
        if guns:
            print(f"✅ Successfully scraped {len(guns)} assault rifles!")
            print("\n📋 Sample results:")
            for i, gun in enumerate(guns[:3], 1):  # Show first 3
                print(f"  {i}. {gun['gun']} (Rank #{gun['rank']})")
                if gun['class']:
                    print(f"     Attachments: {len(gun['class'])} items")
                print()
            
            return True
        else:
            print("❌ No guns found - check selector or URL")
            return False
            
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        return False

if __name__ == "__main__":
    success = test_multiplayer_scraping()
    if success:
        print("🎯 Multiplayer scraping works! Ready to add to main scraper.")
    else:
        print("⚠️ Multiplayer scraping needs debugging.")
        print("💡 Check the website manually to verify selectors.") 