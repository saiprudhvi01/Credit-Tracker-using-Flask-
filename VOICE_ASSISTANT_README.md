# Voice Assistant for Shop Credit Tracker

A continuous voice assistant that listens for commands and automates tasks in the Shop Credit Tracker application.

## Features

- Continuous voice listening
- Add credits via voice: "Add credit for Ravi 500"
- Add payments via voice: "Add payment for Suresh 1000"
- Automatic command parsing and execution
- Clean, modular code separate from main app

## Installation

1. Install required dependencies:
```bash
pip install SpeechRecognition pyaudio requests
```

**Note for Windows users:** PyAudio may require additional installation:
```bash
pip install pipwin
pipwin install pyaudio
```

## Usage

1. Start the Flask app first:
```bash
python app.py
```

2. In a separate terminal, start the voice assistant:
```bash
python voice_assistant.py
```

3. Log in to the web app at http://localhost:5000

4. Speak commands:
   - "Add credit for Ravi 500"
   - "Add payment for Suresh 1000"
   - "Stop" to exit the assistant

## Voice Commands

### Transaction Commands
- "Add credit for [name] [amount]" - Record a credit (customer owes you)
- "Add payment for [name] [amount]" - Record a payment (customer paid you)
- "Gave credit for [name] [amount]" - Alternative for credit
- "Got payment for [name] [amount]" - Alternative for payment

### Control Commands
- "Stop" - Stop the voice assistant
- "Exit" - Stop the voice assistant
- "Quit" - Stop the voice assistant

## How It Works

1. The voice assistant continuously listens for voice input
2. When it detects speech, it converts speech to text
3. It parses the text to identify the command type, customer name, and amount
4. It makes API calls to the Flask app to execute the action
5. The transaction is saved to the database automatically

## Architecture

- `voice_assistant.py` - Standalone voice assistant module
- `app.py` - Flask app with API endpoints for voice assistant
- API endpoints:
  - `/api/customers` - Get list of customers
  - `/api/transaction` - Add a new transaction

## Troubleshooting

**Microphone not detected:**
- Ensure your microphone is connected and working
- Check system audio settings

**SpeechRecognition errors:**
- Ensure you have an internet connection (uses Google Speech API)
- Try speaking more clearly

**PyAudio installation issues (Windows):**
- Use pipwin: `pip install pipwin && pipwin install pyaudio`
- Or download from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

## Notes

- The assistant requires the Flask app to be running
- You must be logged in to the web app for voice commands to work
- Commands are case-insensitive
- The assistant runs in a continuous loop until stopped
