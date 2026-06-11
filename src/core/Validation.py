import asyncio
from src.frontend.agents.Agent import BaseAgent


class Validation:

    def __init__(self, SpecAgent : BaseAgent):
        self.agent = SpecAgent
        self.agent.name = "Validation"
        self.agent.instructions = f"read instructions in info/instruction.md"

    async def run(self, input : str):
        result = self.agent.run(input)
        return result