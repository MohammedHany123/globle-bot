# 🌍 Globle Discord Bot

A Discord bot that lets you play a geography guessing game with friends! The bot thinks of a country, and you try to guess it. You'll get "hot" or "cold" feedback based on how close your guesses are to the target country.

**🗺️ Beautiful Maps:** After every guess, see a realistic OpenStreetMap with entire countries smoothly colored by temperature! Hot guesses glow red/orange, cold guesses turn blue.

## 🎮 How to Play

1. Start a game with `/start`
2. Make guesses with `/guess [country name]`
3. The bot tells you:
   - How far away your guess is from the target country
   - If you're getting HOTTER (closer) or COLDER (farther) than your last guess
   - Temperature feedback: 🔥 (hot/close) or ❄️ (cold/far)
4. Keep guessing until you find the right country!

## 📋 Commands

- `/start` - Start a new game
- `/guess [country]` - Make a guess (e.g., `/guess France`)
- `/hint` - Get a hint about the target country
- `/stats` - Show current game statistics
- `/surrender` - Give up and reveal the answer

## 🛠️ Setup Instructions

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
5. Click "Reset Token" and copy your bot token (you'll need this!)

### 2. Install the Bot

1. Clone or download this repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Chrome/Chromium and ChromeDriver (required for map generation):
   - **Ubuntu/Debian:**
     ```bash
     sudo apt-get update
     sudo apt-get install chromium-chromedriver
     ```
   - **macOS:**
     ```bash
     brew install --cask chromedriver
     ```
   - **Windows:** Download [ChromeDriver](https://chromedriver.chromium.org/) and add to PATH

4. Create a `.env` file in the project directory:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_actual_bot_token_here
   ```

### 3. Invite Bot to Your Server

1. Go back to the Discord Developer Portal
2. Go to "OAuth2" → "URL Generator"
3. Select scopes:
   - `bot`
   - `applications.commands`
4. Select bot permissions:
   - Send Messages
   - Embed Links
   - Read Message History
5. Copy the generated URL and open it in your browser
6. Select your server and authorize the bot

### 4. Run the Bot

```bash
python bot.py
```

You should see: "Bot has connected to Discord!"

## 🎯 Game Features

- **🗺️ Stunning Realistic Maps**: Beautiful OpenStreetMap visualization!
  - Entire countries smoothly colored based on temperature
  - Red/orange countries = hot (close to target)
  - Blue countries = cold (far from target)
  - Unguessed countries shown in light gray
  - Real country borders and shapes
  - Modern, polished legend with gradients

- **Hot & Cold Feedback**: Distance-based temperature indicators
  - 🔥🔥🔥 < 500 km (BURNING HOT!)
  - 🔥🔥 < 1000 km (Very Hot)
  - 🔥 < 2500 km (Hot)
  - 🌡️ < 5000 km (Warm)
  - ❄️ < 7500 km (Cool)
  - ❄️❄️ < 10000 km (Cold)
  - ❄️❄️❄️ > 10000 km (FREEZING!)

- **Trend Tracking**: Know if you're getting closer or farther
- **Multiple Players**: Track who's playing in each game
- **Hints System**: Get clues about continent, capital, and hemisphere
- **Statistics**: See guess counts and closest attempts

## 📁 Files

- `bot.py` - Main Discord bot code
- `game.py` - Game logic and distance calculations
- `map_generator.py` - Beautiful map rendering with Folium + OpenStreetMap
- `countries.json` - Database of 195 countries with coordinates
- `requirements.txt` - Python dependencies (folium, selenium)
- `.env` - Your bot token (create this file)

## 🧮 How It Works

The bot uses the **Haversine formula** to calculate the great-circle distance between capital cities. This gives accurate distances accounting for the Earth's curvature.

**Beautiful Map Visualization**: 
- Uses **Folium** with **OpenStreetMap** tiles for realistic geography
- Loads real country GeoJSON shapes from world.geo.json
- Colors entire countries with smooth gradients based on distance
- Converts HTML map to PNG using Selenium + Chrome
- Professional legend with modern styling

## 🔒 Security Note

Never share your `.env` file or bot token! The `.env` file is gitignored to keep your token safe.

## 🐛 Troubleshooting

**Bot doesn't respond:**
- Make sure Message Content Intent is enabled in Discord Developer Portal
- Check that the bot has permission to send messages in your channel

**"Module not found" errors:**
- Run `pip install -r requirements.txt`

**Bot disconnects:**
- Check your internet connection
- Verify your bot token is correct in `.env`

## 🎉 Have Fun!

Enjoy playing Globle with your friends! May the best geographer win! 🌍
