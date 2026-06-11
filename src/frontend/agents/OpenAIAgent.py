from agents import Agent, Runner

from src.frontend.agents.Agent import BaseAgent


class OpenAIAgent (BaseAgent):
    def __init__(self, name: str, instructions: str, model: str) -> None:
        super().__init__(model, instructions, name)

        self.agent = Agent(
            name=self.name,
            instructions=self.instructions,
            model=self.model
        )

    async def run(self, input : str) -> str | None:

        try:
            result = await Runner.run(self.agent, input)
        except:
            print("Result could not be loaded")
            return None

        return result.final_output

