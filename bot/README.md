# Discord Audio Bot (Python)

A Discord bot that plays audio from YouTube in voice channels using commands.

## Setup

1. **Install Python:**
   - Make sure you have Python 3.8 or higher installed
   - Check with: `python --version` or `python3 --version`

2. **Install FFmpeg:**
   - **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **macOS:** `brew install ffmpeg`
   - **Linux:** `sudo apt install ffmpeg`

3. **Install Python dependencies:**
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`
   or
   \`\`\`bash
   pip3 install -r requirements.txt
   \`\`\`

4. **Configure environment variables:**
   - Copy `.env.example` to `.env`
   - Add your Discord bot token

5. **Get Discord Bot Token:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to "Bot" section and create a bot
   - Copy the token and add it to `.env`
   - Enable these Privileged Gateway Intents:
     - Server Members Intent
     - Message Content Intent

6. **Invite bot to your server:**
   - Go to OAuth2 > URL Generator in Discord Developer Portal
   - Select scopes: `bot`
   - Select permissions: `Connect`, `Speak`, `View Channels`, `Send Messages`
   - Copy and open the generated URL

## Running

\`\`\`bash
python play_audio.py
\`\`\`
or
\`\`\`bash
python3 play_audio.py
\`\`\`

## Commands

- `!play <url>` - Play audio from a YouTube URL (you must be in a voice channel)
- `!stop` - Stop playback and disconnect the bot
- `!pause` - Pause the current playback
- `!resume` - Resume paused playback
- `!volume <0-100>` - Change the volume (default is 50)
- `!help` - Show all available commands

## Usage Example

1. Join a voice channel in your Discord server
2. Type: `!play https://www.youtube.com/watch?v=dQw4w9WgXcQ`
3. Bot will join your channel and play the audio

## Requirements

- Python 3.8 or higher
- FFmpeg installed and in PATH
- Discord bot with proper permissions

## Troubleshooting

- **"FFmpeg not found"**: Install FFmpeg and make sure it's in your system PATH
- **Bot doesn't respond**: Check that Message Content Intent is enabled in Discord Developer Portal
- **Can't join voice channel**: Verify the bot has Connect and Speak permissions
- **Login failed**: Double-check your DISCORD_BOT_TOKEN in the `.env` file
