import os

def generate_script(data):
    """
    Generates a professional Marathi news script with correct gender grammar.
    Input data tuple: (news_items, bulletin_type, is_breaking, anchor_gender)
    """
    news_items, bulletin_type, is_breaking, anchor_gender = data

    # 1. Gender-specific Introduction
    if anchor_gender == "female":
        intro = "नमस्कार, मी तुमची बातमीदार आहे."
    else:
        intro = "नमस्कार, मी तुमचा बातमीदार आहे."

    # 2. Bulletin Header
    script = f"{intro}\nअथक परिश्रमानंतर {bulletin_type} सुरु होत आहे.\n\n"

    # 3. Breaking News Alert
    if is_breaking:
        script += "📢 महत्वाची ब्रेकिंग न्यूज! आताची सर्वात मोठी बातमी समोर येत आहे.\n\n"

    # 4. News Content Iteration
    # If news_items is a list of dicts, extract headlines; if it's a single dict, use it.
    if isinstance(news_items, list):
        for i, n in enumerate(news_items[:5], 1):
            headline = n.get("headline", n) if isinstance(n, dict) else n
            script += f"{i}. {headline}\n"
    else:
        headline = news_items.get("headline", news_items) if isinstance(news_items, dict) else news_items
        script += f"१. {headline}\n"

    # 5. Professional Closing
    script += "\nपाहत राहा 'वार्ताप्रवाह'. धन्यवाद!"

    return script
