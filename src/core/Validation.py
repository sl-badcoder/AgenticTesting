import asyncio

from agents import Agent, Runner


class Validation:

    def __init__(self):
        self.agent = Agent(
            name="Validator",
            instructions="You will validate all the code changes. You will check a",
            model="gpt-5.5"
        )

    async def run(self, path : str):
        result = await  Runner.run(self.agent, f"Validate the file created in {path}")
        return result