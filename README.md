# Voice Browser - Hands-Free Web Browsing

A Python application that enables voice-controlled web browsing using speech recognition and text-to-speech technology.

## Overview

Voice Browser is a hands-free browsing system that allows users to control web navigation using voice commands. It integrates speech recognition to understand user commands and text-to-speech to provide audio feedback.

## Features

- **Voice-Controlled Navigation**: Search the web and navigate using voice commands
- **Text-to-Speech Feedback**: Audible confirmation of commands and results
- **Web Scraping & Automation**: Automated interaction with web elements
- **Search Integration**: Perform Bing searches directly via voice commands
- **Page Scrolling**: Navigate web pages by voice (scroll up/down)
- **Element Clicking**: Click links and buttons by speaking their names
- **Form Filling**: Automatically fill web forms using voice input
- **Weather Information**: Get current weather updates via voice command
- **Tab Management**: Close browser tabs with voice commands

## Requirements

- Python 3.x
- Microphone (for speech input)
- Speakers (for text-to-speech output)
- Internet connection

## Dependencies

```
speech_recognition
pyttsx3
pyautogui
requests
selenium
webdriver-manager
```

## Installation

1. Install Python dependencies:
```bash
pip install speech_recognition pyttsx3 pyautogui requests selenium webdriver-manager
```

2. Install system audio packages (if needed):
```bash
# On Ubuntu/Debian
sudo apt-get install python3-pyaudio

# On macOS
brew install portaudio
pip install pyaudio
```

## Usage

Run the application:
```bash
python voice\ browser.py
```

### Available Voice Commands

| Command | Action |
|---------|--------|
| "search [query]" / "open [query]" | Search Bing for the given query |
| "scroll down" | Scroll down on the current page |
| "scroll up" | Scroll up on the current page |
| "click [element]" | Click on an element with the specified text |
| "fill [field] [value]" | Fill a form field with the specified value |
| "close tab" | Close the current browser tab |
| "what's the weather" / "what is the weather" | Get current weather information |
| "terminate" | End the voice browser session |

## Architecture

### Main Functions

- **`speak(text)`**: Converts text to speech using pyttsx3
- **`listen_command()`**: Captures and recognizes voice input using Google's speech recognition API
- **`init_browser()`**: Initializes Microsoft Edge WebDriver for automation
- **`search_bing(query)`**: Performs a Bing search for the given query
- **`scroll_page(direction)`**: Scrolls the webpage in the specified direction
- **`click_link_or_button(keyword)`**: Finds and clicks elements by their text content
- **`fill_form(field, value)`**: Fills form input fields with specified values
- **`get_weather()`**: Fetches and announces current weather information

## Technical Stack

- **Speech Recognition**: Google Speech Recognition API
- **Text-to-Speech**: pyttsx3
- **Web Automation**: Selenium WebDriver with Edge browser
- **Browser Control**: pyautogui for keyboard/mouse automation

## Notes

- The application uses Microsoft Edge as the default browser
- Google's Speech Recognition API is used for voice input
- Requires an active internet connection for most features
- Weather information is fetched from wttr.in

## Future Enhancements

- Support for additional browsers (Chrome, Firefox)
- Custom command recognition and voice profiles
- Offline speech recognition
- Local weather caching
- Improved error handling and user feedback
- Support for additional languages

## Troubleshooting

- **"Could not understand the audio"**: Ensure microphone is working and reduce background noise
- **"API unavailable"**: Check internet connection and ensure Google's Speech Recognition API is accessible
- **Browser not opening**: Verify Microsoft Edge is installed and WebDriver is properly configured
- **Audio not playing**: Ensure speakers are working and volume is adjusted

## License

This project is for educational purposes.
