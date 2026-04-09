import re
import speech_recognition as sr
import pyttsx3
import time
import os
import tempfile
import whisper
import numpy as np
import sounddevice as sd
import scipy.io.wavfile
import imageio_ffmpeg
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
### using for Chrome browser
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
###
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException, WebDriverException, InvalidElementStateException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from urllib.parse import quote, urlparse
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from transformers import pipeline
from sentence_transformers import SentenceTransformer, util
from bs4 import BeautifulSoup
import gc
import tkinter as tk
from tkinter import ttk
import threading

# Global variables
driver = None
listening_active = False
model = None
temp_dir = tempfile.gettempdir()
ACTIVATION_WORD = "activate"
form_mode = False
current_domain = None
command_history = []
custom_form_data = {}
gui = None
start_button = None
stop_button = None

# Initialize Whisper model for speech recognition (force CPU)
def load_whisper_model(model_size="base"):
    global model
    try:
        ffmpeg_path = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
        os.environ["PATH"] += os.pathsep + ffmpeg_path
        print(f"✅ FFmpeg path set to: {ffmpeg_path}")
    except Exception as e:
        print(f"⚠️ FFmpeg configuration warning: {e}")
        print("⚠️ Will attempt to use system FFmpeg")
    
    print(f"🔄 Loading Whisper {model_size} model...")
    try:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Disable GPU
        model = whisper.load_model(model_size, device="cpu")
        print("✅ Whisper model loaded successfully on CPU!")
        gc.collect()
    except Exception as e:
        print(f"⚠️ Error loading Whisper model: {e}")
        speak("I had trouble loading the speech recognition model. Voice commands may not work properly.")

# Text-to-speech function
def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)
    engine.say(text)
    engine.runAndWait()

# Initialize Microsoft Edge browser
def init_browser():
    global driver
    if is_browser_alive():
        return True
    try:
        print("🔄 Setting up Microsoft Edge browser...")
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--inprivate")
        options.add_argument("--disable-notifications")
        # edge_service = EdgeService(EdgeChromiumDriverManager().install())
        # driver = webdriver.Edge(service=edge_service, options=options)
        # Chrome browser
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Nếu bạn muốn chạy headless
        options.add_argument("--disable-gpu")  # (Tùy chọn) giúp ổn định hơn
        options.add_argument("--no-sandbox")  # Nếu chạy trên Linux server

        edge_service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=chrome_service, options=options)
        ###
        driver.implicitly_wait(5)
        print("✅ Microsoft Edge browser successfully initialized!")
        update_current_domain()
        return True
    except Exception as e:
        print(f"❌ Browser initialization error: {e}")
        speak("I couldn't start the web browser. Please check if Microsoft Edge is installed.")
        return False

# Check if browser is alive
def is_browser_alive():
    global driver
    try:
        if driver is None:
            return False
        driver.current_url
        return True
    except:
        driver = None
        return False

# Update current domain
def update_current_domain():
    global current_domain
    try:
        current_url = driver.current_url
        current_domain = urlparse(current_url).netloc
        print(f"🌐 Current domain: {current_domain}")
    except:
        current_domain = None

# Record audio with optimized settings
def record_audio(duration=5, fs=16000):
    print("🎙️ Recording... Speak now. (Sample rate: 16kHz)")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    amplitude = np.max(np.abs(recording))
    sd.wait()
    return recording, fs, amplitude

# Save audio to WAV file
def save_to_wav(audio, fs):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    scipy.io.wavfile.write(temp_file.name, fs, audio)
    return temp_file.name

# Transcribe audio using Whisper with relaxed garble check
def transcribe_audio(path, max_retries=2):
    print("🧠 Transcribing...")
    for attempt in range(max_retries):
        try:
            result = model.transcribe(path)
            text = result["text"].lower()
            if not text or (len(text.split()) < 2 and ACTIVATION_WORD not in text and "click" not in text and "search" not in text):
                raise ValueError("Possible transcription garble detected")
            print(f"🔊 Raw transcription attempt {attempt + 1}: {text}")
            print(f"🔊 Command: {text}")
            return text
        except Exception as e:
            print(f"⚠️ Transcription attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                print("❌ Transcription failed after retries")
                speak("I couldn't understand your command. Please speak clearly and try again, or check your microphone.")
                return ""
            time.sleep(1)
    return ""

# Initialize pretrained NLP models (force CPU)
def load_nlp_models():
    global classifier, embedder
    try:
        print("🔄 Loading BART for intent classification...")
        os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Disable GPU
        classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
        print("✅ BART loaded successfully on CPU!")
        gc.collect()
        
        print("🔄 Loading sentence transformer for semantic matching...")
        embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        print("✅ Sentence transformer loaded successfully on CPU!")
        gc.collect()
    except Exception as e:
        print(f"⚠️ Error loading NLP models: {e}")
        speak("I had trouble loading the language models. Using fallback mode for command processing.")
        classifier = None
        embedder = None

# Handle pop-ups on Amazon
def dismiss_amazon_popups():
    try:
        signin_popup = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "nav-signin-tooltip"))
        )
        if signin_popup:
            driver.execute_script("arguments[0].style.display = 'none';", signin_popup)
            print("✅ Dismissed sign-in pop-up")
    except TimeoutException:
        pass

    try:
        location_popup = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "nav-global-location-popover-link"))
        )
        if location_popup:
            driver.execute_script("arguments[0].style.display = 'none';", location_popup)
            print("✅ Dismissed location pop-up")
    except TimeoutException:
        pass

    try:
        modal_close = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'a-button-close')]"))
        )
        modal_close.click()
        print("✅ Dismissed generic modal")
    except TimeoutException:
        pass

    try:
        cookie_accept = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "sp-cc-accept"))
        )
        cookie_accept.click()
        print("✅ Accepted cookies")
    except TimeoutException:
        pass

    try:
        promo_popup = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'a-popover')]//button[contains(@class, 'a-button-close')]"))
        )
        promo_popup.click()
        print("✅ Dismissed promotional pop-up")
    except TimeoutException:
        pass

