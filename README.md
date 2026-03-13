# DoNotes

AI-powered personal productivity bot that turns voice notes and conversations into organized action.

Send a voice memo, audio recording, or text note via Telegram — DoNotes handles the rest: transcribes with OpenAI Whisper, extracts action items and calendar events with GPT, creates Google Calendar events, logs to Google Sheets, and sends email digests.

## Features

- **Voice & Text Capture** — Send voice memos, audio files, or text notes via Telegram
- **AI Transcription** — Automatic speech-to-text via OpenAI Whisper API
- **Smart Extraction** — GPT analyzes your messages to extract:
  - Action items with deadlines and priorities
  - Calendar events with times, locations, and attendees
  - Commitments (who promised what to whom)
  - People mentioned with roles and context
  - Work vs personal classification
  - Urgency scoring (1-10)
- **Google Calendar** — Auto-creates color-coded events on your work/personal calendars
- **Google Sheets** — Maintains a color-coded tracker spreadsheet with all extracted data
- **Email Digests** — Sends rich HTML digest emails for every processed message
- **Email Composition** — Suggests and auto-composes contextual emails to people mentioned
- **Inline Actions** — Mark action items as done/ignored directly from Telegram buttons
- **Duplicate Detection** — Fuzzy matching prevents duplicate action items
- **Contact Book** — Builds a people graph with roles, relationships, and email addresses
- **macOS Menu Bar App** — Optional native widget to start/stop the bot (macOS only)

## Tech Stack

- **Python 3.9+** with fully async architecture
- **python-telegram-bot** — Telegram bot framework
- **OpenAI** — Whisper (transcription) + GPT-4o (extraction & composition)
- **Google APIs** — Gmail, Calendar, Sheets
- **SQLite** (aiosqlite) — Local database with migration support
- **Pydantic** — Configuration and data validation
- **Jinja2** — HTML email templates

## Prerequisites

- Python 3.9 or higher
- A Telegram account
- An OpenAI API key (with credits)
- A Google Cloud project with Gmail, Calendar, and Sheets APIs enabled

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/NikhiljVIbe/DoNotes.git
cd DoNotes
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 3. Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts to create your bot
3. Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. To find your Telegram user ID, message [@userinfobot](https://t.me/userinfobot)

### 4. Get an OpenAI API Key

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Ensure you have credits/billing configured (Whisper + GPT-4o usage)

### 5. Set Up Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Enable these APIs (search in the API Library):
   - **Gmail API**
   - **Google Calendar API**
   - **Google Sheets API**
4. Go to **APIs & Services** > **Credentials** > **Create Credentials** > **OAuth 2.0 Client ID**
5. If prompted, configure the OAuth consent screen first (External, add your email as test user)
6. Application type: **Desktop app**
7. Download the credentials JSON file
8. Place it in the project:

```bash
mkdir -p data/google_tokens
mv ~/Downloads/client_secret_*.json data/google_tokens/credentials.json
```

9. Run the OAuth setup script:

```bash
python scripts/setup_google_oauth.py
```

This opens a browser window. Sign in with your Google account and authorize Gmail, Calendar, and Sheets access. The token will be saved locally.

> **Note:** If your Google Cloud project is in "Testing" mode, tokens expire every 7 days. You'll need to re-run the setup script when that happens. To avoid this, publish your OAuth consent screen (only your email needs access).

### 6. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable | Description |
|----------|-------------|
| `DONOTES_TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `DONOTES_TELEGRAM_ALLOWED_USER_IDS` | Your Telegram user ID (from @userinfobot) |
| `DONOTES_OPENAI_API_KEY` | OpenAI API key |
| `DONOTES_GMAIL_SENDER_EMAIL` | Your Gmail address |
| `DONOTES_GMAIL_RECIPIENT_EMAIL` | Where to send digests (usually same as sender) |
| `DONOTES_WORK_CALENDAR_ID` | Your work calendar email |
| `DONOTES_PERSONAL_CALENDAR_ID` | Your personal calendar email |
| `DONOTES_TIMEZONE` | Your timezone (e.g., `America/New_York`, `Asia/Kolkata`, `Europe/London`) |
| `DONOTES_USER_NAME` | Your name (used in AI prompts) |

The `DONOTES_GOOGLE_SHEET_ID` is auto-populated on first run.

### 7. Personalize AI Context (Optional)

For better message classification and people recognition:

```bash
cp config/user_profile.example.py config/user_profile.py
```

Edit `config/user_profile.py` with your details — team members, family, frequently mentioned places and companies. This helps the AI:
- Correctly classify work vs personal messages
- Recognize people by name and relationship
- Improve transcription accuracy for names and places
- Avoid suggesting emails to yourself

### 8. Run the Bot

```bash
python __main__.py
```

Send a voice note or text message to your bot on Telegram!

## Optional: macOS Menu Bar App

A native macOS menu bar widget to start/stop the bot:

```bash
pip install -e ".[menubar]"
python -m menubar
```

To build as a standalone `.app`:

```bash
python setup_menubar.py py2app
```

The app will be in `dist/DoNotes.app`.

## Optional: Auto-Start on macOS (launchd)

```bash
cd launchd
bash install.sh
```

This installs a launchd agent that starts the bot automatically on login.

## Project Structure

```
DoNotes/
├── __main__.py              # Bot entry point
├── config/
│   ├── settings.py          # Environment variable configuration
│   ├── prompts.py           # GPT system prompts
│   ├── vocabulary.py        # Whisper vocabulary hints
│   ├── calendars.py         # Calendar ID routing (work vs personal)
│   └── user_profile.example.py  # AI personalization template
├── src/
│   ├── bot/                 # Telegram bot (handlers, callbacks, email flow)
│   ├── ai/                  # OpenAI client, extraction, email composition
│   ├── integrations/        # Gmail, Google Calendar, Sheets, OAuth
│   ├── storage/             # SQLite database, repositories, migrations
│   ├── transcription/       # Whisper API pipeline
│   └── core/                # Message processor, dedup, email suggestions
├── menubar/                 # macOS menu bar app (optional)
├── scripts/                 # Setup scripts (Google OAuth)
├── launchd/                 # macOS auto-start configuration
└── tests/                   # Test suite
```

## How It Works

1. You send a voice note or text to the Telegram bot
2. Audio is transcribed using OpenAI Whisper
3. GPT analyzes the transcript and extracts structured data
4. Results are stored in SQLite and sent back to you on Telegram
5. Calendar events are created in Google Calendar (color-coded by type)
6. A row is appended to your Google Sheets tracker
7. An HTML digest email is sent to your inbox
8. The bot suggests emailing people mentioned, with auto-composed drafts

## License

MIT License. See [LICENSE](LICENSE) for details.
