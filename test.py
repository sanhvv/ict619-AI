import pyttsx3

# engine = pyttsx3.init()
# engine.say("Hello, can you hear me?")
# engine.runAndWait()


engine = pyttsx3.init()
engine.setProperty('rate', 180)
engine.say("Hello, can you hear me?")
engine.runAndWait()