# Dynamic element locator with semantic matching and navigation bar support
def find_element_dynamic(driver, target, element_type=None, max_attempts=2, nav_bar=False):
    target_cleaned = target.lower().strip()
    if not any(x in target for x in [".com", ".org", ".net", "www."]):
        target_cleaned = re.sub(r'[^\w\s\']', '', target_cleaned)
    print(f"🔍 Searching for element: '{target_cleaned}' (type: {element_type or 'any'}, nav_bar: {nav_bar})")
    
    position = None
    if any(pos in target for pos in ["first", "second", "third"]):
        position_map = {"first": 0, "second": 1, "third": 2}
        for pos_name, pos_index in position_map.items():
            if pos_name in target:
                position = pos_index
                if "video" in target:
                    target_cleaned = "video"
                elif "link" in target or "result" in target:
                    target_cleaned = "link"
                break
    
    if "video" in target and current_domain == "www.youtube.com" and not element_type:
        element_type = "video"
    elif "search" in target:
        element_type = "input"
    elif "button" in target or "submit" in target:
        element_type = "button"
    elif any(x in target for x in [".com", ".org", ".net", "www."]) or target in ["google", "youtube", "facebook", "twitter", "reddit", "wikipedia"]:
        element_type = "link"
    else:
        element_type = "link"

    selectors = []
    if nav_bar:
        selectors.extend([
            f"//nav//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{target_cleaned}') and @href]",
            f"//nav//li[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{target_cleaned}')]/a[@href]",
            f"//div[contains(@class, 'nav') or contains(@class, 'navbar')]//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{target_cleaned}') and @href]",
            "//nav//a[@href]"
        ])
    elif element_type == "video" and current_domain == "www.youtube.com":
        selectors.extend([
            "//a[@id='thumbnail']",
            "//a[contains(@class, 'yt-simple-endpoint') and contains(@class, 'ytd-thumbnail')]",
            "//a[contains(@href, '/watch?v=')]",
            "//video",
            "//a[contains(@href, 'video')]"
        ])
    elif element_type == "input":
        selectors.extend([
            "//input[@type='text']",
            "//input[@type='search']",
            "//input[@name='q']",
            "//input[@name='search']",
            "//textarea"
        ])
    elif element_type == "button":
        selectors.extend([
            "//button",
            "//input[@type='submit']",
            "//input[@type='button']",
            "//a[contains(@class, 'button')]",
            "//button[contains(text(), 'Send') or contains(text(), 'Confirm')]"
        ])
    elif element_type == "link":
        selectors.extend([
            f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{target_cleaned}') and @href]",
            "//a[@href and contains(@href, 'youtube.com')]",
            "//a[@href]"
        ])

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    all_elements = soup.find_all(['a', 'button', 'input', 'select', 'textarea', 'div', 'img'])
    element_texts = [(elem, re.sub(r'\s+', ' ', elem.get_text(strip=True).lower() or elem.get('aria-label', '').lower() or elem.get('title', '').lower())) for elem in all_elements if elem.name == 'a' and elem.get('href')]
    
    best_element = None
    best_href = None
    if target_cleaned and embedder:
        target_embedding = embedder.encode(target_cleaned, convert_to_tensor=True)
        element_embeddings = embedder.encode([text for _, text in element_texts if text], convert_to_tensor=True)
        if element_embeddings.shape[0] > 0:
            similarities = util.cos_sim(target_embedding, element_embeddings)[0]
            max_similarity_idx = similarities.argmax().item()
            print(f"🔍 Similarity scores: {[f'{s:.2f}' for s in similarities.tolist()]}")
            if similarities[max_similarity_idx] > 0.5:
                best_element = element_texts[max_similarity_idx][0]
                best_href = best_element.get('href')
                try:
                    element = driver.find_element(By.XPATH, f"//a[@href='{best_href}']")
                    WebDriverWait(driver, 2).until(EC.visibility_of(element))
                    size = element.size
                    location = element.location
                    print(f"✅ Element verified: size={size}, location={location}")
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                    time.sleep(0.3)
                    print(f"✅ Found element via semantic match: '{target_cleaned}' (href: {best_href}, text: {best_element.get_text(strip=True)})")
                    return element, best_href
                except:
                    pass
    
    start_time = time.time()
    max_total_time = 15
    for attempt in range(max_attempts):
        if time.time() - start_time > max_total_time:
            print("⚠️ Search timed out after 15 seconds")
            break
        for selector in selectors:
            try:
                elements = WebDriverWait(driver, 3).until(
                    EC.presence_of_all_elements_located((By.XPATH, selector))
                )
                visible_elements = [e for e in elements if e.is_displayed() and e.is_enabled()]
                if visible_elements:
                    print(f"🔍 Found {len(visible_elements)} visible elements: {[e.text.strip() for e in visible_elements]}")
                    for element in visible_elements:
                        element_text = re.sub(r'\s+', ' ', element.text.lower().strip())
                        if target_cleaned in element_text or f"{target_cleaned} " in element_text or f" {target_cleaned}" in element_text:
                            WebDriverWait(driver, 2).until(EC.visibility_of(element))
                            size = element.size
                            location = element.location
                            print(f"✅ Exact match found: '{element_text}' (size={size}, location={location})")
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                            time.sleep(0.3)
                            href = element.get_attribute('href')
                            print(f"✅ Found element: '{target_cleaned}' (href: {href})")
                            return element, href
                    
                    if not best_element and target_cleaned and embedder:
                        element_texts = []
                        for e in visible_elements:
                            e_text = re.sub(r'\s+', ' ', (e.text.lower().strip() or e.get_attribute('aria-label') or e.get_attribute('title') or '').lower())
                            if e_text:
                                element_texts.append((e, e_text))
                        if element_texts:
                            element_embeddings = embedder.encode([text for _, text in element_texts], convert_to_tensor=True)
                            similarities = util.cos_sim(target_embedding, element_embeddings)[0]
                            max_similarity_idx = similarities.argmax().item()
                            if similarities[max_similarity_idx] > 0.5:
                                element, matched_text = element_texts[max_similarity_idx]
                                print(f"✅ Selected element via semantic match: {matched_text} (score: {similarities[max_similarity_idx]:.2f})")
                                WebDriverWait(driver, 2).until(EC.visibility_of(element))
                                size = element.size
                                location = element.location
                                print(f"✅ Element verified: size={size}, location={location}")
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                                time.sleep(0.3)
                                href = element.get_attribute('href')
                                print(f"✅ Found element: '{target_cleaned}' (href: {href})")
                                return element, href
                            else:
                                print(f"⚠️ No semantic match above threshold for '{target_cleaned}'")
                        else:
                            print(f"⚠️ No valid element texts found for semantic matching")
                    
                    element = visible_elements[0]
                    element_text = re.sub(r'\s+', ' ', element.text.lower().strip())
                    print(f"✅ Selected first visible element: {element_text}")
                    WebDriverWait(driver, 2).until(EC.visibility_of(element))
                    size = element.size
                    location = element.location
                    print(f"✅ Element verified: size={size}, location={location}")
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                    time.sleep(0.3)
                    href = element.get_attribute('href')
                    print(f"✅ Found element: '{target_cleaned}' (href: {href})")
                    return element, href
            except TimeoutException:
                print(f"⚠️ No elements found for selector: {selector}")
                continue
            except Exception as e:
                print(f"⚠️ Error searching for elements with selector {selector}: {e}")
                continue
    
    print(f"❌ Could not find element: '{target_cleaned}'")
    return None, None

