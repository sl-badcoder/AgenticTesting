from typing import Any, Coroutine

from src.frontend.agents.Agent import BaseAgent


class Plan:

    def __init__(self, SpecAgent : BaseAgent):
        self.agent = SpecAgent
        self.agent.instructions = f"read instructions in info/planner.md"
        self.agent.name = "Planner"

    def run(self, input : str):
        result = self.agent.run(input=input)
        return result

