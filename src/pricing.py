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
    # Anthropic, pinned snapshot IDs (what the API receives and what we log)
    "claude-opus-4-7":                    (5.00, 25.00),
    "claude-opus-4-6":                    (5.00, 25.00),
    "claude-sonnet-4-6":                  (3.00, 15.00),   # no date suffix, verified via models.list(); -20250620 404s
    "claude-haiku-4-5-20251001":          (1.00,  5.00),

    # OpenAI, pinned snapshot IDs (what the API receives and what we log)
    # Batch API pricing is 50% of real-time; cost is logged from actual usage.
    #
    # CORRECTED 2026-08-05 (terminology/cost audit): the previous entries here
    # (2.50, 15.00) / (0.75, 4.50) were the "gpt-5.4" / "gpt-5.4-mini" family's
    # rates, not "gpt-5"'s, a stale mislabeling (src/pricing.py's own prior
    # comment called gpt-5-2025-08-07 a "GPT-5.4 (project alias)"; PROJECT_BRIEF.md
    # §-level provider table still says "GPT-5.4"). "gpt-5.4" is never actually
    # sent as a model string anywhere in this codebase (grepped: only appeared
    # as a second, unused PRICING key). Every real request uses the literal
    # pinned snapshot "gpt-5-2025-08-07", and that snapshot's OWN model page
    # (https://developers.openai.com/api/docs/models/gpt-5, fetched via curl
    # 2026-08-05. Page confirms "gpt-5-2025-08-07" directly, showing
    # Input $1.25 / Cached $0.125 / Output $10.00, i.e. the "gpt-5" family row,
    # NOT "gpt-5.4"'s $2.50/$15.00) is the authoritative price for what this
    # project actually calls. Same check for gpt-5-mini-2025-08-07's own model
    # page (https://developers.openai.com/api/docs/models/gpt-5-mini): $0.25 /
    # $0.025 / $2.00, not "gpt-5.4-mini"'s $0.75/$4.50. Batch API price on both
    # pages confirmed at exactly 50% of these (cross-checked against
    # https://developers.openai.com/api/docs/pricing's raw embedded pricing
    # table and https://help.openai.com/en/articles/9197833-batch-api-faq).
    # This was a real, if modest, overstatement of every dollar figure
    # anywhere in this project that cites GPT-5/-mini cost (including already-
    # logged `cost_usd` on real batch rows, computed via this table at
    # ingestion time, see analysis/OPENAI_COST_AND_BILLING.md for the
    # reconciliation). The dead "gpt-5.4"/"gpt-5.4-mini" alias keys are removed,
    # not fixed in place, since neither is ever used as an actual
    # model_id in this codebase and keeping them invites the same confusion
    # again.
    "gpt-5-2025-08-07":         (1.25, 10.00),
    "gpt-5-mini-2025-08-07":    (0.25,  2.00),

    # Google Gemini (standard context <= 200K tokens)
    # gemini-2.5-pro/-flash retired 2026-07-14: "no longer available to new
    # users" (404 on live generate_content calls despite still appearing in
    # models.list() as Stable), replaced with the 3.1 generation. Pricing
    # verified 2026-07-14 against ai.google.dev/gemini-api/docs/pricing plus
    # two independent secondary sources (all agreed).
    "gemini-3.1-pro-preview":   (2.00, 12.00),   # preview, no non-preview Pro-class model exists right now
    "gemini-3.1-flash-lite":    (0.25,  1.50),   # GA/stable
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