# Enhanced form field detector to handle any form
def analyze_form_dynamic(driver, timeout=5):
    print("📋 Analyzing form fields dynamically...")
    form_elements = {}
    
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input, select, textarea, button"))
        )
        elements = driver.find_elements(By.CSS_SELECTOR, "input, select, textarea, button")
        for element in elements:
            if not element.is_displayed() or not element.is_enabled():
                continue
            
            field_name = None
            element_id = element.get_attribute("id")
            element_name = element.get_attribute("name")
            element_type = element.get_attribute("type") or "text"
            element_placeholder = element.get_attribute("placeholder")
            
            try:
                if element_id:
                    label = driver.find_element(By.CSS_SELECTOR, f"label[for='{element_id}']")
                    field_name = label.text.strip().lower()
            except:
                pass
            
            if not field_name:
                field_name = (element_placeholder or element_name or element_id or "").replace("_", " ").lower()
                field_name = re.sub(r'^\d+', '', field_name).strip()
                field_name = re.sub(r'\s+', ' ', field_name)
                if not field_name and element.tag_name in ["input", "select", "textarea"]:
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    parent = soup.find(lambda tag: tag.name in ["div", "span", "p", "label"] and (element.get_attribute("name") or element.get_attribute("id")) in tag.text.lower())
                    if parent:
                        field_name = re.sub(r'\s+', ' ', parent.text.lower().strip())
                        field_name = re.sub(r'^\d+', '', field_name).strip()
            
            if field_name:
                form_elements[field_name] = {
                    "element": element,
                    "type": element_type if element.tag_name == "input" else element.tag_name,
                    "id": element_id,
                    "name": element_name,
                    "options": [opt.text for opt in Select(element).options] if element.tag_name == "select" else None
                }
                print(f"🔍 Detected field: {field_name} (type: {element_type}, id: {element_id}, name: {element_name})")
        
        print(f"✅ Identified {len(form_elements)} form fields")
        return form_elements
    except Exception as e:
        print(f"⚠️ Form analysis error: {e}")
        return {}

