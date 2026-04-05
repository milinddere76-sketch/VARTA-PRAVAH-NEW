import os
import requests
from groq import Groq
from gtts import gTTS
import subprocess
from dotenv import load_dotenv

# Initialize Environment & AI Clients
load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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
                news_list.append({"headline": n["title"], "description": n["text"][:400]})
    except Exception as e:
        print(f"Maharashtra fetch error: {e}")
        
    # Priority 2: National / India
    try:
        r2 = requests.get(f"https://api.worldnewsapi.com/search-news?api-key={api_key}&text=India&language=mr&number=2", timeout=5)
        d2 = r2.json()
        if d2.get("news"):
            for n in d2["news"]:
                news_list.append({"headline": n["title"], "description": n["text"][:400]})
    except Exception as e:
        print(f"National fetch error: {e}")
        
    # Priority 3: World
    try:
        r3 = requests.get(f"https://api.worldnewsapi.com/search-news?api-key={api_key}&text=World&language=mr&number=1", timeout=5)
        d3 = r3.json()
        if d3.get("news"):
            for n in d3["news"]:
                news_list.append({"headline": n["title"], "description": n["text"][:400]})
    except Exception as e:
        print(f"World fetch error: {e}")

    if not news_list:
        news_list.append({"headline": "Maharashtra Political Update", "description": "New developments in the state assembly regarding the budget."})

    return news_list

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

    print(f"Generating Script for: {bulletin['time_slot']} (Anchor: {anchor_gender})...")
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

# 4. Engine Generator (Edge-TTS + FFmpeg)
def generate_video(script, bulletin, is_female=False):
    print(f"Synthesizing Audio & Video for {bulletin['time_slot']}...")
    out_audio = f"c:/VARTAPRAVAH/backend/output_audio_{bulletin['time_slot']}.mp3"
    out_video = f"c:/VARTAPRAVAH/backend/bulletin_{bulletin['time_slot']}.mp4"
    
    # Text-to-Speech Processing using Microsoft Edge TTS
    voice = "mr-IN-AarohiNeural" if is_female else "mr-IN-ManoharNeural"
    subprocess.run(["python", "-m", "edge_tts", "--voice", voice, "--text", script, "--write-media", out_audio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    
    # Alternating Synthetic Anchors
    anchor_name = "anchor_female.mp4" if is_female else "anchor.mp4"
    anchor_mp4 = f"c:/VARTAPRAVAH/backend/{anchor_name}"
    
    # Overlay FFmpeg Video PiP Logic
    cmd = [
        "ffmpeg", "-y", 
        "-stream_loop", "-1", "-i", anchor_mp4,
        "-loop", "1", "-i", "c:/VARTAPRAVAH/backend/studio.jpg",
        "-i", "c:/VARTAPRAVAH/backend/logo.png",
        "-i", out_audio,
        "-filter_complex", "[0:v]colorkey=0x00FF00:0.3:0.2,scale=1280:720[anchor]; [1:v][anchor]overlay=(W-w)/2:(H-h)/2[base]; [2:v]scale=250:-1[logoscale]; [base][logoscale]overlay=W-w-50:50[outv]",
        "-map", "[outv]", "-map", "3:a",
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest", out_video
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Successfully compiled: {out_video}\n")

if __name__ == "__main__":
    print("---------------------------------------")
    print("VARTAPRAVAH AUTOMATED DAILY BATCH GEN")
    print("---------------------------------------")
    print("Fetching global headlines for batch generation...")
    headlines = fetch_news()
    
    for idx, bulletin in enumerate(BULLETINS):
        is_female_anchor = (idx % 2 == 1) # Alternate dynamically
        selected_news = headlines[idx % len(headlines)]
        script = generate_script(selected_news, bulletin, is_female=is_female_anchor)
        generate_video(script, bulletin, is_female=is_female_anchor)
        
    print("---------------------------------------")
    print("Batch Generation Complete! All 5 bulletins ready in backend directory.")
