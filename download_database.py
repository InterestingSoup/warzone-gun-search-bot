#!/usr/bin/env python3
"""
Download the latest gun database artifact from GitHub Actions.
Useful for local development or manual deployment.
"""
import os
import json
import requests
import zipfile
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

def download_latest_database(repo_owner=None, repo_name=None, github_token=None):
    """Download the latest gun database artifact from GitHub Actions"""
    
    # Try to get repo info from environment or git
    if not repo_owner or not repo_name:
        try:
            # Try to get from git remote
            import subprocess
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                url = result.stdout.strip()
                # Parse GitHub URL
                if 'github.com' in url:
                    parts = url.replace('https://github.com/', '').replace('.git', '').split('/')
                    repo_owner = parts[0]
                    repo_name = parts[1]
        except:
            pass
    
    # Fallback values
    if not repo_owner:
        repo_owner = input("Enter GitHub username/organization: ").strip()
    if not repo_name:
        repo_name = input("Enter repository name: ").strip()
    
    if not github_token:
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            print("⚠️ No GitHub token found. You may hit rate limits.")
            print("   Set GITHUB_TOKEN in your .env file for authenticated access.")
    
    print(f"🔍 Fetching artifacts from {repo_owner}/{repo_name}...")
    
    # GitHub API endpoints
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if github_token:
        headers['Authorization'] = f'token {github_token}'
    
    artifacts_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/artifacts"
    
    try:
        # Get list of artifacts
        response = requests.get(artifacts_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Find gun-database artifacts
        gun_artifacts = [a for a in data['artifacts'] if a['name'] == 'gun-database']
        
        if not gun_artifacts:
            print("❌ No gun database artifacts found!")
            print("   Make sure the scraper workflow has run successfully.")
            return False
        
        # Get the latest artifact
        latest = gun_artifacts[0]  # Artifacts are sorted by created_at desc
        
        print(f"📊 Found artifact from {latest['created_at']}")
        print(f"💾 Size: {latest['size_in_bytes']} bytes")
        
        # Download artifact
        download_url = latest['archive_download_url']
        
        print("⬇️ Downloading artifact...")
        download_response = requests.get(download_url, headers=headers)
        download_response.raise_for_status()
        
        # Extract ZIP file
        with zipfile.ZipFile(BytesIO(download_response.content)) as z:
            z.extractall('.')
        
        # Verify the file
        if os.path.exists('all_guns_database.json'):
            with open('all_guns_database.json', 'r') as f:
                db = json.load(f)
            
            print("✅ Database downloaded successfully!")
            print(f"📊 Total weapons: {db['total_guns']}")
            print(f"📅 Last updated: {db['last_updated']}")
            print("🤖 Ready to run Discord bot: python discord_search_bot.py")
            return True
        else:
            print("❌ Database file not found in artifact!")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading artifact: {e}")
        if '404' in str(e):
            print("   Check that the repository exists and is accessible.")
        elif '403' in str(e):
            print("   You may need a GitHub token for private repositories.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    print("🔫 Gun Database Downloader")
    print("=" * 40)
    
    # Check if database already exists
    if os.path.exists('all_guns_database.json'):
        choice = input("Database already exists. Download fresh copy? (y/N): ").strip().lower()
        if choice != 'y':
            print("🚫 Download cancelled.")
            return
    
    success = download_latest_database()
    
    if success:
        print("\n🎯 Next steps:")
        print("1. Set up Discord bot token in .env file")
        print("2. Run: python discord_search_bot.py")
    else:
        print("\n💡 Alternative: Run the scraper locally")
        print("   python scrape.py")

if __name__ == "__main__":
    main() 