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
                        "You are the Chief News Editor and Senior Anchor for 'Varta Pravah' (वार्ता प्रवाह) television network. "
                        "Your task is to craft a completely meaningful, highly professional, and grammatically flawless Marathi news bulletin from the provided raw headlines.\n"
                        "CRITICAL RULES:\n"
                        "1. MEANINGFUL EXPANSION: Do not just list the headlines. Expand them into complete, fully resolved sentences (पूर्ण वाक्ये). Ensure every news story makes logical sense and provides complete context.\n"
                        "2. PURE MARATHI: Use highly official, pure, and professional broadcast Marathi vocabulary (अस्सल, शुद्ध आणि प्रमाण मराठी भाषा). Translate any English words or corporate jargon into their formal Marathi equivalents.\n"
                        "3. FLAWLESS GRAMMAR: Ensure 100% perfect Marathi grammar and syntax. Verbs must match subjects perfectly, and sentences must flow naturally for a professional TV news anchor (उदा. 'आले आहे', 'करण्यात आले', 'झाले').\n"
                        "4. TRANSITIONS: Use proper Marathi connecting words between news stories (उदा. 'याव्यतिरिक्त', 'दुसरीकडे', 'महत्त्वाची बातमी म्हणजे') so the broadcast flows seamlessly.\n"
                        "5. FORMATTING: Absolutely NO Markdown (**bold**, *italics*, # headers, - lists), no asterisks, no English letters. Provide ONLY a clean, continuous Devanagari text paragraph.\n"
                        "6. STRUCTURE: Start exactly with 'नमस्कार, वार्ता प्रवाह मध्ये आपले स्वागत आहे...' Then deliver the news in detail. End elegantly with 'सविस्तर बातम्यांसाठी पाहत राहा, वार्ता प्रवाह. धन्यवाद!'\n"
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
