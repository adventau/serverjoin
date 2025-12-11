import discord
from discord.ext import commands
import requests
import json
import os
from dotenv import load_dotenv
from flask import Flask, request, redirect
from threading import Thread

# ==========================================
# Load environment variables
# ==========================================
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_PATH = os.path.join(BASE_DIR, "users.json")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# ==========================================
# Flask OAuth App
# ==========================================
app = Flask(__name__)

def load_users():
    try:
        with open(USERS_PATH, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(USERS_PATH, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/")
def home():
    return "OAuth Login Ready. Go to /login to authenticate."

@app.route("/login")
def login():
    params = (
        f"client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20email%20guilds%20guilds.join"
    )
    return redirect(f"https://discord.com/oauth2/authorize?{params}")

@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return "No authorization code."

    # Exchange code for token
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_res = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)

    try:
        token_json = token_res.json()
    except:
        return f"Token error: {token_res.text}"

    access_token = token_json.get("access_token")

    if not access_token:
        return f"OAuth failed: {token_json}"

    # Get user from Discord
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user = user_res.json()

    users = load_users()
    users[user["id"]] = {
        "username": user.get("username"),
        "global_name": user.get("global_name"),
        "access_token": access_token
    }
    save_users(users)

    return f"<h1>Authorized:</h1><pre>{user}</pre>"

@app.route("/users")
def get_users():
    try:
        with open(USERS_PATH, "r") as f:
            data = f.read()
        return data, 200, {"Content-Type": "application/json"}
    except:
        return "{}", 200, {"Content-Type": "application/json"}


# ==========================================
# Discord Bot Section
# ==========================================
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load / Save config.json
def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except:
        return {"guild_id": None}

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)


# ------------------------------------------
# COMMAND: Set the server
# ------------------------------------------
@bot.command(name="setserver")
async def setserver(ctx, guild_id: int):
    cfg = load_config()
    cfg["guild_id"] = guild_id
    save_config(cfg)
    await ctx.send(f"Guild ID set to `{guild_id}`.")


# ------------------------------------------
# COMMAND: Add single user
# ------------------------------------------
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

    url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}"
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    payload = {"access_token": access_token}

    r = requests.put(url, headers=headers, json=payload)

    if r.status_code in (200, 201, 204):
        await ctx.send(f"Added user `{user_id}` successfully.")
    else:
        await ctx.send(f"Failed ({r.status_code}): {r.text}")


# ------------------------------------------
# COMMAND: Add ALL OAuth users
# ------------------------------------------
@bot.command(name="addall")
async def addall(ctx):
    cfg = load_config()
    guild_id = cfg.get("guild_id")

    if guild_id is None:
        await ctx.send("Guild ID not set. Use `!setserver <id>` first.")
        return

    users = load_users()
    success = 0
    fail = 0

    for user_id, data in users.items():
        url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}"
        headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
        payload = {"access_token": data["access_token"]}

        r = requests.put(url, headers=headers, json=payload)

        if r.status_code in (200, 201, 204):
            success += 1
        else:
            fail += 1

    await ctx.send(f"Finished. Success: {success}, Failed: {fail}")


# ==========================================
# Run Flask + Bot Together
# ==========================================
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

def run_bot():
    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    Thread(target=run_bot).start()
