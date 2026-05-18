def clean_marathi(text):
    """
    Optimizes Marathi text for professional TTS pronunciation.
    Preserves authentic Marathi script while enhancing readability.
    """
    # Replace common abbreviations with Marathi equivalents
    replacements = {
        "भारत": "भारत देश",
        "₹": "रुपये",
        "%": "टक्के",
        "cm": "सेंटीमीटर",
        "pm": "पंतप्रधान",
        "$": "डॉलर",
        "km": "किलोमीटर",
        "IND": "भारत",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    # Moderate pausing - collapse multiple dandas and add single space
    # This helps TTS pronunciation without corrupting the Marathi text
    text = text.replace("।।।", "। ")
    text = text.replace("।।", "। ")
    
    return text
