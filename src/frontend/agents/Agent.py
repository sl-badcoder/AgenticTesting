import asyncio


class BaseAgent:
    def __init__(self, model : str, instructions: str, name: str) -> None:
        self.model = model
        self.instructions = instructions
        self.name = name

    async def run(self, input: str) -> str | None:
        pass

    def get_type(self) -> str:
        return self.type

