# 🔫 Warzone Gun Database & Discord Search Bot

This project provides **two separate tools**:

1. **📊 Gun Database Scraper** (`scrape.py`) - Scrapes ALL weapons from wzstats.gg and saves to JSON
2. **🤖 Discord Search Bot** (`discord_search_bot.py`) - Slash commands to search the gun database

---

## 🎯 Features

### 🔍 Comprehensive Gun Database
- ✅ Scrapes **ALL guns** in each category (Resurgence/Verdansk × Long Range/Close Range/Sniper)
- 💾 Stores complete database in `all_guns_database.json`
- 📈 Tracks weapon rankings, attachments, and meta updates
- 🖼️ Includes weapon images (top 5 per category)

### 🤖 Discord Search Bot
- ✅ `/search <weapon_name>` - Find weapons by name (fuzzy search)
- ✅ `/gun <weapon_name>` - Get detailed loadout for specific weapon
- ✅ `/top [mode] [range]` - Show top 10 weapons in category
- ✅ `/stats` - Database statistics and info
- 🎨 Beautiful embeds with weapon images and full attachment lists

---

## 🚀 Quick Start

### 1. Setup Scraper Environment
```bash
# Install scraper dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Create .env file (optional - only needed for weapon images)
cp .env.example .env
# Add your Imgur client ID if you want weapon images
```

### 2. Scrape Gun Database
```bash
python scrape.py
```

### 3. Setup & Run Discord Search Bot
```bash
# Install Discord bot dependencies
pip install -r discord_bot_requirements.txt

# Add Discord bot token to .env
# DISCORD_SEARCH_BOT_TOKEN=your_bot_token_here

# Run the search bot
python discord_search_bot.py
```

---

## 📋 Environment Variables

Create a `.env` file with:

```env
# Discord Search Bot (required for bot functionality)
DISCORD_SEARCH_BOT_TOKEN=your_search_bot_token_here

# Imgur (optional - for weapon images in database)
IMGUR_CLIENT_ID=your_imgur_client_id_here
```

---

## 🧠 Meta Query API (for AI tools)

All games are queryable through one JSON API, served on the same port as `/health`
(`start.py`, or standalone with `python meta_api.py`). Built so an AI can drill down
step by step and ask the user follow-up questions using the options it returns.

| Game id | Modes | Source |
|---|---|---|
| `mw4` | multiplayer, dmz-pvp, dmz-pve | wzstats.gg/mw4/meta |
| `warzone` | battle-royale, resurgence, ranked, ranked-resurgence, iron-gauntlet, black-ops-royale | wzstats.gg |
| `bo6` | multiplayer, ranked | wzstats.gg/bo6/meta |
| `bo7` | multiplayer, ranked | wzstats.gg/bo7/meta |

Data lives in `data/<game>.json`, scraped by `games/wzstats.py` (plain HTTP, no browser).
The container re-scrapes every `META_REFRESH_HOURS` (default 6); refresh by hand with
`python -m games.wzstats [game ...]`. `warzone`/`bo6` fall back to the legacy
`all_guns_database.json` if their data file is missing.

```
GET /api                                         index + usage hints for the AI
GET /api/games                                   games + modes
GET /api/games/mw4                               modes, categories, weapon types, tiers
GET /api/games/mw4/meta?mode=dmz-pvp&category=long-range&limit=5
GET /api/games/mw4/tier-list?mode=multiplayer&type=smg&tier=META
GET /api/games/mw4/weapons/han-86?mode=multiplayer
GET /api/games/warzone/meta?mode=resurgence&type=smg
GET /api/search?q=kastov&game=mw4
```

Params accept ids or loose names (`dmz pvp`, `long range`, `smg`). Errors return
the valid options, e.g. `Unknown mode 'resurgence'. Options: multiplayer, dmz-pvp, dmz-pve`.

