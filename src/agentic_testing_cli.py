import argparse
import asyncio

from src.core.agentic_testing import AgenticTestingConfig, AgenticTestingRunner
from src.core.project_profiles import PROJECT_PROFILES, get_project_profile
from src.frontend.llm.factory import create_llm_provider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Improve a repository's tests with an agent pipeline until a target "
            "line coverage percentage is reached."
        )
    )
    parser.add_argument("repo", help="Repository path to improve.")
    parser.add_argument(
        "target_coverage",
        type=int,
        help="Target line coverage percentage, from 0 to 100.",
    )
    parser.add_argument(
        "--provider",
        choices=["fake", "llama.cpp", "huggingface", "openai", "anthropic"],
        default="fake",
        help="Model provider used by analyzer, planner, implementer, and reviewer.",
    )
    parser.add_argument("--model-path", help="Path to a GGUF model for llama.cpp.")
    parser.add_argument("--model-id", help="Hugging Face model id.")
    parser.add_argument("--model", help="API model name for OpenAI or Anthropic.")
    parser.add_argument("--device", help="Hugging Face device, for example cpu, mps, cuda.")
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--implementer-max-steps", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--n-ctx", type=int, default=4096)
    parser.add_argument("--n-threads", type=int)
    parser.add_argument(
        "--project-profile",
        choices=sorted(PROJECT_PROFILES),
        default="python-pytest",
        help="Project and test stack profile.",
    )
    parser.add_argument(
        "--test-framework",
        default="",
        help="Optional test framework preference, such as xUnit or GoogleTest.",
    )
    parser.add_argument(
        "--coverage-command",
        default="",
        help="Coverage command to run inside the target repository.",
    )
    parser.add_argument(
        "--allow-command",
        action="append",
        default=["pytest"],
        help="Command executable the implementer may run. Can be passed multiple times.",
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

    if args.provider == "openai":
        return {
            "type": "openai",
            "model": args.model or "gpt-4.1-mini",
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
        }

    if args.provider == "anthropic":
        return {
            "type": "anthropic",
            "model": args.model or "claude-3-5-haiku-latest",
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
        }

    return {
        "type": "fake",
        "responses": [
            "Fake analyzer summary.",
            "Fake test improvement plan.",
            '{"actions": [], "final": "Fake implementer made no changes."}',
            "Fake reviewer feedback.",
        ],
    }


async def main() -> None:
    args = parse_args()
    if not 0 <= args.target_coverage <= 100:
        raise SystemExit("target_coverage must be between 0 and 100.")

    provider = create_llm_provider(build_provider_config(args))
    profile = get_project_profile(args.project_profile)
    runner = AgenticTestingRunner(
        config=AgenticTestingConfig(
            repository_path=args.repo,
            target_line_coverage=args.target_coverage,
            max_iterations=args.max_iterations,
            coverage_command=args.coverage_command or profile.coverage_command,
            allowed_commands=tuple(set(args.allow_command) | set(profile.allowed_commands)),
            implementer_max_steps=args.implementer_max_steps,
            project_profile=args.project_profile,
            test_framework=args.test_framework or profile.test_framework,
        ),
        provider=provider,
    )
    result = await runner.run()

    print(f"Final line coverage: {result.final_line_coverage}%")
    print(f"Target line coverage: {result.target_line_coverage}%")
    print(f"Reached target: {result.reached_target}")
    print(f"Iterations: {len(result.iterations)}")


if __name__ == "__main__":
    asyncio.run(main())
