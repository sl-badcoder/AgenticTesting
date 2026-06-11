import argparse
import asyncio

from src.core.local_coding_agent import LocalCodingAgent
from src.core.workspace import RepositoryWorkspace
from src.frontend.llm.factory import create_llm_provider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a constrained local coding agent against a repository."
    )
    parser.add_argument("task", help="Coding task for the local model.")
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository root the agent may inspect and edit.",
    )
    parser.add_argument(
        "--provider",
        choices=["llama.cpp", "huggingface", "fake"],
        default="fake",
        help="Model provider to use.",
    )
    parser.add_argument("--model-path", help="Path to a GGUF model for llama.cpp.")
    parser.add_argument("--model-id", help="Hugging Face model id.")
    parser.add_argument("--device", help="Hugging Face device, for example cpu, mps, cuda.")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--n-ctx", type=int, default=4096)
    parser.add_argument("--n-threads", type=int)
    parser.add_argument(
        "--allow-command",
        action="append",
        default=["pytest"],
        help="Command executable the agent may run. Can be passed multiple times.",
    )
    return parser.parse_args()


def build_provider_config(args: argparse.Namespace) -> dict[str, object]:
    if args.provider == "llama.cpp":
        if not args.model_path:
            raise SystemExit("--model-path is required for llama.cpp.")
        return {
            "type": "llama.cpp",
            "model_path": args.model_path,
            "n_ctx": args.n_ctx,
            "n_threads": args.n_threads,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
        }

    if args.provider == "huggingface":
        if not args.model_id:
            raise SystemExit("--model-id is required for huggingface.")
        return {
            "type": "huggingface",
            "model_id": args.model_id,
            "device": args.device,
            "max_new_tokens": args.max_tokens,
            "temperature": args.temperature,
        }

    return {
        "type": "fake",
        "responses": [
            '{"actions": [{"tool": "list_files"}], "final": null}',
            '{"actions": [], "final": "Fake run completed after listing files."}',
        ],
    }


async def main() -> None:
    args = parse_args()
    provider = create_llm_provider(build_provider_config(args))
    workspace = RepositoryWorkspace(
        root=args.repo,
        allowed_commands=tuple(args.allow_command),
    )
    agent = LocalCodingAgent(
        provider=provider,
        workspace=workspace,
        max_steps=args.max_steps,
    )
    result = await agent.run(args.task)

    if result.final:
        print(result.final)
        return

    print("The agent stopped before returning a final answer.")
    if result.steps:
        print("Last observations:")
        for observation in result.steps[-1].observations:
            print(f"- {observation}")


if __name__ == "__main__":
    asyncio.run(main())
