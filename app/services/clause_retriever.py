from app.services.vector_store import retrieve_clauses


def get_agent_context(agent_type, namespace="contracts"):

    queries = {
        "legal": "termination indemnity governing law dispute resolution",
        "finance": "payment penalties liability damages cost financial",
        "compliance": "data protection privacy regulatory compliance laws",
        "operations": "scope deliverables responsibilities timeline obligations"
    }

    query = queries.get(agent_type, "contract clauses")

    clauses = retrieve_clauses(query, namespace=namespace)

    return "\n".join(clauses)