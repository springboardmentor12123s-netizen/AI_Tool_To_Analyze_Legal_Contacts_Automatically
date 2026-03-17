# app/agents/roles.py

AGENT_ROLES = {

    "compliance": {
        "purpose": "Analyze the contract for regulatory compliance and legal adherence.",
        "focus_areas": [
            "data protection",
            "regulatory obligations",
            "mandatory clauses",
            "legal enforceability"
        ],
        "output_format": {
            "identified_risks": [],
            "missing_clauses": [],
            "recommendations": []
        }
    },

    "finance": {
        "purpose": "Evaluate financial clauses and monetary exposure.",
        "focus_areas": [
            "payment terms",
            "penalties",
            "liability caps",
            "financial exposure"
        ],
        "output_format": {
            "financial_risks": [],
            "liability_issues": [],
            "recommendations": []
        }
    },

    "legal": {
        "purpose": "Interpret legal language and identify legal risks.",
        "focus_areas": [
            "termination clauses",
            "indemnification",
            "dispute resolution",
            "governing law"
        ],
        "output_format": {
            "legal_risks": [],
            "ambiguous_clauses": [],
            "recommendations": []
        }
    },

    "operations": {
        "purpose": "Assess operational feasibility and delivery risks.",
        "focus_areas": [
            "scope of services",
            "performance obligations",
            "timelines",
            "resource commitments"
        ],
        "output_format": {
            "operational_risks": [],
            "unclear_scope": [],
            "recommendations": []
        }
    }
}