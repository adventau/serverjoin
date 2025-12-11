import json
from flask import Flask, request, redirect
import requests
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

app = Flask(__name__)

@app.route("/")
def home():
    return "OAuth App Running. Go to /login to authenticate with Discord."

@app.route("/login")
def login():
    params = (
        f"client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
    )

    return redirect(f"https://discord.com/oauth2/authorize?{params}")

@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return "No authorization code provided."

    # Step 1: Exchange code for access token
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_res = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    token_json = token_res.json()

    access_token = token_json.get("access_token")

    if not access_token:
        return f"Error retrieving access token: {token_json}"

    # Step 2: Fetch user info
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user = user_res.json()

    # Step 3: Save user access token
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
    except:
        users = {}

    users[user["id"]] = {
        "username": user.get("username"),
        "global_name": user.get("global_name"),
        "access_token": access_token
    }

    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

    return f"<h1>Authorized & Saved:</h1><pre>{user}</pre>"

@app.route("/users")
def get_users():
    try:
        with open("users.json", "r") as f:
            data = f.read()
        return data, 200, {"Content-Type": "application/json"}
    except:
        return "{}", 200, {"Content-Type": "application/json"}

# -----------------------
# REQUIRED FOR RENDER
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
