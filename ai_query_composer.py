#!/usr/bin/env python3
"""
AI Query Composer Example - Using Azure OpenAI to help users compose precise searches
Instead of AI doing the search, AI helps users navigate to the exact data they want.
"""
import json
import asyncio
from typing import Dict, List, Optional

# Mock Azure OpenAI client (replace with actual implementation)
class MockAzureOpenAI:
    def __init__(self):
        self.conversation_context = {}
    
    async def chat_completion(self, messages: List[Dict], user_id: str) -> str:
        """Mock Azure OpenAI chat completion"""
        user_message = messages[-1]["content"].lower()
        
        # Simple mock responses based on patterns
        if any(weapon in user_message for weapon in ["c9", "ak", "kar", "hdR"]):
            weapon = next(w for w in ["c9", "ak", "kar", "hdr"] if w in user_message)
            return f"I found {weapon.upper()} in multiple categories. Which game mode do you prefer?\n🎮 **Resurgence** or **Verdansk**?"
        
        elif any(mode in user_message for mode in ["resurgence", "verdansk"]):
            mode = "Resurgence" if "resurgence" in user_message else "Verdansk"
            return f"Great! {mode} it is. Which range category?\n🎯 **Long Range**, **Close Range**, or **Sniper**?"
        
        elif any(range_type in user_message for range_type in ["long", "close", "sniper"]):
            if "long" in user_message:
                return "Perfect! Searching for Long Range loadouts..."
            elif "close" in user_message:
                return "Perfect! Searching for Close Range loadouts..."
            else:
                return "Perfect! Searching for Sniper loadouts..."
        
        else:
            return "I can help you find weapon loadouts! Try asking about a specific weapon like 'C9' or 'AK-74'."

def load_gun_database():
    """Load the gun database"""
    with open('all_guns_database.json', 'r') as f:
        return json.load(f)

def search_specific_category(weapon_name: str, mode: str, range_type: str, database: Dict) -> Optional[Dict]:
    """Search for a specific weapon in a specific category"""
    category_key = f"{mode}_{range_type}"
    
    if category_key not in database["categories"]:
        return None
    
    guns = database["categories"][category_key]
    
    # Find exact or partial match
    for gun in guns:
        if weapon_name.lower() in gun["gun"].lower():
            return gun
    
    return None

class ConversationalGunBot:
    def __init__(self):
        self.ai_client = MockAzureOpenAI()
        self.database = load_gun_database()
        self.user_sessions = {}  # Track conversation state per user
    
    async def handle_message(self, user_id: str, message: str) -> str:
        """Handle a user message and return appropriate response"""
        
        # Initialize or get user session
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "state": "initial",
                "weapon": None,
                "mode": None,
                "range": None,
                "conversation": []
            }
        
        session = self.user_sessions[user_id]
        session["conversation"].append({"role": "user", "content": message})
        
        # Parse the message to extract intent and update session
        await self._update_session_from_message(session, message)
        
        # If we have all required info, perform the search
        if session["weapon"] and session["mode"] and session["range"]:
            result = search_specific_category(
                session["weapon"], 
                session["mode"], 
                session["range"], 
                self.database
            )
            
            if result:
                response = self._format_weapon_result(result)
                # Reset session for next query
                self.user_sessions[user_id] = {"state": "initial", "weapon": None, "mode": None, "range": None, "conversation": []}
                return response
            else:
                return f"❌ Sorry, I couldn't find {session['weapon']} in {session['mode']} {session['range']}. Try a different category?"
        
        # Otherwise, use AI to ask for missing information
        ai_response = await self.ai_client.chat_completion(session["conversation"], user_id)
        session["conversation"].append({"role": "assistant", "content": ai_response})
        
        return ai_response
    
    async def _update_session_from_message(self, session: Dict, message: str) -> None:
        """Extract weapon, mode, and range from user message"""
        message_lower = message.lower()
        
        # Extract weapon name
        weapon_keywords = ["c9", "ak", "kar", "hdr", "ffar", "lc10", "m4", "krig"]
        for weapon in weapon_keywords:
            if weapon in message_lower:
                session["weapon"] = weapon
                break
        
        # Extract mode
        if "resurgence" in message_lower:
            session["mode"] = "Resurgence"
        elif "verdansk" in message_lower:
            session["mode"] = "Verdansk"
        
        # Extract range
        if "long" in message_lower and "range" in message_lower:
            session["range"] = "Long Range"
        elif "close" in message_lower and "range" in message_lower:
            session["range"] = "Close Range"
        elif "sniper" in message_lower:
            session["range"] = "Sniper"
    
    def _format_weapon_result(self, weapon_data: Dict) -> str:
        """Format weapon data for Discord response"""
        emoji_map = {
            ("Resurgence", "Long Range"): "🏹",
            ("Resurgence", "Close Range"): "🔫", 
            ("Resurgence", "Sniper"): "🔭",
            ("Verdansk", "Long Range"): "🏹",
            ("Verdansk", "Close Range"): "🔫",
            ("Verdansk", "Sniper"): "🔭"
        }
        
        emoji = emoji_map.get((weapon_data["mode"], weapon_data["range"]), "🛡️")
        
        response = f"{emoji} **{weapon_data['gun']}** - {weapon_data['mode']} {weapon_data['range']}\n"
        response += f"**Rank:** #{weapon_data['rank']}\n"
        response += f"**Updated:** {weapon_data['updated']}\n\n"
        response += "**Attachments:**\n"
        response += "\n".join(weapon_data["class"][:8])  # Show first 8 attachments
        
        return response

