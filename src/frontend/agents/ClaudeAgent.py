from anthropic import Anthropic
import os
from src.frontend.agents.Agent import BaseAgent


class ClaudeAgent (BaseAgent):
    def __init__(self, model : str, instructions: str, type : str, max_tokens=1024):
        super().__init__(model, instructions, type)
        try:
            self.client = Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )
        except:
            print("Define ANTHROPIC_API_KEY")

        self.max_tokens = max_tokens

    async def run(self, input : str) -> Anthropic:
        try:
            message = await self.client.messages.create(
                max_tokens= self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": input,
                    }
                ],
                model=self.model,
            )
        except Exception:
            print("ClaudeAgent failed")
            return None
        return message.content