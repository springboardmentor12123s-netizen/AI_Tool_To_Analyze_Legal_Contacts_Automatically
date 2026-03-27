def extract_clauses(text):
    clauses = text.split("\n\n")
    return [c.strip() for c in clauses if len(c.strip()) > 30]