**Adding a game:** if wzstats covers it, add an entry to `GAMES` in `games/wzstats.py`
and a `LOADERS` line in `meta_store.py`. Other sources: write a loader returning a `Game`.

---

## 🎮 Discord Bot Commands

### `/search <weapon_name>`
Search for weapons with partial names:
- `/search ak` → finds AK-74, AK-47, etc.
- `/search kar` → finds Kar98k variants  
- `/search fennec` → finds Fennec 45 loadouts

### `/gun <weapon_name>`
Get detailed info for a specific weapon:
- Shows rank, category, full attachment list
- Includes weapon image if available
- Perfect for getting exact loadout details

### `/top [mode] [range]`
Show top 10 weapons in a category:
- `/top Resurgence "Long Range"` → Top long-range Resurgence weapons
- `/top Verdansk Sniper` → Top Verdansk sniper rifles

### `/stats`
View database statistics:
- Total weapons count
- Last update timestamp  
- Weapons per category

---

## 📁 File Structure

```
├── scrape.py                     # Gun database scraper
├── discord_search_bot.py         # Discord search bot with slash commands
├── start.py                      # Production startup script (Render/cloud)
├── download_database.py          # Download database from GitHub Actions
├── test_database.py              # Test script to verify database
├── requirements.txt              # Scraper dependencies
├── discord_bot_requirements.txt  # Discord bot dependencies
├── render.yaml                   # Render deployment configuration
├── DEPLOY_RENDER.md             # Detailed Render deployment guide
├── .github/workflows/
│   ├── scrape-guns.yml           # Automated scraping workflow
│   └── deploy-bot.yml            # Bot deployment workflow
├── all_guns_database.json        # Weapon database (auto-generated)
├── .env.example                  # Environment variables template
└── .env                          # Your environment variables (create this)
```

---

## 🔧 Usage Workflow

### Option 1: GitHub Actions (Recommended)

#### 1. Set up GitHub Secrets
```bash
# In your GitHub repo settings > Secrets and variables > Actions
IMGUR_CLIENT_ID=your_imgur_client_id_here
DISCORD_SEARCH_BOT_TOKEN=your_bot_token_here
GITHUB_TOKEN=your_github_token_here  # For downloading artifacts
```

#### 2. Automated Scraping
- The scraper runs automatically twice daily (8 AM & 8 PM UTC)
- Creates `gun-database` artifact with the latest data
- Check the Actions tab to see scraping results

#### 3. Download Database Locally
```bash
# Download latest database from GitHub Actions
python download_database.py

# Then run Discord bot
python discord_search_bot.py
```

### Option 2: Local Development

#### 1. Build Database Locally
```bash
# Run scraper to get latest weapon data
python scrape.py
```

#### 2. Run Search Bot
```bash
# Keep Discord bot running 24/7 for slash commands
python discord_search_bot.py
```

---

## 📊 Database Structure

The `all_guns_database.json` contains:

```json
{
  "last_updated": "2024-01-20 15:30:45 UTC",
  "total_guns": 150,
  "categories": {
    "Resurgence_Long Range": [
      {
        "rank": 1,
        "mode": "Resurgence",
        "range": "Long Range", 
        "gun": "Kar98k",
        "class": ["• Monolithic Suppressor — Muzzle", "• Singuard Custom 27.6\" — Barrel", ...],
        "image": "https://i.imgur.com/...",
        "updated": "2024-01-20"
      }
    ]
  }
}
```

---

## 🤖 Discord Bot Setup

