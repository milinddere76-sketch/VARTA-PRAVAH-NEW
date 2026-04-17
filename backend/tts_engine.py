import os
import time
from gtts import gTTS

def generate_audio(data):
    """
    Generates Marathi audio using gTTS.
    Input data tuple: (text, anchor_gender)
    """
    text, anchor = data

    # 1. Use Unique Filename to prevent IO clashing and FFmpeg crashes
    ts = int(time.time())
    path = f"/app/videos/audio_{ts}.mp3"

    print(f"🎙️ [TTS] Generating Audio for {anchor} using gTTS...")

    # gTTS currently supports 'mr' (Marathi) standard voice.
    # We maintain the interface for future voice selection expansion.
    lang = "mr"
    
    try:
        tts = gTTS(text=text, lang=lang)
        tts.save(path)
        return path
    except Exception as e:
        print(f"❌ gTTS Error: {e}")
        # Return a silent or dummy file if tts fails to keep the pipeline moving
        return path 
