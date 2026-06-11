from src.frontend.agents.Agent import BaseAgent


class Reviewer:

    def __init__(self, SpecAgent : BaseAgent):
        self.agent = SpecAgent
        self.agent.instructions = f"read instructions in info/review.md"
        self.agent.name = "Reviewer"

    async def review(self, input : str) -> int | None:
        result = self.agent.run(input=input)
        try:
            score = int(result)
            return score
        except ValueError:
            print("Reviewer did not return a numeric score between 0-100")