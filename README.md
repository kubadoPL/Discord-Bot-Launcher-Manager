# Discord Bot Launcher

A Python script for managing multiple Discord bots by downloading their repositories from GitHub, extracting them, and running them.

## Features
- Fetch bot configurations from an online JSON or a local `bots.json` file.
- Download private repositories from GitHub using authentication.
- Automatically extract and organize bot files.
- Start multiple bots in parallel while handling logging and errors.
- Gracefully stop all bots on exit.

## Requirements
- Python 3.x
- GitHub personal access token with repository access
- Environment variables:
  - `GitHub_User`: Your GitHub username
  - `GitHub_TOKEN`: Your GitHub personal access token
  - `ONLINE_JSON_URL`: (Optional) URL to a remote `bots.json` configuration file
  - Additional environment variables for bot tokens as defined in `bots.json`
