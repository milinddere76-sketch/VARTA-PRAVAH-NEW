import os
import requests
from groq import Groq
from gtts import gTTS
import subprocess
import time
import glob
import sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv

# Initialize Environment & AI Clients
load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Paths mapping relative to /news-ai/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
ANCHORS_DIR = os.path.join(BASE_DIR, "anchors")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# [SMART AI] Garbage Collection Module
def cleanup_old_videos(hours=6, min_files=5):
    print("🧹 Running Video Garbage Collection Cache Sweep...")
    now = time.time()
    video_files = glob.glob(os.path.join(VIDEOS_DIR, "*.mp4"))
    
    # Safe protection check (e.g., must have 5 videos to stream)
    if len(video_files) <= min_files:
        print(f"✅ Shield Active: Only {len(video_files)} files remain. Retaining all files to protect Stream.")
        return
        
    # Sort files by modification time (oldest first)
    video_files.sort(key=os.path.getmtime)
    
    deleted_count = 0
    # Iterate over older files and delete safely until we hit the minimum buffer constraint
    for f in video_files:
        if len(video_files) - deleted_count <= min_files:
            break
            
        file_mod_time = os.path.getmtime(f)
        if now - file_mod_time > (hours * 3600):
            try:
                os.remove(f)
                # Cleanup associated tmp audio file to save inode space
                audio_file = f.replace(".mp4", ".mp3").replace("bulletin_", "output_audio_")
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                deleted_count += 1
                print(f"🗑️ Cleaned up expired broadcast segment: {os.path.basename(f)}")
            except Exception as e:
                pass

# 1. Dynamic News Fetcher (Priority: Maharashtra -> National -> World)
def fetch_news():
    api_key = os.getenv("WORLD_NEWS_API_KEY")
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        return [{"headline": "[MOCK] Maharashtra Update", "description": "Mock news description for the batch gen."}]
    
    news_list = []
    
    # Priority 1: Maharashtra
    try:
        r1 = requests.get(f"https://api.worldnewsapi.com/search-news?api-key={api_key}&text=Maharashtra&language=mr&number=2", timeout=5)
        d1 = r1.json()
        if d1.get("news"):
            for n in d1["news"]:
                news_list.append({"headline": "Maharashtra: " + n["title"], "description": n["text"][:400]})
    except Exception as e:
        print(f"Maharashtra fetch error: {e}")
        
    # Priority 2: National / India
    try:
        r2 = requests.get(f"https://api.worldnewsapi.com/search-news?api-key={api_key}&text=India&language=mr&number=2", timeout=5)
        d2 = r2.json()
        if d2.get("news"):
            for n in d2["news"]:
                news_list.append({"headline": "National: " + n["title"], "description": n["text"][:400]})
    except Exception as e:
        print(f"National fetch error: {e}")
        
    # Priority 3: World
    try:
        r3 = requests.get(f"https://api.worldnewsapi.com/search-news?api-key={api_key}&text=World&language=mr&number=1", timeout=5)
        d3 = r3.json()
        if d3.get("news"):
            for n in d3["news"]:
                news_list.append({"headline": "International: " + n["title"], "description": n["text"][:400]})
    except Exception as e:
        print(f"World fetch error: {e}")

    if not news_list:
        news_list.append({"headline": "Maharashtra Political Update", "description": "New developments in the state assembly regarding the budget."})

    return news_list

# [SMART AI] Intelligent Keyword Processor
def check_breaking_news(headline):
    breaking_keywords = ["तात्काळ", "मोठी बातमी", "ब्रेकिंग न्यूज", "भूकंप", "राजिनामा"]
    for kw in breaking_keywords:
        if kw in headline:
            return kw
    return None