# Enhanced form field filler to handle any input type
def fill_field_dynamic(driver, field_name, value):
    form_elements = analyze_form_dynamic(driver)
    field_name = field_name.lower().strip()
    
    if not form_elements:
        print(f"❌ No form fields detected for '{field_name}'")
        return False
    
    if field_name in form_elements:
        element_info = form_elements[field_name]
        element = element_info["element"]
        element_type = element_info["type"]
        
        try:
            if element_type in ["text", "email", "tel", "textarea"]:
                element.clear()
                element.send_keys(value)
                print(f"✅ Filled '{field_name}' with '{value}'")
                return True
            elif element_type == "select":
                select = Select(element)
                try:
                    select.select_by_visible_text(value)
                    print(f"✅ Selected '{value}' for '{field_name}'")
                    return True
                except:
                    options = element_info["options"] or [opt.text for opt in select.options]
                    for option in options:
                        if value.lower() in option.lower():
                            select.select_by_visible_text(option)
                            print(f"✅ Selected '{option}' for '{field_name}' (matched '{value}')")
                            return True
                    select.select_by_index(0)
                    print(f"⚠️ Value '{value}' not found, selected first option for '{field_name}'")
                    return True
            elif element_type in ["checkbox", "radio"]:
                if value.lower() in ["yes", "true", "on", "check", "1"]:
                    if not element.is_selected():
                        element.click()
                        print(f"✅ Checked '{field_name}'")
                    else:
                        print(f"ℹ️ '{field_name}' already checked")
                    return True
                elif value.lower() in ["no", "false", "off", "uncheck", "0"]:
                    if element.is_selected():
                        element.click()
                        print(f"✅ Unchecked '{field_name}'")
                    else:
                        print(f"ℹ️ '{field_name}' already unchecked")
                    return True
            elif element_type == "password":
                element.clear()
                element.send_keys(value)
                print(f"✅ Filled password '{field_name}' with '{value}'")
                return True
            elif element_type == "button" and "submit" in field_name:
                element.click()
                print(f"✅ Clicked submit button '{field_name}'")
                return True
            else:
                print(f"⚠️ Unsupported element type '{element_type}' for '{field_name}'")
                return False
        except Exception as e:
            print(f"⚠️ Error filling '{field_name}': {e}")
            return False
    
    if embedder:
        field_names = list(form_elements.keys())
        if field_names:
            field_embeddings = embedder.encode(field_names, convert_to_tensor=True)
            target_embedding = embedder.encode(field_name, convert_to_tensor=True)
            similarities = util.cos_sim(target_embedding, field_embeddings)[0]
            max_similarity_idx = similarities.argmax().item()
            if similarities[max_similarity_idx] > 0.3:
                best_field = field_names[max_similarity_idx]
                print(f"✅ Semantic match: '{field_name}' mapped to '{best_field}' (score: {similarities[max_similarity_idx]:.2f})")
                return fill_field_dynamic(driver, best_field, value)
    
    print(f"❌ No matching field found for '{field_name}'")
    return False

# Auto-fill form with sample or custom data
def autofill_form_dynamic(driver):
    form_elements = analyze_form_dynamic(driver)
    if not form_elements:
        print("⚠️ No form elements detected")
        return False
    
    if custom_form_data:
        data = custom_form_data.items()
    else:
        data = [
            ("name", "John Smith"),
            ("first name", "John"),
            ("last name", "Smith"),
            ("email", "john.smith@example.com"),
            ("phone", "617-555-1234"),
            ("address", "123 Main Street"),
            ("city", "Boston"),
            ("state", "Massachusetts"),
            ("zip", "02108"),
            ("country", "United States"),
            ("password", "SecurePass123!"),
            ("username", "jsmith2025"),
            ("credit card type", "Visa")
        ]
    
    filled_count = 0
    for field, value in data:
        if fill_field_dynamic(driver, field, value):
            filled_count += 1
    
    print(f"✅ Auto-filled {filled_count} fields")
    return filled_count > 0

