import os
import requests
from groq import Groq
from gtts import gTTS
import subprocess
from dotenv import load_dotenv

# Initialize Environment & AI Clients
load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 1. Dynamic News Fetcher
def fetch_news():
    api_key = os.getenv("WORLD_NEWS_API_KEY")
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        return {"headline": "[MOCK] Maharashtra Update", "description": "Mock news description for the batch gen."}
    
    url = f"https://api.worldnewsapi.com/search-news?api-key={api_key}&text=Maharashtra&language=mr&number=1"
    try:
        r = requests.get(url)
        data = r.json()
        if data.get("news"):
            news = data["news"][0]
            return {"headline": news["title"], "description": news["text"][:500]}
    except Exception as e:
        print(f"News fetch error: {e}")
    return {"headline": "Maharashtra Political Update", "description": "New developments in the state assembly regarding the budget."}

# 2. Scheduling Logic Defined by User
BULLETINS = [
    {"name": "सकाळ", "style": "Top headlines and morning updates", "time_slot": "6_AM"},
    {"name": "दुपार", "style": "Updates and breaking news", "time_slot": "12_PM"},
    {"name": "संध्याकाळ", "style": "Detailed reporting", "time_slot": "6_PM"},
    {"name": "प्राइम टाइम", "style": "Deep analysis and critical insights", "time_slot": "9_PM"},
    {"name": "रात्री", "style": "Summary of the day's major events", "time_slot": "11_PM"}
]

# 3. AI Script Engine
def generate_script(news_data, bulletin):
    system_prompt = f"""तुम्ही एक व्यावसायिक Marathi वृत्तवाहिनीचे अँकर आहात. आता '{bulletin['name']}' बुलेटिनची वेळ आहे.

नियम:
* भाषा पूर्णपणे शुद्ध आणि अधिकृत Marathi असावी
* उच्चार स्पष्ट आणि प्रभावी असावेत
* बातमी सादरीकरणाचा वेग मध्यम असावा
* आवाजात आत्मविश्वास आणि गांभीर्य असावे
* सादरीकरण पुर्णपणे '{bulletin['style']}' या शैलीत असावे.
"""
    user_prompt = f"""बातमी:
{news_data['headline']} - {news_data['description']}

कृपया वरील बातमीसाठी 'Varta Pravah - {bulletin['name']}' या बुलेटिनची स्क्रिप्ट तयार करा:"""

    print(f"Generating Script for: {bulletin['time_slot']}...")
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

# 4. Engine Generator (gTTS + FFmpeg)
def generate_video(script, bulletin):
    print(f"Synthesizing Audio & Video for {bulletin['time_slot']}...")
    out_audio = f"c:/VARTAPRAVAH/backend/output_audio_{bulletin['time_slot']}.mp3"
    out_video = f"c:/VARTAPRAVAH/backend/bulletin_{bulletin['time_slot']}.mp4"
    
    # Text-to-Speech
    tts = gTTS(text=script, lang='mr')
    tts.save(out_audio)
    
    # Overlay FFmpeg Video PiP Logic
    cmd = [
        "ffmpeg", "-y", 
        "-i", "c:/VARTAPRAVAH/backend/anchor.mp4",
        "-loop", "1", "-i", "c:/VARTAPRAVAH/backend/studio.jpg",
        "-i", out_audio,
        "-filter_complex", "[0:v]scale=1280:720[anchor]; [1:v][anchor]overlay=(W-w)/2:(H-h)/2[outv]",
        "-map", "[outv]", "-map", "2:a",
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
    
    for bulletin in BULLETINS:
        script = generate_script(headlines, bulletin)
        generate_video(script, bulletin)
        
    print("---------------------------------------")
    print("Batch Generation Complete! All 5 bulletins ready in backend directory.")