# 2. Scheduling Logic Defined by User
BULLETINS = [
    {"name": "सकाळ", "style": "Top headlines and morning updates", "time_slot": "6_AM"},
    {"name": "दुपार", "style": "Updates and breaking news", "time_slot": "12_PM"},
    {"name": "संध्याकाळ", "style": "Detailed reporting", "time_slot": "6_PM"},
    {"name": "प्राइम टाइम", "style": "Deep analysis and critical insights", "time_slot": "9_PM"},
    {"name": "रात्री", "style": "Summary of the day's major events", "time_slot": "11_PM"}
]

# 3. AI Script Engine
def generate_script(news_data, bulletin, is_female=False):
    anchor_gender = "महिला (Female)" if is_female else "पुरुष (Male)"
    gender_instruction = f"* व्याकरण (Grammar): अत्यंत शुद्ध आणि व्यावसायिक मराठी भाषेचा वापर करा. कोणतीही व्याकरणीय चूक नको.\n* लिंग (Gender Rule): अँकर {anchor_gender} आहे. त्यामुळे स्वतःबद्दल बोलताना क्रियापदे '{anchor_gender}' लिंगानुसारच वापरा (उदा. पुरुष असल्यास 'मी सांगतो', 'माझा', महिला असल्यास 'मी सांगते', 'माझी'). हे अत्यंत महत्त्वाचे आहे!"
    
    system_prompt = f"""तुम्ही एक व्यावसायिक Marathi वृत्तवाहिनीचे अँकर आहात. आता '{bulletin['name']}' बुलेटिनची वेळ आहे.

नियम:
* भाषा पूर्णपणे शुद्ध आणि अधिकृत Marathi असावी. वाक्यरचना अचूक आणि बातमीदाराला शोभेल अशी असावी.
* उच्चार स्पष्ट आणि प्रभावी असावेत
* बातमी सादरीकरणाचा वेग मध्यम असावा
* आवाजात आत्मविश्वास आणि गांभीर्य असावे
* सादरीकरण पुर्णपणे '{bulletin['style']}' या शैलीत असावे.
* केवळ बातमी (STRICT RULE): DO NOT add any greetings like "Namaskar", DO NOT introduce yourself or the channel, DO NOT add closing remarks, DO NOT add conversational fillers. YOU MUST START READING THE CORE SCRIPT DIRECTLY.
{gender_instruction}
"""
    user_prompt = f"""बातमी:
{news_data['headline']} - {news_data['description']}

कृपया वरील बातमीसाठी 'Varta Pravah - {bulletin['name']}' या बुलेटिनची स्क्रिप्ट तयार करा. फक्त बातमीचा मजकूर द्या, दुसरे काहीही नाही:"""

    print(f"Generating Llama3 Script Sequence for: {bulletin['time_slot']} (Anchor: {anchor_gender})...")
    completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    return completion.choices[0].message.content

