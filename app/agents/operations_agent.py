from app.agents.base_agent import BaseContractAgent
from app.agents.roles import AGENT_ROLES


class OperationsAgent(BaseContractAgent):

    def __init__(self):
        super().__init__(
            role_name="operations",
            role_config=AGENT_ROLES["operations"]
        )