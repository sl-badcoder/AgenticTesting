from agents import Agent


class Plan:
    def __init__(self):
        self.agent = Agent(
            name="Planner",
            instructions="You are a Planner Agent."
                         "You will Plan the testing structure.",
            model="gpt-5.5"
        )

    async def run(self, path : str):
