#!/usr/bin/env python3
"""
Discord bot with Azure OpenAI query composition integration
"""
import os
import json
import asyncio
from typing import Dict, List, Optional
from dotenv import load_dotenv
import discord
from discord.ext import commands
from openai import AsyncAzureOpenAI

load_dotenv()

class AzureGunBotAI:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
    async def compose_query(self, conversation_history: List[Dict], available_categories: Dict) -> str:
        """Use Azure OpenAI to help compose search queries"""
        
        system_prompt = f"""
You are a helpful Warzone weapon expert. Help users find specific weapon loadouts by asking clarifying questions.

Available categories:
{json.dumps(available_categories, indent=2)}

When a user mentions a weapon, check if you need more information:
1. Which game mode? (Resurgence or Verdansk)
2. Which range category? (Long Range, Close Range, or Sniper)

Once you have both mode and range category, respond with:
"SEARCH_READY: {{mode}}_{{range}}_{{weapon}}"

Be conversational and helpful. Use emojis and make it engaging.
"""
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",  # or gpt-35-turbo for lower cost
                messages=[{"role": "system", "content": system_prompt}] + conversation_history,
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Sorry, I'm having trouble right now. Try using the regular `/search` command! Error: {e}"

class ConversationalGunBot:
    def __init__(self):
        self.ai_client = AzureGunBotAI()
        self.database = self.load_gun_database()
        self.user_sessions = {}  # Track conversations per user
        
    def load_gun_database(self):
        """Load the gun database"""
        try:
            with open('all_guns_database.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ Gun database not found! Run scraper first.")
            return {"categories": {}, "total_guns": 0}
    
    def get_available_categories(self) -> Dict:
        """Get available categories for AI context"""
        categories = {}
        for category_key in self.database.get("categories", {}):
            mode, range_type = category_key.split("_", 1)
            if mode not in categories:
                categories[mode] = []
            categories[mode].append(range_type)
        return categories
    
    async def handle_conversation(self, user_id: str, message: str) -> str:
        """Handle conversational search with AI"""
        
        # Initialize user session
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {"conversation": []}
        
        session = self.user_sessions[user_id]
        session["conversation"].append({"role": "user", "content": message})
        
        # Get AI response
        categories = self.get_available_categories()
        ai_response = await self.ai_client.compose_query(session["conversation"], categories)
        
        # Check if AI is ready to search
        if "SEARCH_READY:" in ai_response:
            # Extract search parameters
            search_params = ai_response.split("SEARCH_READY:")[1].strip()
            try:
                mode, range_type, weapon = search_params.split("_", 2)
                
                # Perform the actual search
                result = self.search_specific_weapon(weapon, mode, range_type)
                
                # Clear conversation for next search
                self.user_sessions[user_id] = {"conversation": []}
                
                if result:
                    return self.format_weapon_result(result)
                else:
                    return f"❌ Sorry, I couldn't find **{weapon}** in **{mode} - {range_type}**.\nTry a different category or check the spelling!"
            
            except ValueError:
                return "❌ Something went wrong with the search. Let's start over - what weapon are you looking for?"
        
        else:
            # Continue conversation
            session["conversation"].append({"role": "assistant", "content": ai_response})
            return ai_response
    
    def search_specific_weapon(self, weapon_name: str, mode: str, range_type: str) -> Optional[Dict]:
        """Search for a weapon in a specific category"""
        category_key = f"{mode}_{range_type}"
        
        if category_key not in self.database["categories"]:
            return None
        
        guns = self.database["categories"][category_key]
        
        # Find weapon (case insensitive, partial match)
        for gun in guns:
            if weapon_name.lower() in gun["gun"].lower():
                return gun
        
        return None
    
    def format_weapon_result(self, weapon_data: Dict) -> str:
        """Format weapon data for Discord"""
        emoji_map = {
            ("Resurgence", "Long Range"): "🏹",
            ("Resurgence", "Close Range"): "🔫", 
            ("Resurgence", "Sniper"): "🔭",
            ("Verdansk", "Long Range"): "🏹",
            ("Verdansk", "Close Range"): "🔫",
            ("Verdansk", "Sniper"): "🔭"
        }
        
        emoji = emoji_map.get((weapon_data["mode"], weapon_data["range"]), "🛡️")
        
        result = f"{emoji} **{weapon_data['gun']}** - {weapon_data['mode']} {weapon_data['range']}\n"
        result += f"**Rank:** #{weapon_data['rank']}\n"
        result += f"**Updated:** {weapon_data['updated']}\n\n"
        result += "**Attachments:**\n"
        result += "\n".join(weapon_data["class"][:10])  # Show up to 10 attachments
        
        return result

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize conversational bot
gun_bot = ConversationalGunBot()

@bot.event
async def on_ready():
    print(f"🤖 AI Gun Bot logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.tree.command(name="find", description="Find a weapon with AI assistance")
async def find_weapon(interaction: discord.Interaction, query: str):
    """AI-powered conversational weapon search"""
    await interaction.response.defer()
    
    try:
        user_id = str(interaction.user.id)
        response = await gun_bot.handle_conversation(user_id, query)
        
        # Split long responses for Discord's character limit
        if len(response) > 2000:
            await interaction.followup.send(response[:2000])
            await interaction.followup.send(response[2000:])
        else:
            await interaction.followup.send(response)
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}\nTry using `/search` for basic search.")

@bot.tree.command(name="search", description="Quick weapon search (original functionality)")  
async def search_weapon(interaction: discord.Interaction, weapon_name: str):
    """Original fast search - no AI"""
    await interaction.response.defer()
    
    # Use existing search logic from discord_search_bot.py
    from discord_search_bot import search_guns
    
    database = gun_bot.database
    all_guns = []
    for guns in database.get("categories", {}).values():
        all_guns.extend(guns)
    
    results = search_guns(weapon_name, max_results=5)
    
    if not results:
        await interaction.followup.send(f"🚫 No weapons found matching **{weapon_name}**")
        return
    
    if len(results) == 1:
        # Single result - show detailed info
        response = gun_bot.format_weapon_result(results[0])
        await interaction.followup.send(response)
    else:
        # Multiple results - show list
        description = f"Found {len(results)} weapons matching **{weapon_name}**:\n\n"
        
        for i, gun in enumerate(results, 1):
            description += f"**{i}.** {gun['gun']} - {gun['mode']} {gun['range']} (Rank #{gun['rank']})\n"
        
        description += f"\n💡 Use `/find {weapon_name}` for AI-guided precise search"
        
        embed = discord.Embed(
            title="🔍 Search Results", 
            description=description,
            color=0x3498db
        )
        await interaction.followup.send(embed=embed)

if __name__ == "__main__":
    token = os.getenv('DISCORD_SEARCH_BOT_TOKEN')
    if not token:
        print("❌ DISCORD_SEARCH_BOT_TOKEN not found in environment variables!")
        exit(1)
        
    # Check for Azure OpenAI credentials
    if not os.getenv('AZURE_OPENAI_KEY') or not os.getenv('AZURE_OPENAI_ENDPOINT'):
        print("⚠️ Azure OpenAI credentials not found. AI features will be disabled.")
        print("   Set AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT in your .env file")
    
    bot.run(token) 