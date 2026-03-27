def calculate_risk_score(text: str):
    text = text.lower()
    score = 0

    keywords = {
        "undefined": 20,
        "not defined": 20,
        "unclear": 15,
        "liability": 20,
        "breach": 15,
        "data": 15,
        "confidentiality": 15,
        "payment": 10,
        "privacy": 10,
        "ip": 15,
        "intellectual property": 20
    }

    for word, points in keywords.items():
        if word in text:
            score += points

    return min(score, 100)