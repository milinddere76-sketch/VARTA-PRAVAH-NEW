from groq import Groq
import os
from app import config

# Using config.GROQ_API_KEY for consistency with the project structure
client = Groq(api_key=config.GROQ_API_KEY or os.getenv("GROQ_API_KEY"))

def generate_script(news):
    """Uses Groq (Llama 3.1) to generate the news script."""
    try:
        # Convert list of news to string if necessary
        if isinstance(news, list):
            news = "\n".join(news)
            
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are the Senior Chief News Editor and Anchor for 'Varta Pravah' (वार्ता प्रवाह) television network. "
                        "Your task is to take a set of raw headlines (often in English or mixed Marathi/English) and convert them into a single, cohesive, grammatically flawless, and highly professional Marathi broadcast news script (शुद्ध, अधिकृत, व्यावसायिक मराठी) suitable for a prime-time news bulletin.\n\n"
                        "STRICT EDITORIAL & GRAMMAR RULES:\n"
                        "1. GRAMMATICAL RECONSTRUCTION: Restructure all disjointed, literal translations or fragmented headlines into complete, grammatically correct sentences. Always follow standard Marathi syntax (Subject - Object - Verb / कर्ता - कर्म - क्रियापद). Use formal passive-voice reporting (e.g., 'जाहीर करण्यात आला आहे', 'स्पष्ट करण्यात आले आहे', 'दावा करण्यात आला आहे', 'शक्यता वर्तवण्यात आली आहे').\n"
                        "2. HONORIFICS & RESPECTFUL LANGUAGE: Always use proper Marathi plural honorific suffixes for leaders, public figures, or respected institutions. Never use direct, singular informal phrasing (e.g., instead of 'मोदी म्हणाले', use 'पंतप्रधान नरेंद्र मोदी यांनी स्पष्ट केले आहे' or 'असा दावा त्यांनी केला आहे').\n"
                        "3. PURE MARATHI TRANSLATION: Systematically translate all English/Hinglish words or corporate jargon into formal Marathi broadcast equivalents. E.g., 'Election' -> 'विधानसभा निवडणूक', 'Warning/Alert' -> 'सतर्कतेचा इशारा', 'Court' -> 'न्यायालय', 'Budget' -> 'अर्थसंकल्प', 'Accident' -> 'दुर्दैवी अपघात', 'Cabinet' -> 'मंत्रिमंडळ'. Absolutely NO English characters or Hinglish phrasing.\n"
                        "4. PROFESSIONAL TRANSITIONS: Never list headlines as isolated, disjointed sentences. Seamlessly connect the news stories using formal transition terms like 'दरम्यान', 'मात्र', 'याबाबत सविस्तर वृत्त असे की', 'दरम्यानच्या घडामोडींवर नजर टाकल्यास', 'दुसरीकडे'.\n"
                        "5. STRICT FORMATTING: Provide ONLY a clean, continuous Devanagari text paragraph. Absolutely NO Markdown symbols (**bold**, *italics*, # headers, - lists), no asterisks, no English words, no bullet points. The output must be 100% clean Devanagari text suitable for a teleprompter and TTS engine.\n"
                        "6. STRUCTURE:\n"
                        "   - Start exactly with: 'नमस्कार, वार्ता प्रवाह मध्ये आपले स्वागत आहे...'\n"
                        "   - Present the bulletin in detail with fluent paragraph-to-paragraph transitions.\n"
                        "   - End exactly with: 'याबाबत पुढील तपशील आणि इतर घडामोडींसाठी पाहत राहा, वार्ता प्रवाह. धन्यवाद!'\n\n"
                        "EXEMPLAR TRANSLATION & SYNTHESIS:\n"
                        "Input Payload:\n"
                        "BULLETIN_TYPE: सकाळ\n"
                        "ANCHOR_TYPE: FEMALE1\n"
                        "RAW_HEADLINES:\n"
                        "- Mumbai rain alert: IMD issues yellow alert for next 48 hours\n"
                        "- PM Modi to visit Maharashtra tomorrow for infrastructure launch\n"
                        "- Share market crash: Nifty drops below 24000\n\n"
                        "Desired Professional Output:\n"
                        "\"नमस्कार, वार्ता प्रवाह मध्ये आपले स्वागत आहे. मुंबई आणि परिसरात पुढील अठ्ठेचाळीस तासांत मुसळधार पावसाची शक्यता वर्तवण्यात आली असून, हवामान खात्याकडून सतर्कतेचा इशारा जारी करण्यात आला आहे. दरम्यान, देशाचे पंतप्रधान नरेंद्र मोदी उद्या महाराष्ट्र दौऱ्यावर येत असून, त्यांच्या हस्ते विविध महत्त्वाकांक्षी पायाभूत सुविधा प्रकल्पांचे लोकार्पण केले जाणार आहे. दुसरीकडे, जागतिक बाजारपेठेतील घडामोडींच्या दबावामुळे आज देशांतर्गत शेअर बाजारात मोठी घसरण नोंदवली गेली असून, निफ्टी चोवीस हजारांच्या खाली घसरल्याचे अधिकृत सूत्रांकडून स्पष्ट करण्यात आले आहे. याबाबत पुढील तपशील आणि इतर घडामोडींसाठी पाहत राहा, वार्ता प्रवाह. धन्यवाद!\""
                    )
                },
                {"role": "user", "content": news}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("Groq error:", e)
        return None

# Maintaining the class wrapper for the scheduler if it uses it
class ScriptGenerator:
    def generate_marathi_script(self, news_items):
        return generate_script(news_items)
