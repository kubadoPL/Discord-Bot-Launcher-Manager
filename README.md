# 🚀 Discord Bot & Web Services Launcher Manager

A powerful Python platform for managing multiple Discord.py bots **and** modular Flask web services from a single process. It automatically pulls bot repositories from GitHub, organizes them, launches them in parallel, auto-updates on new commits, and hosts a suite of web applications — all deployed on Heroku.

![Bot Launcher Dashboard](https://raw.githubusercontent.com/kubadoPL/Discord-Bot-Launcher-Manager/refs/heads/main/api/templates/Images/bot%20launcher%20new.png)

---

## 🟢 Live Demo

**👉 [https://bot-launcher-discord-017f7d5f49d9.herokuapp.com/](https://bot-launcher-discord-017f7d5f49d9.herokuapp.com/)**

---

## ✨ Features

### 🤖 Bot Launcher (`launcher.py`)
- **Automatic Repository Download**: Fetches private GitHub repos as ZIP archives using token-based authentication.
- **Multi-Bot Parallel Execution**: Runs multiple Discord.py bots in separate subprocesses with real-time log streaming.
- **Auto-Update on Push**: Periodically polls GitHub for new commits (every 60s) and automatically restarts bots when updates are detected.
- **Memory-Optimized**: Reduced thread stack sizes, streaming ZIP downloads (chunked to disk instead of RAM), merged stdout/stderr, and periodic garbage collection — optimized for Heroku's 512MB dynos.
- **Graceful Lifecycle**: Signal handling (`SIGINT`, `SIGTERM`), `atexit` hooks, and timeout-based kill for clean shutdown.
- **Online/Local JSON Config**: Bot definitions loaded from a remote URL with local `bots.json` fallback.

### 🌐 Web App Launcher (`webAppsLauncher.py`)
- **Modular Flask Dispatcher**: Automatically discovers and mounts all Flask apps from the `webApps/` directory under their own URL prefixes (e.g., `/K5ApiManager`, `/DiscordAuthChatApi`).
- **Main Dashboard**: Serves a unified landing page from `api/templates/main.html`.
- **Security Headers**: Adds `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy` to every response.
- **Gevent Support**: Production mode uses gevent monkey-patching for async I/O; served via Gunicorn.
- **CORS**: Enabled globally for cross-service API interaction.

### 📦 Hosted Web Services

#### K5 API Manager (`/K5ApiManager`)
Central API hub providing services for all K5 Studio projects:
- **Discord Bot Status**: Real-time list of running bots with profile info (avatar, username) via Discord API.
- **Spotify / YouTube / Giphy Token Proxy**: Secure server-side token generation with caching and rate limiting.
- **Album Cover Search Engine**: Multi-source search (Spotify, iTunes, Deezer) with Dice-coefficient similarity scoring and in-memory caching.
- **Discord Webhook Relay**: Server-side proxy for "Share to Discord" — keeps webhook URLs private, validates guild membership.
- **Roblox API Proxy**: Game stats proxy (bypasses CORS), asset downloader, user profile & avatar lookup, Bloxlink integration.
- **Steam Workshop Stats**: Fetches subscriber/favorite/view counts for Steam Workshop items.
- **Service Stats API**: Generic CRUD for persistent service statistics (used by portfolio, FormBot, Radio). Public services (e.g., `k5portfolio`) don't require API keys.
- **Server Uptime Endpoint**: Returns uptime in seconds, formatted string, and ISO start timestamp.
- **Running Services Count**: Lists active Discord bots and web services with names.
- **Rate Limiting & Caching**: Per-endpoint rate limits and response caching via Flask-Limiter and Flask-Caching.
- **CORS Restriction**: Configurable origin whitelist (`radio-gaming.stream`, `k5studio.dev`) or open mode.

#### Discord Auth & Chat API (`/DiscordAuthChatApi`)
Full-featured real-time chat backend for [Radio GAMING](https://radio-gaming.stream/):
- **Discord OAuth2**: Login flow with CSRF-protected state tokens, session management, profile fetching (avatar, banner, accent color).
- **Multi-Station Chat**: Separate chat channels per radio station with per-channel message history (100 messages, persisted to MySQL).
- **Custom Emojis**: Upload, store (up to 50), and use custom emoji images in chat. Admin-only deletion.
- **Message Reactions**: Add/remove emoji reactions per message with per-user tracking.
- **Image & Song Sharing**: Attach images (base64, max 2MB) or reference the currently playing song in chat messages.
- **@Mention System**: Mention other users with autocomplete; mentioned users receive cross-station notifications.
- **Online Presence Tracking**: Real-time user presence per station with debounced DB writes (60s intervals). Shows Discord profiles with "last seen" timestamps.
- **Anonymous Listener Stats**: Tracks non-logged-in users with unique IDs. Persists listening time, song history, and favorites to a dedicated `anon_listener_stats` table. Stats can be claimed when user logs in.
- **Global Listener Rankings**: Leaderboard of top listeners by total listening time.
- **Admin Role System**: Configurable admin users with privileges to delete any message or emoji.
- **Background DB Worker**: All database writes are queued and processed by a dedicated background thread (non-blocking API responses).
- **Session Lifecycle**: Periodic cleanup of expired sessions (in-memory + DB), session persistence across server restarts.
- **Deletion Sync**: Recent deletions are tracked for 2 minutes, allowing polling clients to sync removed messages/emojis.

#### Zeno FM Analytics API (`/ZenoFMApi`)
- **Live Listener Count**: Scrapes Zeno FM analytics dashboard via headless Chrome (Selenium) to retrieve per-station listener counts.
- **Singleton Scraping Lock**: Only one Selenium instance runs at a time to conserve memory.
- **Cached Responses**: Results cached for ~8 minutes to minimize scraping overhead.
- **Multi-Station Support**: Supports different Zeno FM accounts per station via environment variables.

#### FormBot – AI Form Auto-filler (`/MSFormsApi`)
- **MS Forms & Google Forms**: Automated form filling via headless Chrome with Selenium.
- **AI-Powered Answers (Gemini)**: Uses Google Gemini (multi-model fallback: 2.5 Flash → 2.5 Flash Lite → 2.0 Flash → 2.0 Flash Lite → 1.5 Flash) to generate coherent, persona-based answers.
- **Persona Generation**: Randomized gender, age, and profession with logical consistency. Custom user prompts supported.
- **Weighted Answer Control**: Users can set per-option weights (including mandatory selections at 95%+) that override AI persona.
- **Browser Queue System**: Managed queue with real-time position updates via Server-Sent Events (SSE). Users see who's ahead and what they're doing.
- **Live Statistics**: Session stats (forms filled/submitted/failed, AI vs random answers) and global persistent stats (saved to MySQL).
- **Online User Tracking**: Heartbeat-based online count with automatic stale session cleanup.
- **Form Preview & Caching**: Scan and cache form questions server-side; preview answers before submission.
- **Short Answers Mode**: Toggle between detailed and brief text responses.
- **API Key Recovery**: If Gemini quota is exhausted, prompts user for a new API key mid-session.

### 🗄️ Database
- **MySQL**: All persistent data stored in MySQL (hosted externally).
  - `api_keys` — API key authentication
  - `users` — Discord/Roblox user balances
  - `chat_messages` — Chat message history with reactions
  - `chat_custom_emojis` — User-uploaded emoji images
  - `chat_user_profiles` — Discord user profiles with last-seen tracking
  - `chat_user_sessions` — OAuth session tokens
  - `user_data` — Generic key-value user data store
  - `anon_listener_stats` — Anonymous listener profiles
  - `service_stats` — Cross-service statistics (visits, forms submitted, etc.)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Heroku Dyno                            │
├──────────────┬──────────────────────────────────────────────┤
│  worker      │  launcher.py                                │
│              │  ├── Downloads & runs Discord bots           │
│              │  └── Auto-updates on GitHub push             │
├──────────────┼──────────────────────────────────────────────┤
│  web         │  webAppsLauncher.py (Gunicorn + Gevent)     │
│              │  ├── / ─────────────── Main Dashboard        │
│              │  ├── /K5ApiManager ─── API Hub               │
│              │  ├── /DiscordAuthChatApi ── Chat Backend     │
│              │  ├── /ZenoFMApi ────── Analytics Scraper     │
│              │  └── /MSFormsApi ───── FormBot               │
└──────────────┴──────────────────────────────────────────────┘
```

---

## ⚙️ Requirements

- **Python** 3.x
- **GitHub** personal access token with repository access
- **MySQL** database (external)
- `requirements.txt` (Flask, Gunicorn, Gevent, Selenium, mysql-connector, google-genai, etc.)

### Environment Variables

| Variable | Description |
|---|---|
| `GitHub_User` | Your GitHub username |
| `GitHub_TOKEN` | GitHub personal access token |
| `ONLINE_JSON_URL` | *(Optional)* URL to remote `bots.json` |
| `DATABASE_HOST/USER/PASSWORD/DATABASE/PORT` | MySQL connection settings |
| `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` | Discord OAuth2 credentials |
| `DISCORD_REDIRECT_URI` | OAuth2 callback URL |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | Spotify API credentials |
| `GIPHY_TOKEN` | Giphy API key |
| `YOUTUBE_DATA_TOKEN` | YouTube Data API key |
| `GEMINI_API_KEY` | Google Gemini API key (FormBot) |
| `ZENOFM_EMAIL_<STATION>` / `ZENOFM_PASSWORD_<STATION>` | Zeno FM credentials per station |
| `WEBHOOK_<GUILD_ID>` | Discord webhook URLs per guild |
| `FLASK_SECRET_KEY` | Flask session secret |
| Bot tokens as defined in `bots.json` | e.g., `SOCIALCREDITBOT_TOKEN`, `GROOVY_TOKEN` |

---

## 🚀 Deployment

### Heroku

The project uses a `Procfile` with two process types:
```
worker: python launcher.py
web: gunicorn -k gevent -w 1 --bind 0.0.0.0:$PORT webAppsLauncher:application
```

### Local Development

```bash
pip install -r requirements.txt
python webAppsLauncher.py   # Starts web services on port 5000
python launcher.py          # Starts bot launcher (separate terminal)
```