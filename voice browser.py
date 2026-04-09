import speech_recognition as sr
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

if __name__ == "_main_":
    main()