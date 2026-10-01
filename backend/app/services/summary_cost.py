OPENAI_PRICES_PER_MILLION = {
    "gpt-5.6-luna": (0.20, 1.20),
    "gpt-5.6-terra": (2.00, 12.00),
}


def estimated_cost_usd(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> float | None:
    if provider == "ollama":
        return 0.0
    prices = OPENAI_PRICES_PER_MILLION.get(model) if provider == "openai" else None
    if prices is None:
        return None
    return round((input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000, 8)
