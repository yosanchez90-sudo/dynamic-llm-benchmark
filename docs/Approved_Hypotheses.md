Hypotheses
Each hypothesis is paired with the research question and the test that will support or reject it.
H1 (RQ1): Mutation scores produced by 8 LLMs on the dynamic benchmark will be lower than the scores on the static benchmarks, after controlling for cyclomatic complexity (to hold cyclomatic complexity constant and run fair comparisons).
Test 1: run paired comparison, Wilcoxon signed-rank across model–problem pairs.
Note: problem is a specific code function or coding task that is being mutated and tested.
Pair: Model-Problem will have:
- Mutation score on the static benchmark
- Mutation score on the dynamic benchmark
Test 2: Comparison between ULT vs PLT. Observational contamination signal: same models, decontaminated vs leaked equivalents. Having Mutation score as the main metric.
H2 (RQ1): After fine-tuning a small open-source LLM on a static benchmark, its mutation-score on the static benchmark will be larger than on the dynamic benchmark (even after applying changes).
Test: validate differences on mutation scores (pre vs. post fine-tuning), considering (static vs. dynamic).
H3 (RQ2): Mean mutation score will keep decreasing (or stay the same) from L1 to L4 across all evaluated LLMs, it will never go back up.
Test: Spearman ρ between tier index and mutation score, per model and for all models combined.
H4 (RQ3): The gap between static and dynamic mutation scores will be larger at L1–L2 than at L3–L4.
Test: See if there is an interaction between tier and benchmark in a regression that treats different LLMs as a random source of variation (so results are not driven by any single model).
H5 (RQ4): Across N=5 independent instantiations of the dynamic benchmark, the Kendall’s τ (A measure of rank correlation between two rankings) between LLM rankings will exceed 0.7 (yielding a strong positive correlation. Indicating stability across random instantiations)
Test: pairwise Kendall’s τ across instantiations, each time with different random seeds (or different random variations of test cases, mutation operators, etc.), so, each instantiation produces its own set of mutation scores for the LLMs.
H6 (RQ5). Test-generation mutation score on the dynamic benchmark will correlate positively but imperfectly with code-generation Pass@1 on a proxy benchmark, and this correlation will be weaker than the correlation between static-benchmark mutation score and the same proxy. Test: Pearson r and Spearman ρ between scores.
