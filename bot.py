import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import requests

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load or initialize config.json
def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except:
        return {"guild_id": None}

def save_config(cfg):
    with open("config.json", "w") as f:
        json.dump(cfg, f, indent=4)

# Load users.json (OAuth users)
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}

#====================================
# COMMAND 1: Set the target server
#====================================

@bot.command(name="setserver")
async def setserver(ctx, guild_id: int):
    cfg = load_config()
    cfg["guild_id"] = guild_id
    save_config(cfg)
    await ctx.send(f"Guild ID set to `{guild_id}`.")
    
#====================================
# COMMAND 2: Add one user to server
#====================================

@bot.command(name="adduser")
async def adduser(ctx, user_id: int):
    cfg = load_config()
    guild_id = cfg.get("guild_id")

    if guild_id is None:
        await ctx.send("Guild ID not set. Use `!setserver <id>` first.")
        return

    users = load_users()
    user_data = users.get(str(user_id))

    if not user_data:
        await ctx.send("User not found in OAuth records.")
        return

    access_token = user_data["access_token"]

    # Discord API call to add user
    url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}"
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"access_token": access_token}

    r = requests.put(url, headers=headers, json=payload)

    if r.status_code in (200, 201, 204):
        await ctx.send(f"Successfully added user `{user_id}` to guild `{guild_id}`.")
    else:
        await ctx.send(f"Failed with status {r.status_code}: {r.text}")

#====================================
# COMMAND 3: Add ALL OAuth users
#====================================

@bot.command(name="addall")
async def addall(ctx):
    cfg = load_config()
    guild_id = cfg.get("guild_id")

    if guild_id is None:
        await ctx.send("Guild ID not set. Use `!setserver <id>` first.")
        return

    users = load_users()

    if not users:
        await ctx.send("No OAuth users found.")
        return

    success = 0
    fail = 0

    for user_id, data in users.items():
        url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}"
        headers = {
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {"access_token": data["access_token"]}

        r = requests.put(url, headers=headers, json=payload)

        if r.status_code in (200, 201, 204):
            success += 1
        else:
            fail += 1

    await ctx.send(f"Finished. Success: {success}, Failed: {fail}")

# Run the bot
bot.run(BOT_TOKEN)