# Dynamic command handler using pretrained NLP
def handle_dynamic_command(text):
    global driver, listening_active, form_mode, current_domain, command_history, custom_form_data
    
    text = text.lower().strip()
    if ACTIVATION_WORD in text:
        text = text.replace(ACTIVATION_WORD, "").strip()
    
    if not text:
        return
    
    print(f"🔊 Processing command: '{text}'")
    
    command_history.append({"command": text, "domain": current_domain})
    if len(command_history) > 5:
        command_history.pop(0)
    
    possible_intents = [
        "navigate_to_url",
        "search",
        "click_element",
        "type_text",
        "scroll_page",
        "go_back",
        "go_forward",
        "open_new_tab",
        "close_tab",
        "close_browser",
        "auto_fill_form",
        "submit_form",
        "clear_field",
        "stop_assistant",
        "help",
        "enter_form_mode",
        "exit_form_mode",
        "set_form_data"
    ]
    
    nav_bar = "navigation bar" in text or "navbar" in text or "menu" in text
    
    if form_mode and any(keyword in text for keyword in ["type", "enter", "fill", "select"]) and (" in " in text or " to " in text or " with " in text or "," in text):
        intent = "type_text"
        confidence = 1.0
        print(f"🧠 Heuristic intent (form mode): {intent} (confidence: {confidence:.2f})")
    elif text.startswith("click on"):
        intent = "click_element"
        confidence = 1.0
        print(f"🧠 Heuristic intent: {intent} (confidence: {confidence:.2f})")
    elif "select" in text and form_mode:
        intent = "type_text"
        confidence = 1.0
        print(f"🧠 Heuristic intent (form mode): {intent} (confidence: {confidence:.2f})")
    elif text.startswith("open") or "website" in text:
        intent = "navigate_to_url"
        confidence = 1.0
        print(f"🧠 Heuristic intent: {intent} (confidence: {confidence:.2f})")
    elif "scroll" in text and any(d in text for d in ["down", "up", "top", "bottom"]):
        intent = "scroll_page"
        confidence = 1.0
        print(f"🧠 Heuristic intent: {intent} (confidence: {confidence:.2f})")
    elif "go back" in text:
        intent = "go_back"
        confidence = 1.0
        print(f"🧠 Heuristic intent: {intent} (confidence: {confidence:.2f})")
    elif "enter form mode" in text:
        intent = "enter_form_mode"
        confidence = 1.0
        print(f"🧠 Heuristic intent: {intent} (confidence: {confidence:.2f})")
    elif "exit form mode" in text:
        intent = "exit_form_mode"
        confidence = 1.0
        print(f"🧠 Heuristic intent: {intent} (confidence: {confidence:.2f})")
    elif "set form data" in text:
        intent = "set_form_data"
        confidence = 1.0
        print(f"🧠 Heuristic intent: {intent} (confidence: {confidence:.2f})")
    else:
        if classifier:
            result = classifier(text, candidate_labels=possible_intents, multi_label=False)
            intent = result['labels'][0]
            confidence = result['scores'][0]
            print(f"🧠 Detected intent: {intent} (confidence: {confidence:.2f})")
            if form_mode and intent != "type_text" and confidence < 0.3 and ("type" in text or "enter" in text or "fill" in text or "select" in text):
                intent = "type_text"
                confidence = 0.9
                print(f"🧠 Adjusted intent (form mode): {intent} (confidence: {confidence:.2f})")
            elif intent == "navigate_to_url" and confidence < 0.15:
                speak("I didn't recognize that website. Try saying 'open youtube.com' or 'search for youtube'.")
                return
            elif intent == "scroll_page" and confidence < 0.2:
                speak("I didn't understand the scroll direction. Try saying 'scroll down' or 'scroll up'.")
                return
            elif intent == "go_back" and confidence < 0.2:
                speak("I didn't understand the go back command. Try saying 'go back' clearly.")
                return
            elif confidence < 0.5:
                speak("I'm not sure what you meant. Could you clarify or try a more specific command?")
                return
        else:
            intent = "search"
            if "click" in text or "select" in text:
                intent = "click_element"
            elif "type" in text or "enter" in text or "fill" in text:
                intent = "type_text"
            elif "scroll" in text:
                intent = "scroll_page"
            elif "back" in text:
                intent = "go_back"
            elif "forward" in text:
                intent = "go_forward"
            elif "new tab" in text:
                intent = "open_new_tab"
            elif "close" in text:
                intent = "close_browser"
            elif "auto fill" in text:
                intent = "auto_fill_form"
            elif "submit" in text:
                intent = "submit_form"
            elif "clear" in text:
                intent = "clear_field"
            elif "stop" in text:
                intent = "stop_assistant"
            elif "help" in text:
                intent = "help"
            elif "open" in text or "website" in text:
                intent = "navigate_to_url"
            print(f"🧠 Fallback intent: {intent}")
            confidence = 0.5
    
    target = text
    if intent in ["click_element", "type_text", "clear_field", "search", "set_form_data"]:
        action_keywords = ["click on", "select", "type", "enter", "fill", "clear", "in", "to", "with", "search for", "search on", "set form data", "navigation bar", "navbar", "menu"]
        for keyword in action_keywords:
            target = target.replace(keyword, "").strip()
        target = re.sub(r'[^\w\s\'\.]', '', target)
    
    print(f"🧠 Target: {target}")
    
    if intent not in ["stop_assistant", "help"] and not is_browser_alive():
        if not init_browser():
            speak("I couldn't start the browser")
            return
    
    update_current_domain()
    
    try:
        if intent == "navigate_to_url":
            url_match = re.search(r'(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', target)
            if url_match:
                target = url_match.group(0)
                if not target.startswith("www."):
                    target = "www." + target
            if "." in target or target in ["youtube", "facebook", "twitter", "google", "reddit", "wikipedia"]:
                url = target
                if not url.startswith("http"):
                    common_sites = {
                        "youtube": "https://www.youtube.com",
                        "facebook": "https://www.facebook.com",
                        "twitter": "https://www.twitter.com",
                        "google": "https://www.google.com",
                        "reddit": "https://www.reddit.com",
                        "wikipedia": "https://www.wikipedia.org"
                    }
                    url = common_sites.get(target, f"https://{target}")
                speak(f"Opening {target}")
                driver.get(url)
                update_current_domain()
            else:
                speak(f"I didn't recognize {target} as a website. Try saying 'open youtube.com' or 'search for {target}'.")
        
        elif intent == "search":
            query = target.replace("youtube", "").strip() if "youtube" in target else target
            if current_domain == "www.youtube.com" or "youtube" in target:
                speak(f"Searching YouTube for {query}")
                driver.get(f"https://youtube.com/results?search_query={quote(query)}")
                update_current_domain()
            elif current_domain == "www.google.com":
                try:
                    try:
                        consent_button = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept') or contains(., 'Agree')]"))
                        )
                        consent_button.click()
                        print("✅ Dismissed consent popup")
                    except TimeoutException:
                        pass
                    element = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//input[@name='q' or @type='search' or @type='text']"))
                    )
                    print("✅ Search input field is clickable")
                    driver.execute_script("arguments[0].focus();", element)
                    time.sleep(0.5)
                    for attempt in range(2):
                        try:
                            element.clear()
                            element.send_keys(query)
                            element.send_keys(Keys.ENTER)
                            speak(f"Searched for {query} on Google")
                            update_current_domain()
                            break
                        except (InvalidElementStateException, ElementNotInteractableException) as e:
                            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                            if attempt == 1:
                                print("❌ Failed to interact with search field after retries")
                                speak("I couldn't type in the search field. Searching directly.")
                                driver.get(f"https://www.google.com/search?q={quote(query)}")
                                update_current_domain()
                            time.sleep(1)
                except TimeoutException:
                    print("❌ Search input field not found or not clickable")
                    speak("I couldn't find the search field. Searching directly.")
                    driver.get(f"https://www.google.com/search?q={quote(query)}")
                    update_current_domain()
            else:
                speak(f"Searched for {query} on Google")
                driver.get(f"https://www.google.com/search?q={quote(query)}")
                update_current_domain()
        
        elif intent == "click_element":
            try:
                if current_domain == "www.amazon.com":
                    dismiss_amazon_popups()

                element, href = find_element_dynamic(driver, target, element_type="link", nav_bar=nav_bar)
                if element and href:
                    WebDriverWait(driver, 10).until_not(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(@class, 'loading')]"))
                    )
                    for attempt in range(3):
                        try:
                            element = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, f"//a[@href='{href}']"))
                            )
                            WebDriverWait(driver, 10).until(EC.visibility_of(element))
                            size = element.size
                            location = element.location
                            print(f"✅ Element verified: size={size}, location={location}")
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                            time.sleep(1)
                            overlapping = driver.execute_script(
                                "var elem = arguments[0]; var rect = elem.getBoundingClientRect(); "
                                "var x = rect.left + (rect.width / 2); var y = rect.top + (rect.height / 2); "
                                "var elementAtPoint = document.elementFromPoint(x, y); "
                                "return elementAtPoint !== elem;",
                                element
                            )
                            if overlapping:
                                driver.execute_script("arguments[0].click();", element)
                                print(f"✅ Clicked on {target} via JavaScript (href: {href})")
                                speak(f"Clicked on {target}")
                                break
                            WebDriverWait(driver, 10).until(
                                lambda d: element.is_displayed() and element.is_enabled()
                            )
                            ActionChains(driver).move_to_element(element).click().perform()
                            print(f"✅ Clicked on {target} (href: {href})")
                            speak(f"Clicked on {target}")
                            break
                        except StaleElementReferenceException as e:
                            print(f"⚠️ Stale element on attempt {attempt + 1}: {e}")
                            if attempt == 2:
                                print("❌ Failed to click element after retries due to staleness")
                                speak(f"I couldn't click on {target} because the element became unavailable. Try again.")
                                return
                            time.sleep(1)
                        except (ElementNotInteractableException, InvalidElementStateException) as e:
                            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                            if attempt == 2:
                                print("❌ Failed to click element with ActionChains after retries")
                                try:
                                    element = WebDriverWait(driver, 10).until(
                                        EC.element_to_be_clickable((By.XPATH, f"//a[@href='{href}']"))
                                    )
                                    driver.execute_script("arguments[0].click();", element)
                                    print(f"✅ Clicked on {target} via JavaScript (href: {href})")
                                    speak(f"Clicked on {target}")
                                    WebDriverWait(driver, 5).until(EC.url_changes(driver.current_url))
                                    time.sleep(3)
                                    update_current_domain()
                                except Exception as js_e:
                                    print(f"❌ JavaScript click failed: {js_e}")
                                    full_url = f"https://{current_domain}{href}" if href.startswith('/') else href
                                    driver.get(full_url)
                                    print(f"✅ Navigated directly to {full_url}")
                                    speak(f"Clicked on {target} by navigating directly")
                                    update_current_domain()
                                return
                            time.sleep(1)
                else:
                    speak(f"I couldn't find {target} on this page. Try scrolling down or searching for it.")
                    driver.execute_script("window.scrollBy(0, 1000)")
                    element, href = find_element_dynamic(driver, target, element_type="link", nav_bar=nav_bar)
                    if element and href:
                        WebDriverWait(driver, 10).until_not(
                            EC.presence_of_element_located((By.XPATH, "//*[contains(@class, 'loading')]"))
                        )
                        for attempt in range(3):
                            try:
                                element = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, f"//a[@href='{href}']"))
                                )
                                WebDriverWait(driver, 10).until(EC.visibility_of(element))
                                size = element.size
                                location = element.location
                                print(f"✅ Element verified after scroll: size={size}, location={location}")
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                                time.sleep(1)
                                overlapping = driver.execute_script(
                                    "var elem = arguments[0]; var rect = elem.getBoundingClientRect(); "
                                    "var x = rect.left + (rect.width / 2); var y = rect.top + (rect.height / 2); "
                                    "var elementAtPoint = document.elementFromPoint(x, y); "
                                    "return elementAtPoint !== elem;",
                                    element
                                )
                                if overlapping:
                                    driver.execute_script("arguments[0].click();", element)
                                    print(f"✅ Clicked on {target} via JavaScript after scrolling (href: {href})")
                                    speak(f"Clicked on {target} after scrolling")
                                    break
                                WebDriverWait(driver, 10).until(
                                    lambda d: element.is_displayed() and element.is_enabled()
                                )
                                ActionChains(driver).move_to_element(element).click().perform()
                                print(f"✅ Clicked on {target} after scrolling (href: {href})")
                                speak(f"Clicked on {target} after scrolling")
                                break
                            except StaleElementReferenceException as e:
                                print(f"⚠️ Stale element on attempt {attempt + 1}: {e}")
                                if attempt == 2:
                                    print("❌ Failed to click element after retries due to staleness")
                                    speak(f"I couldn't click on {target} because the element became unavailable. Try again.")
                                    return
                                time.sleep(1)
                            except (ElementNotInteractableException, InvalidElementStateException) as e:
                                print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                                if attempt == 2:
                                    print("❌ Failed to click element after scrolling")
                                    try:
                                        element = WebDriverWait(driver, 10).until(
                                            EC.element_to_be_clickable((By.XPATH, f"//a[@href='{href}']"))
                                        )
                                        driver.execute_script("arguments[0].click();", element)
                                        print(f"✅ Clicked on {target} via JavaScript after scrolling (href: {href})")
                                        speak(f"Clicked on {target} after scrolling")
                                        WebDriverWait(driver, 5).until(EC.url_changes(driver.current_url))
                                        time.sleep(3)
                                        update_current_domain()
                                    except Exception as js_e:
                                        print(f"❌ JavaScript click failed: {js_e}")
                                        full_url = f"https://{current_domain}{href}" if href.startswith('/') else href
                                        driver.get(full_url)
                                        print(f"✅ Navigated directly to {full_url}")
                                        speak(f"Clicked on {target} by navigating directly after scrolling")
                                        update_current_domain()
                                    return
                                time.sleep(1)
                    else:
                        speak(f"Still couldn't find {target}. Try a different command or search for it.")
            except TimeoutException:
                print(f"❌ Link not found or not clickable: {target}")
                speak(f"I couldn't find a clickable link for {target}. Try a different website or position.")
            except Exception as e:
                print(f"⚠️ Click error: {e}")
                speak(f"I had trouble clicking on {target}. Please try again.")
        
        elif intent == "type_text":
            print(f"🔊 Original command: '{text}'")
            print(f"🧠 Processing type_text intent (form_mode: {form_mode})")
            analyze_form_dynamic(driver)
            if form_mode:
                field = None
                value = None
                cleaned_text = re.sub(r'[^\w\s]', '', text).strip()
                print(f"🧠 Cleaned text: '{cleaned_text}'")
                if "select" in cleaned_text:
                    parts = cleaned_text.replace("select", "").strip().split()
                    if len(parts) > 1:
                        field = ' '.join(parts[:-1]).strip()
                        value = parts[-1].strip()
                elif "," in cleaned_text:
                    parts = [p.strip() for p in cleaned_text.split(",") if p.strip()]
                    if len(parts) >= 2:
                        field = parts[1].strip()
                        value = parts[2].strip() if len(parts) > 2 else parts[0].replace("type", "").strip()
                else:
                    match = re.match(r'^(?:type|enter|fill|select)\s+(.+?)\s+(?:in|to|with)\s+(.+)$', cleaned_text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        field = match.group(2).strip()
                    else:
                        for delimiter in [" in ", " to ", " with "]:
                            if delimiter in cleaned_text:
                                parts = cleaned_text.split(delimiter, 1)
                                value = parts[0].replace("type", "").replace("select", "").strip()
                                field = parts[1].strip()
                                break
                        if not field:
                            parts = cleaned_text.split()
                            if len(parts) > 2:
                                value = ' '.join(parts[1:parts.index('in') if "in" in parts else len(parts)]).strip()
                                field = ' '.join(parts[parts.index('in') + 1:] if "in" in parts else parts[1:]).strip()

                print(f"🧠 Extracted value: '{value}', field: '{field}'")
                if field and value:
                    if fill_field_dynamic(driver, field, value):
                        speak(f"Filled {field} with {value}")
                    else:
                        form_elements = analyze_form_dynamic(driver)
                        speak(f"I couldn't find the {field} field. Available fields: {list(form_elements.keys())}")
                else:
                    speak("Please specify a field and value, e.g., 'type tabish 123 in password' or 'select visa in credit card type'")
            else:
                element, _ = find_element_dynamic(driver, "search", element_type="input")
                if not element:
                    element, _ = find_element_dynamic(driver, "input", element_type="input")
                if element:
                    element.clear()
                    element.send_keys(target)
                    speak(f"Typed {target}")
                else:
                    active_element = driver.switch_to.active_element
                    if active_element.tag_name in ["input", "textarea"]:
                        active_element.clear()
                        active_element.send_keys(target)
                        speak(f"Typed {target}")
                    else:
                        speak("I couldn't find a text field")
        
        elif intent == "scroll_page":
            driver.switch_to.window(driver.current_window_handle)
            direction = target.lower()
            if "down" in direction:
                driver.execute_script("window.scrollBy(0, 1000)")
                try:
                    ActionChains(driver).send_keys(Keys.PAGE_DOWN).perform()
                except:
                    pass
                speak("Scrolled down")
            elif "up" in direction:
                driver.execute_script("window.scrollBy(0, -1000)")
                try:
                    ActionChains(driver).send_keys(Keys.PAGE_UP).perform()
                except:
                    pass
                speak("Scrolled up")
            elif "top" in direction:
                driver.execute_script("window.scrollTo(0, 0)")
                speak("Scrolled to top")
            elif "bottom" in direction:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                speak("Scrolled to bottom")
            else:
                speak("Please specify scroll direction, like 'scroll down' or 'scroll up'")
        
        elif intent == "go_back":
            driver.switch_to.window(driver.current_window_handle)
            if driver.execute_script("return history.length") <= 1:
                speak("There is no previous page to go back to")
                return
            try:
                speak("Going back")
                driver.back()
                time.sleep(2)
                update_current_domain()
                speak("Went back to the previous page")
            except WebDriverException as e:
                print(f"⚠️ WebDriver error during back navigation: {e}")
                speak("I couldn't go back. The page history might be unavailable.")
        
        elif intent == "go_forward":
            speak("Going forward")
            driver.forward()
            time.sleep(2)
            update_current_domain()
        
        elif intent == "open_new_tab":
            driver.execute_script("window.open('', '_blank');")
            driver.switch_to.window(driver.window_handles[-1])
            speak("Opened new tab")
            update_current_domain()
        
        elif intent == "close_tab":
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[-1])
                speak("Closed current tab")
                update_current_domain()
            else:
                speak("This is the last tab")
        
        elif intent == "close_browser":
            speak("Closing browser")
            if driver:
                driver.quit()
                driver = None
            command_history.clear()
        
        elif intent == "auto_fill_form":
            if autofill_form_dynamic(driver):
                speak("Form auto-filled successfully")
            else:
                speak("I couldn't auto-fill the form")
        
        elif intent == "submit_form":
            element, href = find_element_dynamic(driver, "submit", element_type="button")
            if not element:
                element, href = find_element_dynamic(driver, "save", element_type="button")
            if not element:
                element, href = find_element_dynamic(driver, "send", element_type="button")
            if element and href:
                try:
                    ActionChains(driver).move_to_element(element).click().perform()
                    speak("Form submitted")
                    update_current_domain()
                except:
                    driver.execute_script("arguments[0].click();", element)
                    speak("Form submitted")
                    update_current_domain()
            else:
                speak("I couldn't find the submit button")
        
        elif intent == "clear_field":
            element, _ = find_element_dynamic(driver, target, element_type="input")
            if element:
                element.clear()
                speak(f"Cleared {target} field")
            else:
                speak(f"I couldn't find the {target} field")
        
        elif intent == "stop_assistant":
            speak("Stopping voice assistant")
            listening_active = False
            if driver:
                driver.quit()
                driver = None
            command_history.clear()
        
        elif intent == "help":
            speak("I can understand most browser commands, like opening websites, searching, clicking elements, typing text, filling forms, scrolling, or going back. For forms: say 'enter form mode' to fill fields, 'type value in field', 'select value in field', 'auto fill form', or 'submit form'. For navigation: say 'click on home in navigation bar'. Try specific website names or positions like 'first link' for search results.")
        
        elif intent == "enter_form_mode":
            form_mode = True
            speak("Form mode enabled. You can now fill fields by saying 'type value in field' or 'select value in field'.")
        
        elif intent == "exit_form_mode":
            form_mode = False
            speak("Form mode disabled.")
        
        elif intent == "set_form_data":
            parts = target.split("to")
            if len(parts) == 2:
                field = parts[0].strip()
                value = parts[1].strip()
                custom_form_data[field] = value
                speak(f"Set form data: {field} to {value}")
            else:
                speak("Please say 'set form data field to value', e.g., 'set form data name to Jane Doe'")
        
        else:
            speak("I'm not sure how to handle that command. Try rephrasing or say 'help' for options.")
    
    except Exception as e:
        print(f"⚠️ Command error: {e}")
        speak("I had trouble with that command. Please try again.")

