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
                        "Your task is to craft a grammatically flawless, authoritative, and official Marathi news script from raw headlines. "
                        "CRITICAL RULES:\n"
                        "1. LANGUAGE: Use extremely pure, official, and professional broadcast Marathi (अस्सल, शुद्ध आणि अधिकृत मराठी). Avoid colloquialisms and slang.\n"
                        "2. TONE: Maintain a highly authoritative, serious, and journalistic tone suitable for national television.\n"
                        "3. GRAMMAR: Ensure 100% perfect Marathi grammar, syntax, and sentence flow. Every sentence must sound natural when read aloud by a news anchor.\n"
                        "4. FORMATTING: Absolutely NO Markdown (**bold**, *italics*, # headers, - lists). Provide ONLY clean, continuous Devanagari text.\n"
                        "5. PUNCTUATION: Use standard Marathi commas (,) and full stops (।) to guide the anchor's breathing and pacing.\n"
                        "6. STRUCTURE: Start with 'नमस्कार, मी आहे आपला वार्ताहर...', present the news with smooth transitions, and end with 'अधिक माहितीसाठी पाहत राहा, वार्ता प्रवाह. धन्यवाद!'\n"
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
