"""Per-million-token pricing for closed-source providers, USD.

Sources verified at time of commit:
- Anthropic: docs.claude.com pricing page
- OpenAI:    platform.openai.com/docs/pricing
- Google:    ai.google.dev/gemini-api/docs/pricing

Pricing changes over time. We log token counts exactly; cost is
recomputed from this table at analysis time, so when the table is
updated, historical bills can be recomputed if needed.
"""

# (input_per_mtok, output_per_mtok) in USD
PRICING: dict[str, tuple[float, float]] = {
    # Anthropic — pinned snapshot IDs (what the API receives and what we log)
    "claude-opus-4-7":                    (5.00, 25.00),
    "claude-opus-4-6":                    (5.00, 25.00),
    "claude-sonnet-4-6-20250620":         (3.00, 15.00),
    "claude-haiku-4-5-20251001":          (1.00,  5.00),

    # OpenAI — pinned snapshot IDs (what the API receives and what we log)
    # Batch API pricing is 50% of real-time; cost is logged from actual usage.
    "gpt-5-2025-08-07":         (2.50, 15.00),   # GPT-5.4 (project alias)
    "gpt-5.4":                  (2.50, 15.00),
    "gpt-5-mini-2025-08-07":    (0.75,  4.50),   # GPT-5.4-mini (project alias)
    "gpt-5.4-mini":             (0.75,  4.50),

    # Google Gemini (standard context <= 200K tokens)
    "gemini-2.5-pro":           (1.25, 10.00),
    "gemini-2.5-flash":         (0.30,  2.50),
}


def compute_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
    """Return USD cost. None for unpriced models (open-source)."""
    if model_id not in PRICING:
        return None
    in_per_m, out_per_m = PRICING[model_id]
    return (input_tokens * in_per_m + output_tokens * out_per_m) / 1_000_000