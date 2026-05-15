from typing import Any, Coroutine

from agents import Agent, Runner

class Reviewer:

    def __init__(self):
        self.agent = Agent(
            name="Reviewer",
            instructions="Read the file in info/review.md",
            model="gpt-5.5"
        )

    async def review(self, path) -> int | None:
        result = await Runner.run(self.agent, f"Inspect the files in {path}")
        try:
            score = int(result.final_output)
            return score
        except ValueError:
            print("Reviewer did not return a numeric score between 0-100")