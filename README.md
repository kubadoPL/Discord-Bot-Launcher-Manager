# Discord Bot Launcher Manager

A Python script for managing multiple Discord.py bots by downloading their repositories from GitHub, extracting them, and running them.

## Features
- Fetch bot configurations from an online JSON or a local `bots.json` file.
- Download private repositories from GitHub using authentication.
- Automatically extract and organize bot files.
- Start multiple bots in parallel while handling logging and errors.
- Gracefully stop all bots on exit.
- Update Bot that recieved new pushed commit.
- API enabling interaction with the databases used by bots from anywhere.
- Support for Discord and Roblox accounts API.
- Web panel that works with API.

## Requirements
- Python 3.x
- GitHub personal access token with repository access
- Environment variables:
  - `GitHub_User`: Your GitHub username
  - `GitHub_TOKEN`: Your GitHub personal access token
  - `ONLINE_JSON_URL`: (Optional) URL to a remote `bots.json` configuration file
  - Additional environment variables for bot tokens as defined in `bots.json`


## Check Launcher Webpage!
https://bot-launcher-discord-017f7d5f49d9.herokuapp.com/

<img src="https://raw.githubusercontent.com/kubadoPL/Discord-Bot-Launcher-Manager/refs/heads/main/api/templates/Images/bot%20launcher.png" width="auto" height="auto">