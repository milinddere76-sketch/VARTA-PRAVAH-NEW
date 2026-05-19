def clean_hindi(text):
    """
    Optimizes Hindi text for professional TTS pronunciation.
    Preserves authentic Hindi script while enhancing readability.
    """
    # Replace common abbreviations with Hindi equivalents
    replacements = {
        "₹": "रुपये",
        "%": "प्रतिशत",
        "cm": "सेंटीमीटर",
        "pm": "प्रधानमंत्री",
        "$": "डॉलर",
        "km": "किलोमीटर",
        "IND": "भारत",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    # Moderate pausing - collapse multiple dandas and add single space
    # This helps TTS pronunciation without corrupting the Hindi text
    text = text.replace("।।।", "। ")
    text = text.replace("।।", "। ")
    
    return text

# Alias for backward compatibility if any other package/service expects clean_marathi
def clean_marathi(text):
    return clean_hindi(text)