# 4. Engine Generator (Edge-TTS + FFmpeg Ticker Logic)
def generate_video(script, bulletin, breaking_text=None, is_female=False, is_promo=False):
    print(f"Rendering Broadcast Pipeline for {bulletin['time_slot']}...")
    
    out_audio = os.path.join(VIDEOS_DIR, f"output_audio_{bulletin['time_slot']}.mp3")
    out_video = os.path.join(VIDEOS_DIR, f"bulletin_{bulletin['time_slot']}.mp4")
    
    # Alternating Synthetic Anchors
    anchor_name = "anchor_female.mp4" if is_female else "anchor_male.mp4"
    anchor_mp4 = os.path.join(ANCHORS_DIR, anchor_name)
    
    # Custom Promo Backdrop
    bg_jpg = os.path.join(ASSETS_DIR, "promo.jpg") if is_promo else os.path.join(ASSETS_DIR, "studio.jpg")
    font_path = os.path.join(ASSETS_DIR, "font.ttf").replace("\\", "/") # Unix formatting critical for FFmpeg filters
    logo_png = os.path.join(ASSETS_DIR, "logo.png")
    
    # Text-to-Speech Processing using Microsoft Edge TTS (Realistic Marathi Neural Voices)
    voice = "mr-IN-AarohiNeural" if is_female else "mr-IN-ManoharNeural"
    subprocess.run(["python", "-m", "edge_tts", "--voice", voice, "--text", script, "--write-media", out_audio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if not os.path.exists(anchor_mp4) or not os.path.exists(bg_jpg) or not os.path.exists(logo_png):
        print(f"⚠️ SYSTEM FAULT: Master visual assets (anchor, bg, or logo) are missing!")
        return
        
    # [SMART AI] Dynamic Screen Burn-in Graphic logic
    filter_complex = "[0:v]colorkey=0x00FF00:0.3:0.2,scale=1280:720[anchor]; [1:v][anchor]overlay=(W-w)/2:(H-h)/2[base];"
    filter_complex += "[2:v]scale=250:-1[logoscale]; [base][logoscale]overlay=W-w-50:50[base2];"
    
    if breaking_text and os.path.exists(font_path):
        # Escaping rules for FFmpeg drawtext module. Boxed background + Bold Red Ticker style
        text_filter = f"[base2]drawtext=fontfile='{font_path}':text='{breaking_text}':fontcolor=white:fontsize=65:x=(w-text_w)/2:y=600:box=1:boxcolor=red@0.9:boxborderw=20[outv]"
    else:
        text_filter = "[base2]copy[outv]"
        
    # Overlay FFmpeg Command Exec
    cmd = [
        "ffmpeg", "-y", 
        "-stream_loop", "-1", "-i", anchor_mp4,
        "-loop", "1", "-i", bg_jpg,
        "-i", logo_png,
        "-i", out_audio,
        "-filter_complex", filter_complex + text_filter,
        "-map", "[outv]", "-map", "3:a",
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest", out_video
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Successfully exported multiplex container: {out_video}\n")

if __name__ == "__main__":
    print("---------------------------------------")
    print("⚡ ZERO-PC NEWS-AI SMART COMPILER ⚡")
    print("---------------------------------------")
    
    # Pre-execution environment sanity check / cleanup
    cleanup_old_videos(hours=6, min_files=5)
    
    print("Fetching top regional headlines across API...")
    headlines = fetch_news()
    
    # Execute Breaking News evaluation priority
    detected_breaking_keyword = check_breaking_news(headlines[0]["headline"])
    
    if detected_breaking_keyword:
        print(f"🚨 MAJOR ALERT: Detected '{detected_breaking_keyword}'! Executing Emergency Override Protocol.")
        urgent_bulletin = {
            "name": "ब्रेकिंग न्यूज",
            "style": "URGENT Priority News Alert, speak dynamically, fast paced.",
            "time_slot": "BREAKING"
        }
        script = generate_script(headlines[0], urgent_bulletin, is_female=False)
        generate_video(script, urgent_bulletin, breaking_text=f"ब्रेकिंग न्यूज: {detected_breaking_keyword}", is_female=False)
    else:
        print("Executing standard TV-style schedule loops.")
        for idx, bulletin in enumerate(BULLETINS):
            selected_news = headlines[idx % len(headlines)]
            is_female_anchor = (idx % 2 == 1) # Alternate dynamically
            script = generate_script(selected_news, bulletin, is_female=is_female_anchor)
            generate_video(script, bulletin, breaking_text="आत्ताची घडामोड", is_female=is_female_anchor)
            
        print("🚀 Generating Gen-Z Promotional Filler...")
        promo_b = {
            "name": "Promo", "style": "Gen-Z style, youthful, high energy channel promotion, Marathi and English mix.", "time_slot": "PROMO"
        }
        promo_script = generate_script({"headline": "Subscribe to VartaPravah", "description": "Keep it locked to VartaPravah for 24/7 non-stop ultra lit Marathi news streams!"}, promo_b, is_female=True)
        generate_video(promo_script, promo_b, breaking_text="🔥 फॉलो आणि सबस्क्राईब करा!", is_female=True, is_promo=True)

    print("---------------------------------------")
    print("Sequence Operation Complete! Server safely idling until next cycle.")
