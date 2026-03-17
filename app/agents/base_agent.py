import os
import json
from google import genai

class BaseContractAgent:

    MODEL_NAME = "gemini-2.0-flash"

    def __init__(self, role_name, role_config):

        self.role_name = role_name
        self.role_config = role_config

        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


    def build_prompt(self, contract_text):

        return f"""
You are an expert {self.role_name} contract analyst.

Analyze the contract clauses below and identify critical issues.

Return STRICT JSON.

Each list MUST contain bullet insights.
Do NOT return empty sections.

JSON FORMAT:

{json.dumps(self.role_config["output_format"], indent=2)}

Contract Clauses:
{contract_text}

Rules:
- Maximum 3 bullet points per section
- Each bullet must be short
- Focus only on important risks
"""


    def analyze(self, contract_text):

        prompt = self.build_prompt(contract_text)

        response = self.client.models.generate_content(
            model=self.MODEL_NAME,
            contents=prompt
        )

        text = response.text.strip()

        try:
            return json.loads(text)

        except:
            return {"error": text}