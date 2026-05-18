from gtts import gTTS
import os
from app import config
from app.text_cleaner import clean_marathi

def female_voice_effect(file):
    """Fake female pitch shift."""
    temp = file.replace(".mp3", "_f.mp3")
    # Normalize tempo back to 1.0x speed (no slowdown)
    os.system(f"ffmpeg -y -i {file} -filter:a 'asetrate=44100*1.1,atempo=1.0' {temp} > /dev/null 2>&1")
    if os.path.exists(temp):
        os.rename(temp, file)

def male_voice_effect(file):
    """Deep male voice effect - lowers pitch for authoritative news anchor."""
    temp = file.replace(".mp3", "_m.mp3")
    # Lower pitch for deep, authoritative male voice (15% deeper)
    os.system(f"ffmpeg -y -i {file} -filter:a 'asetrate=44100*0.85,atempo=1.0' {temp} > /dev/null 2>&1")
    if os.path.exists(temp):
        os.rename(temp, file)

def enhance_audio(input_file, output_file):
    """Broadcast Enhancement - preserve bass for anchor authority."""
    cmd = f"""
    ffmpeg -y -i {input_file} \
    -filter:a "volume=1.3,highpass=f=100,lowpass=f=4000,acompressor=threshold=0.3:ratio=4:attack=5:release=50" \
    -ar 44100 \
    {output_file} > /dev/null 2>&1
    """
    os.system(cmd)

def generate_tts(text, output_file, anchor_type="male"):
    """Full Synthesis Pipeline with Gender Effects.
    Default to male anchor for authoritative news presentation.
    """
    text = clean_marathi(text)
    
    # Use slow=True for clearer, more intelligible audio
    tts = gTTS(text=text, lang='mr', slow=True)
    temp_raw = os.path.join(config.OUTPUT_DIR, f"raw_{os.path.basename(output_file)}")
    tts.save(temp_raw)

    # Apply Gender Identity Effect
    if anchor_type == "male":
        male_voice_effect(temp_raw)
    else:
        female_voice_effect(temp_raw)

    # Final Broadcast Enhancement
    enhance_audio(temp_raw, output_file)

    if os.path.exists(temp_raw):
        os.remove(temp_raw)

    return output_file

def generate_audio(text, file_path, anchor_type="male"):
    return generate_tts(text, file_path, anchor_type)

class TTSEngine:
    def generate_audio(self, text, output_path, anchor_type="male"):
        return generate_tts(text, output_path, anchor_type)
