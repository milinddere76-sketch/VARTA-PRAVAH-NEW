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
                        "You are an expert senior Marathi news anchor and journalist at Varta Pravah. "
                        "Your task is to convert raw news headlines/stories into a formal, grammatically perfect, and meaningful Marathi news script. "
                        "Rules:\n"
                        "1. Write in elegant, formal, and official Marathi vocabulary (शुद्ध आणि अधिकृत मराठी).\n"
                        "2. Ensure the sentence structure is natural, fluent, and highly professional for a television broadcast.\n"
                        "3. Do NOT include any English greetings, intro phrases, or meta-commentary (e.g. 'Sure, here is your script...').\n"
                        "4. Do NOT use any Markdown formatting, bolding (e.g. **text**), bullets, lists, asterisk symbols (*), or header tags. Output ONLY clean, raw Devanagari paragraph text.\n"
                        "5. Use standard Marathi punctuation and dandas (।) for natural voice pauses.\n"
                        "6. Structure the script with a strong opening (नमस्कार, मी आहे आपला AI रिपोर्टर...), a detailed body summarizing the key stories, and a professional closing (धन्यवाद, पाहत राहा वार्ता प्रवाह)."
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
