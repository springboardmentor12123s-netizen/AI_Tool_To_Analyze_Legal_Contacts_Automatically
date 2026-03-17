from app.agents.base_agent import BaseContractAgent
from app.agents.roles import AGENT_ROLES


class ComplianceAgent(BaseContractAgent):

    def __init__(self):
        super().__init__(
            role_name="compliance",
            role_config=AGENT_ROLES["compliance"]
        )