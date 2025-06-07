#!/usr/bin/env python3
import os
import json
import asyncio
from difflib import SequenceMatcher
from dotenv import load_dotenv
import discord
from discord.ext import commands

# === Load Environment ===
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_SEARCH_BOT_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")  # Add channel ID from environment
ALL_GUNS_STORE = "all_guns_database.json"

# === Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True  # Enable guild (server) intents
bot = commands.Bot(command_prefix="!", intents=intents)  # or any other prefix
def load_all_guns_database():
    """Load the comprehensive guns database"""
    if os.path.exists(ALL_GUNS_STORE):
        try:
            with open(ALL_GUNS_STORE, "r") as f:
                return json.loads(f.read())
        except Exception as e:
            print(f"⚠️ Could not load all guns database: {e}")
    print(f"⚠️ Database file {ALL_GUNS_STORE} not found!")
    print("💡 To get the database:")
    print("   - Run: python scrape.py")
    print("   - Or: python download_database.py")
    return {"categories": {}, "total_guns": 0}

def similarity(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def search_guns(query, max_results=10):
    """Search for guns by name with fuzzy matching"""
    database = load_all_guns_database()
    if not database or not database.get("categories"):
        return []
    
    results = []
    query_lower = query.lower()
    
    # Search through all categories
    for category, guns in database["categories"].items():
        for gun in guns:
            gun_name = gun["gun"].lower()
            
            # Exact match (highest priority)
            if query_lower in gun_name:
                score = 1.0 if query_lower == gun_name else 0.9
                results.append((score, gun))
            # Fuzzy match (lower priority)
            elif similarity(query_lower, gun_name) > 0.6:
                score = similarity(query_lower, gun_name) * 0.8
                results.append((score, gun))
    
    # Sort by score (highest first) and return top results
    results.sort(key=lambda x: x[0], reverse=True)
    return [gun for score, gun in results[:max_results]]

def format_gun_embed(gun):
    """Format gun data as a Discord embed"""
    emoji_map = {
        # Warzone categories
        ("Resurgence", "Long Range"): "🏹",
        ("Resurgence", "Close Range"): "🔫", 
        ("Resurgence", "Sniper"): "🔭",
        ("Verdansk", "Long Range"): "🏹",
        ("Verdansk", "Close Range"): "🔫",
        ("Verdansk", "Sniper"): "🔭",
        # Multiplayer categories
        ("Multiplayer", "Assault Rifle"): "🔫",
        ("Multiplayer", "SMG"): "🔫",
        ("Multiplayer", "Shotgun"): "💥",
        ("Multiplayer", "LMG"): "⚔️",
        ("Multiplayer", "Marksman Rifle"): "🎯",
        ("Multiplayer", "Sniper"): "🔭",
        ("Multiplayer", "Pistol"): "🔫"
    }
    
    color_map = {
        "Resurgence": 0x3498db,  # Blue
        "Verdansk": 0x2ecc71,    # Green
        "Multiplayer": 0x9b59b6  # Purple
    }
    
    emoji = emoji_map.get((gun["mode"], gun["range"]), "🛡️")
    color = color_map.get(gun["mode"], 0x7289DA)
    
    title = f"{emoji} {gun['gun']}"
    description = f"**Category:** {gun['mode']} - {gun['range']}\n"
    description += f"**Rank:** #{gun['rank']}\n"
    description += f"**Updated:** {gun['updated']}\n\n"
    
    if gun["class"]:
        description += "**Attachments:**\n" + "\n".join(gun["class"][:10])  # Limit to 10 attachments
        if len(gun["class"]) > 10:
            description += f"\n... and {len(gun['class']) - 10} more"
    
    embed = discord.Embed(title=title, description=description, color=color)
    
    if gun.get("image"):
        embed.set_thumbnail(url=gun["image"])
    
    embed.set_footer(text=f"🔍 Warzone Gun Database")
    return embed

@bot.event
async def on_ready():
    print(f"🤖 Search Bot logged in as {bot.user}")
    print(f"📊 Connected to {len(bot.guilds)} servers")
    
    # Sync commands with Discord
    try:
        # Sync to all guilds the bot is in
        for guild in bot.guilds:
            print(f"🔄 Syncing commands to {guild.name}...")
            synced = await bot.tree.sync(guild=guild)
            print(f"✅ Synced {len(synced)} commands to {guild.name}")
        print("✅ Successfully synced commands to all servers")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
        print("Please ensure the bot has the 'applications.commands' scope when invited")

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Only process commands if they start with the prefix
    if message.content.startswith('!'):
        await bot.process_commands(message)

@bot.tree.command(name="search", description="Search for a weapon loadout")
async def search(interaction: discord.Interaction, weapon_name: str):
    """Search for a weapon by name"""
    await interaction.response.defer()
    
    results = search_guns(weapon_name, max_results=5)
    
    if not results:
        embed = discord.Embed(
            title="🚫 No Results Found", 
            description=f"No weapons found matching **{weapon_name}**\n\nTry searching with partial names like 'ak', 'kar', 'fennec', etc.",
            color=0xe74c3c
        )
        await interaction.followup.send(embed=embed)
        return
    
    if len(results) == 1:
        # Single result - show detailed info
        embed = format_gun_embed(results[0])
        await interaction.followup.send(embed=embed)
    else:
        # Multiple results - show list
        description = f"Found {len(results)} weapons matching **{weapon_name}**:\n\n"
        
        for i, gun in enumerate(results, 1):
            description += f"**{i}.** {gun['gun']} - {gun['mode']} {gun['range']} (Rank #{gun['rank']})\n"
        
        description += f"\n💡 Use `/gun <exact_name>` for detailed loadout info"
        
        embed = discord.Embed(
            title="🔍 Search Results", 
            description=description,
            color=0x3498db
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="gun", description="Get detailed info for a specific weapon")
async def gun(interaction: discord.Interaction, weapon_name: str):
    """Get detailed info for a specific weapon"""
    await interaction.response.defer()
    
    results = search_guns(weapon_name, max_results=1)
    
    if not results:
        embed = discord.Embed(
            title="🚫 Weapon Not Found", 
            description=f"No weapon found matching **{weapon_name}**\n\nUse `/search <partial_name>` to find available weapons.",
            color=0xe74c3c
        )
        await interaction.followup.send(embed=embed)
        return
    
    embed = format_gun_embed(results[0])
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="top", description="Show top weapons in a category")
async def top(interaction: discord.Interaction, 
              mode: str = "Resurgence", 
              range_type: str = "Long Range"):
    """Show top weapons in a specific category"""
    await interaction.response.defer()
    
    database = load_all_guns_database()
    category_key = f"{mode}_{range_type}"
    
    if category_key not in database.get("categories", {}):
        valid_categories = list(database.get("categories", {}).keys())
        embed = discord.Embed(
            title="🚫 Invalid Category", 
            description=f"Category **{mode} - {range_type}** not found.\n\nValid categories:\n" + 
                       "\n".join([cat.replace("_", " - ") for cat in valid_categories]),
            color=0xe74c3c
        )
        await interaction.followup.send(embed=embed)
        return
    
    guns = database["categories"][category_key][:10]  # Top 10
    
    if not guns:
        embed = discord.Embed(
            title="🚫 No Data", 
            description=f"No weapons found for **{mode} - {range_type}**",
            color=0xe74c3c
        )
        await interaction.followup.send(embed=embed)
        return
    
    emoji_map = {
        ("Resurgence", "Long Range"): "🏹",
        ("Resurgence", "Close Range"): "🔫", 
        ("Resurgence", "Sniper"): "🔭",
        ("Verdansk", "Long Range"): "🏹",
        ("Verdansk", "Close Range"): "🔫",
        ("Verdansk", "Sniper"): "🔭"
    }
    
    emoji = emoji_map.get((mode, range_type), "🛡️")
    
    description = f"Top {len(guns)} weapons in **{mode} - {range_type}**:\n\n"
    
    for gun in guns:
        description += f"**{gun['rank']}.** {gun['gun']}\n"
    
    description += f"\n💡 Use `/gun <weapon_name>` for detailed loadout"
    
    embed = discord.Embed(
        title=f"{emoji} {mode} - {range_type} Meta",
        description=description,
        color=0x3498db if mode == "Resurgence" else 0x2ecc71
    )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="stats", description="Show database statistics")
