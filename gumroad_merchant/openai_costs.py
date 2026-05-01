from __future__ import annotations

from dataclasses import dataclass


TOKENS_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class TokenPricing:
    input_per_million: float
    output_per_million: float


STANDARD_TOKEN_PRICING: dict[str, TokenPricing] = {
    "gpt-5.4-nano": TokenPricing(input_per_million=0.20, output_per_million=1.25),
    "gpt-5.4-mini": TokenPricing(input_per_million=0.75, output_per_million=4.50),
}

DAILY_RUN_SIZES: tuple[tuple[int, int], ...] = (
    (10_000, 1_000),
    (20_000, 2_000),
    (50_000, 5_000),
)


def estimate_token_cost(input_tokens: int, output_tokens: int, model: str = "gpt-5.4-nano") -> float:
    pricing = STANDARD_TOKEN_PRICING[model]
    return (
        (input_tokens / TOKENS_PER_MILLION) * pricing.input_per_million
        + (output_tokens / TOKENS_PER_MILLION) * pricing.output_per_million
    )


def format_cost(amount: float) -> str:
    if amount < 0.01:
        return f"${amount:.4f}".rstrip("0").rstrip(".")
    return f"${amount:.3f}".rstrip("0").rstrip(".")


def daily_run_cost_rows() -> list[dict[str, str | int]]:
    return [
        {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "nano": format_cost(estimate_token_cost(input_tokens, output_tokens, "gpt-5.4-nano")),
            "mini": format_cost(estimate_token_cost(input_tokens, output_tokens, "gpt-5.4-mini")),
        }
        for input_tokens, output_tokens in DAILY_RUN_SIZES
    ]
