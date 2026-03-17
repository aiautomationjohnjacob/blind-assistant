# Blind Assistant

An AI life companion for blind and visually impaired people.

This assistant can see your screen, help you navigate apps, remember your notes,
order food, book travel, and help with daily tasks — all by voice.

This is a nonprofit, open-source project. The core features are free forever.

---

## Getting Started (Voice-Only Setup)

You do not need to see the screen to set up this assistant.
All setup steps are spoken aloud.

### Step 1: Install Python

You need Python 3.11 or later.

On Windows: Download from python.org. During install, check the box that says
"Add Python to PATH".

On Mac: Open Terminal (or ask someone to open it). Type: brew install python3
and press Enter.

On Linux: Open a terminal. Type: sudo apt install python3 python3-pip
and press Enter.

### Step 2: Install the Setup Voice

Type this command and press Enter:

    pip install pyttsx3

This installs the voice that will guide you through setup.

### Step 3: Run the Setup Wizard

Type this command and press Enter:

    python installer/install.py

The assistant will speak to you and guide you through everything.

### What You Will Need for Setup

1. A Telegram account (free at telegram.org)
2. A Claude API key (free tier available at console.anthropic.com)
3. A passphrase you can remember (for protecting your personal notes)

The setup wizard will tell you how to get each of these.

---

## Using the Assistant After Setup

### Through the App (Primary Interface)

The native app runs on Android, iOS, Windows, and macOS. It uses your device's built-in
screen reader (TalkBack on Android, VoiceOver on iOS and macOS, NVDA or JAWS on Windows)
and adds a conversational AI layer on top.

The app is in active development. Until the native app is released, use the
computer interface below or the Telegram bot (for power users).

### Through the Computer Directly

Type this command and press Enter:

    python -m blind_assistant.main --voice

The assistant will listen through your microphone and speak through your speakers.

Examples of things you can say:
- "What is on my screen right now?"
- "Remember that I have a doctor appointment on Friday at 2pm."
- "What do I have scheduled this week?"
- "Order me a pizza."
- "I want to take a vacation — help me plan one."

### Through Telegram (Power User / Remote Access)

Telegram provides remote access for power users who want to send commands while away
from their main computer. Note: Telegram requires visual setup that some blind users
may need sighted assistance to complete. For independent first-time setup, use the
computer interface above.

Open Telegram on your phone or computer.
Find the bot you created during setup.
Send it a message or a voice message.

---

## Your Personal Notes (Second Brain)

The assistant can remember things for you.
Your notes are stored privately on your device, protected with your passphrase.
They are never sent to any company.

To add a note:
"Remember that I'm allergic to penicillin."
"Add a note: I called the insurance company. Reference number 12345."

To retrieve a note:
"What are my allergies?"
"What did I note about the insurance claim?"
"What medications am I supposed to take?"

---

## Privacy and Security

Your notes are encrypted on your device.
Your passwords and card numbers are never stored in plain text.
Screenshots taken to see your screen are never saved to disk.
Password screens are never sent to any AI service.

Before any purchase is made, the assistant will:
1. Tell you there is risk in sharing financial information with any app
2. Ask you to confirm the exact order and price
3. Only proceed if you say yes

You can delete all your stored information at any time by saying:
"Delete everything I've shared with you."

---

## Accessibility

This assistant is designed for blind users first.
Every feature works entirely by voice.
Text responses are available for braille display users.
Speech rate and verbosity are adjustable.

If something does not work for you, please tell us.
This project is built with the blind community, not just for it.

To report an issue: github.com/blind-assistant/blind-assistant/issues

---

## For Developers

If you want to help build this, see docs/ARCHITECTURE.md for the technical design.

All development follows strict accessibility requirements.
Every feature must be tested by blind user personas before shipping.

This is a nonprofit open-source project.
Contributors of all backgrounds are welcome.
