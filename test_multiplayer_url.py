#!/usr/bin/env python3
"""
Test script to find the correct multiplayer URL for wzstats.gg
"""
import requests

def test_multiplayer_urls():
    print('🔍 Testing multiplayer URLs...')
    
    # Primary guess based on pattern
    primary_url = 'https://wzstats.gg/warzone/meta/multiplayer'
    
    # Alternative URLs to try
    alternative_urls = [
        'https://wzstats.gg/multiplayer',
        'https://wzstats.gg/warzone/multiplayer',
        'https://wzstats.gg/meta/multiplayer',
        'https://wzstats.gg/warzone/meta/mp',
        'https://wzstats.gg/mp'
    ]
    
    all_urls = [primary_url] + alternative_urls
    
    for url in all_urls:
        try:
            print(f'Testing: {url}')
            response = requests.get(url, timeout=10)
            print(f'  Status: {response.status_code}')
            
            if response.status_code == 200:
                print(f'✅ Found working URL: {url}')
                
                # Check if it contains weapon loadouts
                if 'app-weapon-loadouts' in response.text or 'loadout' in response.text.lower():
                    print(f'✅ URL contains weapon loadouts!')
                    return url
                else:
                    print(f'⚠️ URL exists but may not contain weapon loadouts')
            elif response.status_code == 404:
                print(f'❌ URL not found (404)')
            else:
                print(f'⚠️ Unexpected status code: {response.status_code}')
                
        except requests.exceptions.Timeout:
            print(f'⏰ Timeout connecting to {url}')
        except requests.exceptions.ConnectionError:
            print(f'❌ Connection error for {url}')
        except Exception as e:
            print(f'❌ Error testing {url}: {e}')
        
        print()
    
    print('❌ No working multiplayer URL found')
    print('📝 You may need to manually check wzstats.gg to find the correct multiplayer section')
    return None

if __name__ == "__main__":
    working_url = test_multiplayer_urls()
    if working_url:
        print(f'🎯 Use this URL in your scraper: {working_url}')
    else:
        print('💡 Check wzstats.gg manually to find the multiplayer section URL') 