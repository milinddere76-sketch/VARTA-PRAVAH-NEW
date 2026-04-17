def is_breaking_news(news_text):
    """
    Heuristic to determine if a news item qualifies as 'Breaking News'.
    Currently based on length (>12 words) or specific Marathi keywords.
    """
    # Splitting by spaces to count words
    word_count = len(news_text.split())
    
    # Urgent Marathi keywords that trigger breaking status
    keywords = ["ब्रेकिंग", "महत्वाची", "आताची", "धक्कादायक", "मोठी", "BREAKING"]
    has_keyword = any(k in news_text for k in keywords)

    return word_count > 12 or has_keyword
