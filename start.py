#!/usr/bin/env python3
"""
Startup script for continuous Discord bot deployment on Render or other platforms.
Downloads latest gun database and starts the Discord bot with health check server.
"""
import os
import sys
import time
import subprocess
import threading
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import datetime

webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
if webhook_url:
    requests.post(webhook_url, json={
        "embeds": [{
            "title": "🚀 B06 Meta Search Bot Re-Deployed",
            "description": "The Discord bot has been redeployed and started.",
            "color": 3447003,
            "footer": { "text": "Coolify Deploy" },
            "timestamp": datetime.datetime.utcnow().isoformat()
        }]
    })

def download_latest_database():
    """Download the latest database before starting the bot"""
    print("🔄 Checking for latest gun database...")
    
    # Import the download function
    sys.path.append(str(Path(__file__).parent))
    
    try:
        from download_database import download_latest_database
        
        # Try to download with environment variables
        repo_owner = os.getenv('GITHUB_REPO_OWNER')
        repo_name = os.getenv('GITHUB_REPO_NAME') 
        github_token = os.getenv('GITHUB_TOKEN')
        
        success = download_latest_database(repo_owner, repo_name, github_token)
        
        if success:
            print("✅ Database downloaded successfully!")
            return True
        else:
            print("⚠️ Could not download database from GitHub")
            return False
            
    except Exception as e:
        print(f"⚠️ Error downloading database: {e}")
        return False

def check_database_exists():
    """Check if database file exists locally"""
    print(f"📁 Current working directory: {Path.cwd()}")
    print(f"📂 Files: {os.listdir()}")
    db_path = Path("gun-database")
    if db_path.exists():
        print(f"✅ Database found: {db_path.stat().st_size} bytes")
        return True
    else:
        print("❌ No database file found")
        return False

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple health check server for Render"""
    
    def do_GET(self):
        if self.path == '/health':
            # Check if database exists and bot is ready
            db_exists = Path("gun-database").exists()
            discord_token = os.getenv('DISCORD_SEARCH_BOT_TOKEN')
            
            if db_exists and discord_token:
                response = {
                    "status": "healthy",
                    "service": "warzone-gun-search-bot",
                    "database": "loaded",
                    "discord": "configured"
                }
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            else:
                response = {
                    "status": "unhealthy",
                    "database": "loaded" if db_exists else "missing",
                    "discord": "configured" if discord_token else "missing"
                }
                self.send_response(503)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
        else:
            # Default response for other paths
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html_response = '<html><body><h1>Warzone Gun Search Bot</h1><p>Discord bot is running!</p><p><a href="/health">Health Check</a></p></body></html>'
            self.wfile.write(html_response.encode('utf-8'))
    
    def log_message(self, format, *args):
        # Suppress default HTTP logs to keep Discord logs clean
        pass

def start_health_server():
    """Start health check server for Render"""
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"🌐 Health check server starting on port {port}")
    server.serve_forever()

def start_discord_bot():
    """Start the Discord bot in a separate thread"""
    print("🤖 Starting Discord search bot...")
    
    # Check for Discord token
    discord_token = os.getenv('DISCORD_SEARCH_BOT_TOKEN')
    if not discord_token:
        print("❌ DISCORD_SEARCH_BOT_TOKEN not found in environment variables!")
        print("   Add this in your Render dashboard under Environment Variables")
        sys.exit(1)
    
    # Import and run the bot
    try:
        from discord_search_bot import bot
        bot.run(discord_token)
    except Exception as e:
        print(f"❌ Error starting Discord bot: {e}")
        sys.exit(1)

def main():
    print("🚀 Starting Discord Bot Service")
    print("=" * 50)
    
    # Try to download latest database
    db_downloaded = download_latest_database()
    
    # Check if we have a database (either downloaded or existing)
    if not check_database_exists():
        if not db_downloaded:
            print("💡 No database available. Options:")
            print("   1. Set GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME in environment")
            print("   2. Upload gun-database manually to your deployment")
            print("   3. Run scraper locally first: python scrape.py")
            sys.exit(1)
    
    # Test database before starting bot
    try:
        from test_database import test_database
        if not test_database():
            print("❌ Database test failed!")
            sys.exit(1)
    except Exception as e:
        print(f"⚠️ Could not test database: {e}")
    
    print("🎯 All checks passed - starting services...")
    print("📡 Bot will be available for slash commands")
    
    # Start Discord bot in a separate thread
    bot_thread = threading.Thread(target=start_discord_bot, daemon=True)
    bot_thread.start()
    
    # Start health check server (this will run indefinitely)
    print("🌐 Starting health check server for Render...")
    start_health_server()

if __name__ == "__main__":
    main() 