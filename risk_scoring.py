def calculate_risk_score(text: str):
    text = text.lower()
    score = 0

    keywords = {
    "high risk": 30,
    "breach": 15,
    "unclear": 10,
    "undefined": 10,
    "data breach": 20,
    "liability": 10,
    "privacy": 10,
    "intellectual property": 10,
    "penalty": 10,
}

    for word, points in keywords.items():
        if word in text:
            score += points

    return min(score, 100)