async def stats(interaction: discord.Interaction):
    """Show database statistics"""
    database = load_all_guns_database()
    
    if not database or not database.get("categories"):
        embed = discord.Embed(
            title="🚫 No Data", 
            description="Gun database is empty or not found.",
            color=0xe74c3c
        )
        await interaction.followup.send(embed=embed)
        return
    
    total_guns = database.get("total_guns", 0)
    last_updated = database.get("last_updated", "Unknown")
    categories = database.get("categories", {})
    
    description = f"**Total Weapons:** {total_guns}\n"
    description += f"**Last Updated:** {last_updated}\n\n"
    description += "**Categories:**\n"
    
    for category, guns in categories.items():
        cat_name = category.replace("_", " - ")
        description += f"• {cat_name}: {len(guns)} weapons\n"
    
    embed = discord.Embed(
        title="📊 Database Statistics",
        description=description,
        color=0x9b59b6
    )
    
    await interaction.followup.send(embed=embed)

# Command autocomplete for mode and range_type
@top.autocomplete('mode')
async def mode_autocomplete(interaction: discord.Interaction, current: str):
    modes = ["Resurgence", "Verdansk", "Multiplayer"]
    return [
        discord.app_commands.Choice(name=mode, value=mode)
        for mode in modes if current.lower() in mode.lower()
    ]

@top.autocomplete('range_type')
async def range_type_autocomplete(interaction: discord.Interaction, current: str):
    # Get all possible categories from the database
    database = load_all_guns_database()
    categories = set()
    
    for category_key in database.get("categories", {}):
        if "_" in category_key:
            mode, category = category_key.split("_", 1)
            categories.add(category)
    
    # Convert to list and sort
    ranges = sorted(list(categories))
    
    return [
        discord.app_commands.Choice(name=range_type, value=range_type)
        for range_type in ranges if current.lower() in range_type.lower()
    ][:25]  # Discord limits to 25 choices

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        print("❌ DISCORD_SEARCH_BOT_TOKEN not found in environment variables")
        print("Add DISCORD_SEARCH_BOT_TOKEN=your_bot_token to your .env file")
        exit(1)
    
    bot.run(DISCORD_BOT_TOKEN) 