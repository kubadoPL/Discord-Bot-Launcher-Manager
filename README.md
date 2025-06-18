# Discord Bot Launcher Manager

A powerful Python tool for managing multiple Discord.py bots. Automatically pulls bot repositories from GitHub, organizes them, and launches them—all with support for an API and a Web Control Panel.

## 🚀 Features
-Fetch bot configurations from an online JSON or local bots.json.
-Download private repositories from GitHub with authentication.
-Automatically extract and organize bot files.
-Start and manage multiple bots in parallel.
-Real-time logging and error tracking.
-Gracefully stop all bots on exit.
-Automatically update bots when new commits are pushed.
-API access to interact with each bot’s data and controls.
-Support for Discord and Roblox account APIs.
-Modern Web Control Panel (Flask-based) to monitor and manage everything.

## 🌐 Web App Launcher
Our project includes a modular Flask web app launcher, letting you run multiple web tools side-by-side under one host using a single Python process.

## ✔️ Key Web Launcher Features
-A main dashboard (/) served from api/templates/main.html.
-Auto-detection and loading of Python files from the webApps/ directory.
-Each sub-app must define a Flask app object.
-All apps are accessible under paths like /status, /logs, etc.
-CORS enabled for API interaction across services.

## Requirements
- Python 3.x
- GitHub personal access token with repository access
- requirements.txt
- Environment variables:
  - `GitHub_User`: Your GitHub username
  - `GitHub_TOKEN`: Your GitHub personal access token
  - `ONLINE_JSON_URL`: (Optional) URL to a remote `bots.json` configuration file
  - Additional environment variables for bot tokens as defined in `bots.json`

## 📁 Example Structure
<details>
project/
├── webAppsLauncher.py # Main WebApp launcher script
├── launcher.py # Main Bot launcher script
├── api/
│ ├── templates/
│ │ └── main.html # Main dashboard UI
│ ├── config.py # Config for Custom API
│ └── FunctionsModule.py # Functionality script for API
│
├── webApps/
│ ├── something.py # Flask app
│ └── something.py # Flask app
├── bots/ # Folder where bots are downloaded
└── bots.json # Configuration file

</details>
## 🟢 Live Demo on Heroku
https://bot-launcher-discord-017f7d5f49d9.herokuapp.com/

<img src="https://raw.githubusercontent.com/kubadoPL/Discord-Bot-Launcher-Manager/refs/heads/main/api/templates/Images/launcher%20web%20panel.png" width="auto" height="auto">