async def demo_conversation():
    """Demonstrate the conversational flow"""
    print("🤖 AI Query Composer Demo")
    print("=" * 50)
    print("This shows how AI helps compose precise search queries\n")
    
    bot = ConversationalGunBot()
    user_id = "demo_user"
    
    # Simulate a conversation
    conversation = [
        "show me c9",
        "verdansk", 
        "close range"
    ]
    
    for i, user_input in enumerate(conversation, 1):
        print(f"👤 User: {user_input}")
        response = await bot.handle_message(user_id, user_input)
        print(f"🤖 Bot: {response}")
        print()
        
        # Add a small delay to simulate real conversation
        await asyncio.sleep(0.1)

def show_architecture():
    """Show the AI query composer architecture"""
    print("🏗️ AI Query Composer Architecture")
    print("=" * 50)
    
    flow = """
    1. 👤 User: "show me c9"
       ↓
    2. 🤖 AI: Recognizes weapon but missing context
       ↓  
    3. 🤖 AI: "Which mode? Resurgence or Verdansk?"
       ↓
    4. 👤 User: "verdansk"
       ↓
    5. 🤖 AI: "Which range? Long Range, Close Range, or Sniper?"
       ↓
    6. 👤 User: "close range"
       ↓
    7. 🔍 System: Composes query -> search_specific_category("c9", "Verdansk", "Close Range")
       ↓
    8. 📊 JSON: Fast local search in Verdansk_Close Range category
       ↓
    9. 🤖 Bot: Returns formatted weapon loadout
    """
    
    print(flow)

def show_benefits():
    """Show benefits of this approach"""
    print("✅ Benefits of AI Query Composition")
    print("=" * 50)
    
    benefits = [
        "🎯 **Precise Results**: No more 20+ results for 'AK', just the exact one you want",
        "💬 **Natural Conversation**: Users can ask casually, AI guides them",
        "⚡ **Still Fast**: JSON search is still ~1ms once query is composed", 
        "🧠 **Smart Context**: AI remembers what you're looking for in the conversation",
        "🔧 **Easy to Extend**: Add new categories/filters without changing search logic",
        "💰 **Cost Efficient**: Only 2-3 AI calls per complete search (vs per-search)",
        "🎮 **Better UX**: Users discover categories they didn't know existed"
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")
    
    print()

def show_azure_implementation():
    """Show actual Azure OpenAI implementation"""
    print("☁️ Azure OpenAI Implementation")
    print("=" * 50)
    
    code = '''
from openai import AsyncAzureOpenAI

class AzureGunBotAI:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key="your-azure-key",
            api_version="2024-02-01", 
            azure_endpoint="https://your-resource.openai.azure.com"
        )
    
    async def compose_query(self, conversation_history):
        system_prompt = """
        You help users find specific weapon loadouts. Available categories:
        - Modes: Resurgence, Verdansk  
        - Ranges: Long Range, Close Range, Sniper
        
        Ask clarifying questions to get exact category + weapon name.
        Once you have both, say "SEARCH_READY: {mode}_{range}_{weapon}"
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": system_prompt}] + conversation_history,
            max_tokens=150,
            temperature=0.3
        )
        
        return response.choices[0].message.content

# Usage in Discord bot:
@bot.tree.command(name="find", description="Find a weapon with AI help")
async def find_weapon(interaction, query: str):
    # Start conversational flow
    ai_response = await ai_client.compose_query([{"role": "user", "content": query}])
    
    if "SEARCH_READY:" in ai_response:
        # Extract and perform search
        search_params = ai_response.split("SEARCH_READY:")[1].strip()
        # ... perform JSON search and return result
    else:
        # Continue conversation
        await interaction.response.send_message(ai_response)
'''
    
    print(code)

async def main():
    await demo_conversation()
    show_architecture()
    show_benefits()
    show_azure_implementation()
    
    print("🎯 Perfect Use Case for Azure OpenAI!")
    print("   • Conversational interface for data navigation")
    print("   • Composes precise queries for fast JSON search") 
    print("   • 2-3 API calls per complete search (very cost effective)")
    print("   • Users get exactly what they want, not 20+ results")

if __name__ == "__main__":
    asyncio.run(main()) 