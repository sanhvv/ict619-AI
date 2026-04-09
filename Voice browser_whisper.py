
import speech_recognition as sr
# Whisper and audio utils
import whisper
import tempfile
import os
import sounddevice as sd
import numpy as np
import scipy.io.wavfile

use_whisper = True  # Will be set by user input

import whisper
import sounddevice as sd
import numpy as np
import scipy.io.wavfile
import tempfile
import os
import queue
import wave
# import webrtcvad

import pyttsx3
import pyautogui
import time
import webbrowser
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager

driver = None

def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def listen_command():
    if use_whisper:
        return listen_command_whisper()
    else:
        return listen_command_google()

def listen_command_google():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening...")
        audio = recognizer.listen(source)
    try:
        command = recognizer.recognize_google(audio).lower()
        print(f"You said: {command}")
        return command
    except sr.UnknownValueError:
        print("❌ Could not understand the audio.")
        return ""
    except sr.RequestError:
        print("⚠️ API unavailable.")
        return ""

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening...")
        audio = recognizer.listen(source)
    try:
        command = recognizer.recognize_google(audio).lower()
        print(f"You said: {command}")
        return command
    except sr.UnknownValueError:
        print("❌ Could not understand the audio.")
        return ""
    except sr.RequestError:
        print("⚠️ API unavailable.")
        return ""

def init_browser():
    global driver
    options = webdriver.EdgeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)

def search_bing(query):
    init_browser()
    driver.get(f"https://www.bing.com/search?q={query}")

def scroll_page(direction):
    if direction == "down":
        pyautogui.scroll(-800)
    elif direction == "up":
        pyautogui.scroll(800)

def click_link_or_button(keyword):
    try:
        elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
        for element in elements:
            if element.is_displayed() and element.is_enabled():
                print(f"✅ Clicking element with text: {element.text}")
                element.click()
                return
        print("❌ No clickable element found.")
    except Exception as e:
        print(f"⚠️ Error while clicking: {e}")

def fill_form(field, value):
    try:
        input_fields = driver.find_elements(By.TAG_NAME, 'input')
        for field_element in input_fields:
            name = field_element.get_attribute("name")
            if name and field.lower() in name.lower():
                field_element.clear()
                field_element.send_keys(value)
                print(f"✅ Filled '{field}' with '{value}'")
                return
        print("❌ Form field not found.")
    except Exception as e:
        print(f"⚠️ Error while filling form: {e}")

def get_weather():
    try:
        response = requests.get("https://wttr.in/?format=3")
        speak(f"The weather is {response.text}")
    except:
        speak("Sorry, I couldn't fetch the weather information.")


def choose_model():
    global use_whisper
    speak("Which speech model do you want to use? Say Whisper or Google")
    choice = listen_command_google()  # Always use Google model for initial choice
    if "whisper" in choice:
        use_whisper = True
        speak("Whisper model activated")
    else:
        use_whisper = True
        speak("Google model activated")


def main():
    speak("Hello hope you are doing good, you have activated hands free browsing system, give me command what you want to browse")
    while True:
        command = listen_command() 
        if not command:
            continue
        if "search" in command or "open" in command:
            query = command.replace("search", "").replace("open", "").strip()
            speak(f"Searching for {query}")
            search_bing(query)
        elif "scroll down" in command:
            scroll_page("down")
        elif "scroll up" in command:
            scroll_page("up")
        elif "click" in command:
            keyword = command.replace("click", "").strip()
            speak(f"Trying to click {keyword}")
            click_link_or_button(keyword)
        elif "fill" in command:
            try:
                parts = command.split()
                field = parts[1]
                value = " ".join(parts[2:])
                fill_form(field, value)
            except:
                print("❌ Could not parse form fill command.")
        elif "close tab" in command:
            pyautogui.hotkey("ctrl", "w")
        elif "what's the weather" in command or "what is the weather" in command:
            get_weather()
        elif "terminate" in command:
            speak("Thank you for using me.")
            break

if __name__ == "__main__":
    main()



def record_with_vad(duration=10, aggressiveness=2):
    import collections
    import sys
    import threading
    import time

    FORMAT = 'int16'
    CHANNELS = 1
    RATE = 16000
    FRAME_DURATION = 30  # ms
    FRAME_SIZE = int(RATE * FRAME_DURATION / 1000)
    FRAMES_PER_BUFFER = FRAME_SIZE

    vad = webrtcvad.Vad(aggressiveness)
    ring_buffer = collections.deque(maxlen=10)
    triggered = False

    audio = []
    start_time = time.time()

    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(status)
        q.put(bytes(indata))

    with sd.RawInputStream(samplerate=RATE, blocksize=FRAMES_PER_BUFFER, dtype=FORMAT,
                           channels=CHANNELS, callback=callback):
        while True:
            frame = q.get()
            if vad.is_speech(frame, RATE):
                if not triggered:
                    triggered = True
                    print("🎙️ Speech started...")
                ring_buffer.clear()
                audio.append(frame)
            else:
                if triggered:
                    ring_buffer.append(frame)
                    if len(ring_buffer) > 3:
                        print("⏹️ Speech ended.")
                        break
                else:
                    ring_buffer.append(frame)
            if time.time() - start_time > duration:
                print("⌛ Max recording time reached.")
                break
    return b''.join(audio)

def listen_command_whisper():
    speak("Listening using Whisper with silence detection...")
    audio_data = record_with_vad()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    with wave.open(temp_file.name, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_data)

    model = whisper.load_model("base")
    result = model.transcribe(temp_file.name)
    os.unlink(temp_file.name)
    text = result["text"].strip().lower()
    print(f"🗣️ Whisper heard: {text}")
    return text

    fs = 44100
    duration = 5
    speak("Listening using Whisper...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    scipy.io.wavfile.write(temp_file.name, fs, recording)
    model = whisper.load_model("base")
    result = model.transcribe(temp_file.name)
    os.unlink(temp_file.name)
    print(f"Whisper heard: {result['text']}")
    return result['text'].lower()