# Start listening
def start_listening():
    global listening_active
    if not listening_active:
        listening_active = True
        start_button.config(state='disabled')
        stop_button.config(state='normal')
        listen_thread = threading.Thread(target=listen_loop, daemon=True)
        listen_thread.start()
        speak("Voice assistant started. Say activate to activate.")

# Stop listening
def stop_listening():
    global listening_active, driver
    listening_active = False
    start_button.config(state='normal')
    stop_button.config(state='disabled')
    if driver:
        driver.quit()
        driver = None
    command_history.clear()
    speak("Voice assistant stopped.")

# Listening loop
def listen_loop():
    global listening_active
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.energy_threshold = 4000
    
    while listening_active:
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("👂 Listening for activation word...")
                
                try:
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    text = recognizer.recognize_google(audio).lower()
                    print(f"🔊 Heard: {text}")
                    
                    if ACTIVATION_WORD in text.lower():
                        print("✅ Activation word detected!")
                        speak("Yes, I'm listening")
                        
                        audio_data, sample_rate, _ = record_audio()
                        audio_file = save_to_wav(audio_data, sample_rate)
                        command = transcribe_audio(audio_file)
                        if command:
                            print(f"🔊 Command: {command}")
                            handle_dynamic_command(command)
                        try:
                            os.unlink(audio_file)
                        except:
                            pass
                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    print(f"⚠️ Google Speech API error: {e}")
                    if model:
                        audio_data, sample_rate, _ = record_audio()
                        audio_file = save_to_wav(audio_data, sample_rate)
                        text = transcribe_audio(audio_file)
                        if ACTIVATION_WORD in text.lower():
                            print("✅ Activation word detected (Whisper)!")
                            speak("Yes, I'm listening")
                            command = transcribe_audio(audio_file)
                            if command:
                                print(f"🔊 Command: {command}")
                                handle_dynamic_command(command)
                        try:
                            os.unlink(audio_file)
                        except:
                            pass
        except Exception as e:
            print(f"⚠️ General error: {e}")
            time.sleep(1)

# Create GUI with Start and Stop buttons
def create_gui():
    global gui, start_button, stop_button
    gui = tk.Tk()
    gui.title("Voice Assistant")
    gui.geometry("300x150")

    # Start button
    start_button = ttk.Button(gui, text="Start", command=start_listening)
    start_button.pack(pady=10)

    # Stop button
    stop_button = ttk.Button(gui, text="Stop", command=stop_listening, state='disabled')
    stop_button.pack(pady=10)

    gui.protocol("WM_DELETE_WINDOW", on_closing)
    gui.mainloop()

# Cleanup on window close
def on_closing():
    global listening_active, driver
    listening_active = False
    if driver:
        driver.quit()
    command_history.clear()
    gui.destroy()
    print("👋 Voice assistant terminated")

if __name__ == "__main__":
    load_whisper_model("base")
    load_nlp_models()
    create_gui()