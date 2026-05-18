import asyncio
import edge_tts
import os
from app import config
from app.text_cleaner import clean_marathi

def enhance_audio(input_file, output_file):
    """Broadcast Enhancement - normalizes volume and adds a high-fidelity compressor presence (no muffled lowpass!)."""
    temp = input_file.replace(".mp3", "_enhanced.mp3")
    # We remove the muffled lowpass=f=4000 to keep the high-fidelity crispness and clarity of the neural voice.
    cmd = f"""
    ffmpeg -y -i "{input_file}" \
    -filter:a "volume=1.2,highpass=f=80,acompressor=threshold=0.2:ratio=3:attack=5:release=50" \
    -ar 44100 \
    "{temp}" > /dev/null 2>&1
    """
    os.system(cmd)
    if os.path.exists(temp):
        import shutil
        shutil.move(temp, output_file)

def generate_tts(text, output_file, anchor_type="male"):
    """
    State-of-the-Art Neural TTS Synthesis Pipeline.
    Uses Microsoft Edge's highly-realistic neural voices for professional news presentation.
    """
    text = clean_marathi(text)
    
    # Premium Neural Voices & Styles mapping
    if anchor_type == "female1":
        voice = "mr-IN-AarohiNeural"
        rate = "+4%"
        pitch = "+0Hz"
    elif anchor_type == "female2":
        voice = "mr-IN-AarohiNeural"
        rate = "+6%"
        pitch = "-5%"
    elif anchor_type == "male1":
        voice = "mr-IN-ManoharNeural"
        rate = "+3%"
        pitch = "+0Hz"
    elif anchor_type == "male2":
        voice = "mr-IN-ManoharNeural"
        rate = "+5%"
        pitch = "-8%"
    else:
        # Fallback to standard mapping
        voice = "mr-IN-ManoharNeural" if "male" in str(anchor_type).lower() else "mr-IN-AarohiNeural"
        rate = "+4%"
        pitch = "+0Hz"
    
    temp_raw = os.path.join(config.OUTPUT_DIR, f"raw_{os.path.basename(output_file)}")
    
    async def amain():
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await communicate.save(temp_raw)

    try:
        asyncio.run(amain())
    except Exception as e:
        print(f"❌ [TTS-ENGINE] Neural Synthesis Error: {e}")
        # Fallback to standard gTTS if network / edge-tts is down
        from gtts import gTTS
        try:
            tts = gTTS(text=text, lang='mr', slow=False)
            tts.save(temp_raw)
        except Exception as fallback_err:
            print(f"🚨 [TTS-ENGINE] Absolute Fallback Failed: {fallback_err}")
            return None

    # Apply broadcast grade audio compression for deep studio authority
    enhance_audio(temp_raw, output_file)

    if os.path.exists(temp_raw):
        try:
            os.remove(temp_raw)
        except:
            pass

    return output_file

def generate_audio(text, file_path, anchor_type="male"):
    return generate_tts(text, file_path, anchor_type)

class TTSEngine:
    def generate_audio(self, text, output_path, anchor_type="male"):
        return generate_tts(text, output_path, anchor_type)