### 1. Create Discord Bot
1. Visit [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and bot
3. Copy the bot token to your `.env` file
4. Generate invite URL with permissions: `Send Messages`, `Use Slash Commands`, `Embed Links`

### 2. Add Bot to Server
Use the OAuth2 URL generator in Discord Developer Portal to invite your bot.

### 3. Bot Permissions
Required permissions: `applications.commands`, `bot` scope with `Send Messages`, `Embed Links`

---

## ⚙️ GitHub Actions Workflows

### 🔫 Scrape Gun Database (`scrape-guns.yml`)
- **Triggers**: Twice daily (8 AM & 8 PM UTC), manual, or code changes
- **Actions**: 
  - Installs dependencies and Playwright
  - Runs the scraper with Imgur integration
  - Validates the database
  - Uploads database as artifact (30-day retention)
  - Creates summary report

### 🤖 Deploy Discord Bot (`deploy-bot.yml`)
- **Triggers**: Manual deployment
- **Actions**:
  - Downloads latest gun database artifact
  - Sets up Discord bot environment
  - Runs validation tests
  - Ready for production deployment

### 💾 Artifacts
- **Name**: `gun-database`
- **Contents**: `all_guns_database.json`
- **Retention**: 30 days
- **Access**: Download via GitHub UI or API

---

## 🔍 Search Features

### Fuzzy Matching
The search bot uses intelligent fuzzy matching:
- Partial names: "ak" finds all AK variants
- Typos: "kar9k" still finds "Kar98k"  
- Smart scoring: Exact matches rank higher than partial matches

### Rich Embeds
- Weapon images (when available)
- Full attachment lists
- Category and ranking info
- Color-coded by game mode
- Professional formatting

---

## 🛠️ Troubleshooting

### Scraper Issues
- **Website changes**: Check if wzstats.gg selectors need updating
- **No images**: Verify Imgur client ID in `.env`
- **Slow scraping**: This is normal, we scrape responsibly to avoid rate limits

### Discord Bot Issues  
- **Bot not responding**: Check bot token and server permissions
- **"No data" errors**: Run `python scrape.py` first to create database
- **Commands not showing**: Wait ~1 hour for Discord to sync slash commands

### Debug Commands
```bash
# Test database after scraping
python test_database.py

# Check if database exists and has data
python -c "import json; db=json.load(open('all_guns_database.json')); print(f'Total guns: {db[\"total_guns\"]}')"

# Test scraper without images
IMGUR_CLIENT_ID="" python scrape.py
```

---

## 📈 Performance

- **Scraping**: ~2-5 minutes for all categories (respects rate limits)
- **Search**: Instant response from local JSON database
- **Memory**: Lightweight - entire database typically < 1MB
- **Discord**: Fast slash command responses

---

## 🚀 Deployment Options

### 🌟 Render (Recommended)
**Perfect for 24/7 Discord bot hosting with free tier!**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

```bash
# Quick start:
1. Fork this repository
2. Connect to Render
3. Set environment variables
4. Deploy!
```

📖 **[Complete Render Deployment Guide →](DEPLOY_RENDER.md)**

### Local Development
```bash
python download_database.py  # Get latest data
python discord_search_bot.py # Run bot locally
```

### Other Cloud Platforms

#### Railway/Heroku/DigitalOcean
```bash
# Startup command:
python start.py
```

Environment variables needed:
- `DISCORD_SEARCH_BOT_TOKEN`
- `GITHUB_TOKEN` (optional)
- `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME` (optional)

#### Docker
```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r discord_bot_requirements.txt
CMD python start.py
```

#### GitHub Actions Self-Hosted
Use the `deploy-bot.yml` workflow with your own runners for automatic deployment.

---

## 🎯 Next Steps

### For GitHub Actions + Local Development:
1. **Set up GitHub repository** with the workflows
2. **Configure GitHub secrets** for automation
3. **Run scraper workflow** to build your database
4. **Download artifacts** and run bot locally

### For 24/7 Deployment on Render:
1. **Fork this repository** to your GitHub
2. **Follow the [Render deployment guide](DEPLOY_RENDER.md)**
3. **Set up environment variables** in Render
4. **Deploy and enjoy 24/7 bot operation!**

### For Both:
5. **Test search commands** in your Discord server
6. **Monitor bot performance** and logs

Happy gaming! 🎮

---
