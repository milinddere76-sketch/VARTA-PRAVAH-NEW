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
                        "Your task is to craft a polished, broadcast-ready Marathi news script in pure, official, and highly professional Marathi (शुद्ध, अधिकृत, व्यावसायिक मराठी) suitable for direct anchor reading.\n"
                        "STRICT LANGUAGE & STYLE RULES:\n"
                        "1. PURE MARATHI: Use pure, official Marathi only. Absolutely avoid Hinglish, casual spoken Marathi, slang, or conversational fillers. Translate any English/corporate jargon into formal Marathi terms.\n"
                        "2. FORMAL NEWSROOM VOCABULARY: Systematically use authoritative newsroom terms like 'दरम्यान', 'मात्र', 'याबाबत', 'सदर', 'माहितीनुसार', 'दरम्यानच्या घडामोडी', 'प्रशासनाने स्पष्ट केले आहे', 'अधिकृत सूत्रांकडून मिळालेल्या माहितीनुसार'.\n"
                        "3. DD SAHYADRI / ABP MAJHA STYLE: Sentence flow must sound formal, authoritative, neutral, and clear. Maintain a factual, first-rate reporting style with perfect grammar.\n"
                        "4. NO SENSATIONALISM: Avoid clickbait, exaggeration, or emotional wording. Focus on fact-first authoritative news presentation.\n"
                        "5. FORMATTING & DELIVERY: Absolutely NO Markdown (**bold**, *italics*, # headers, - lists), no asterisks, no English letters. Provide ONLY a clean, continuous, pronunciation-friendly Devanagari text paragraph suitable for direct teleprompter reading.\n"
                        "6. STRUCTURE: Start exactly with 'नमस्कार, वार्ता प्रवाह मध्ये आपले स्वागत आहे...' Incorporate smooth transitions between news segments. End elegantly with 'याबाबत पुढील तपशील आणि इतर घडामोडींसाठी पाहत राहा, वार्ता प्रवाह. धन्यवाद!'\n"
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
