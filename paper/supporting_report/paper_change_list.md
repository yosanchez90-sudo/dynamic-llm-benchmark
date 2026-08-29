# Paper revision — change list

Every change below is either (a) a structural point raised by the supervisor,
(b) a vocabulary simplification, or (c) a broken sentence that must be fixed.

Quoted text is taken from the rendered PDF, so line breaks and hyphenation may
differ from the LaTeX source. Match on the sentence, not on whitespace.

---

## PART 1 — STRUCTURAL CHANGES (supervisor's points)

### 1.1 Name the benchmark: DyMuT

Introduce the name once, at first use in the abstract, then use it consistently.

**Rule for where to use it:** write **DyMuT** when referring to *this* benchmark.
Write **"dynamic benchmark"** only when referring to the general class of
dynamic benchmarks (for example in Related Work, when discussing DyVal or
LiveBench). Do not replace every occurrence mechanically.

Expand the acronym once, at first use: *DyMuT (Dynamic Mutation-based Testing)*.

**Title.** Consider changing to:

> DyMuT: A Dynamic, Template-Based Benchmark That Resists Contamination in
> LLM Unit-Test Generation

This is the standard form for a benchmark paper and puts the name in the title
where a reader will find it. The author's call.

### 1.2 Section 3 heading

`Methods` does not cover section 3.4 (Models). Rename the section:

> **3 BENCHMARK DESIGN AND EXPERIMENTAL SETUP**

This covers templates, instantiation, metrics, models, fine-tuning and
equivalent-mutant validation without moving anything.

### 1.3 Section 3.5 heading

FIND: `Fine-Tuning Setup (Causal Contamination Probe)`

REPLACE: `Fine-Tuning on ULT to Create Contamination`

### 1.4 Replace the introduction's RQ paragraph with a table column

The paragraph beginning "These objectives map onto five research questions
(RQ1–RQ5)" is dense and hard to follow. Delete it and replace with:

> These objectives map onto five research questions, tested by six
> pre-registered hypotheses. Table I lists each research question, the
> hypothesis that tests it, the prediction made, and the verdict reached.

Then **add an RQ column to Table I** as its first column, so the table becomes:
RQ | Hyp. | Prediction | Verdict.

Values for the new column:
- H1 Test 1 → RQ1
- H1 Test 2 → RQ1
- H2 → RQ1
- H2-supplementary → RQ1 (supplementary)
- H3 → RQ2
- H4 → RQ3
- H5 → RQ4
- H6 clause 1 → RQ5
- H6 clause 2 → RQ5

Add a one-line footnote under the table giving the five questions in short form,
so the table is self-contained:

> RQ1 contamination resistance vs a static benchmark; RQ2 effect of complexity
> tier; RQ3 whether overestimation is larger at low tiers; RQ4 stability of
> rankings across re-instantiations; RQ5 agreement with an external
> code-generation proxy.

This satisfies the request for a table and shortens the introduction.

### 1.5 Figures are too small to read in print

Regenerate all three figures with larger type. Requirements:

- axis labels, tick labels, legends and in-figure annotations at a size that
  stays readable when the figure is printed at column width on A4
- as a working target, no text smaller than about 7pt at final printed size
- Figure 2 is the worst case: four sub-panels, seven model labels each, plus an
  annotation box. Consider dropping to two panels (cross-family only, both
  metrics), since the canonical n=3 panels carry one message that the caption
  already states
- Figure 3's matrix-cell annotations need the same treatment
- keep colours distinguishable in greyscale

Regenerate through the asset pipeline, not by hand.

---

## PART 2 — BROKEN SENTENCES (must fix)

These do not parse as written.

**2.1 Abstract, opening**

FIND: `Benchmark contamination: the presence of evaluation data in a large language model's (LLM) training corpus, inflates reported scores on static test suites.`

REPLACE: `Benchmark contamination, the presence of evaluation data in a large language model's (LLM) training corpus, inflates reported scores on static test suites.`

**2.2 Abstract, Holm sentence**

FIND: `Six hypotheses were pre-specified and evaluated under Holm-Bonferroni correction and p-values are applied; the causal contamination-resistance evidence remains.`

REPLACE: `Six hypotheses were pre-specified. Where p-values apply, they are corrected with the Holm-Bonferroni procedure. The causal evidence for contamination resistance holds.`

**2.3 Section 3.1, stray hyphen and unclear count**

FIND: `every template sampled once per seed to produce fifteen-templates per tier across four tiers with five instances per template, for 300 problems per instantiation`

REPLACE: `fifteen templates per tier, four tiers, five instances per template, giving 300 problems per instantiation`

**2.4 Section 4.2, opening**

FIND: `Not within the six pre-registered hypotheses: it tests If a single instantiation is itself leaked into training. Does inflation follow the leaked artefact rather than the benchmark as a whole?`

REPLACE: `This probe sits outside the six pre-registered hypotheses. It asks what happens when a single instantiation is leaked into training. Does the inflation attach to the leaked artefact, or to the benchmark as a whole?`

**2.5 Section 4.4, missing noun**

FIND: `The co-primary unconditional reading restricts the comparison to a zero-filled, in which a suite that fails the baseline gate scores zero rather than being excluded`

REPLACE: `The co-primary reading is unconditional. A suite that fails the baseline gate scores zero instead of being excluded from the average`

**2.6 Section 4.7, sentence fragment**

FIND: `ULT↔BigCodeBench (clause 2), vs. Dynamic↔BigCodeBench. whether the dynamic-proxy correlation is weaker than the static-proxy correlation, is answerable directly from data already computed for clause 1:`

REPLACE: `ULT↔BigCodeBench (clause 2). Clause 2 asks whether the dynamic-proxy correlation is weaker than the static-proxy correlation. It can be answered from the data already computed for clause 1.`

**2.7 Section 4.7, dangling participle**

FIND: `opposite to the pre-registered prediction, stating that the dynamic benchmark tracks external code-generation capability better than the static benchmark.`

REPLACE: `This is the opposite of the pre-registered prediction. DyMuT tracks external code-generation capability better than the static benchmark does.`

**2.8 Section 4.6, agreement error**

FIND: `Only 3/6 of the six headline-scope pairs was individually significant at raw p < 0.05, and 1/6 survived Holm correction.`

REPLACE: `Three of the six headline-scope pairs were individually significant at raw p < 0.05, and one survived Holm correction.`

**2.9 Section 4.6, unclear referent**

FIND: `Reaching the pre-registered fifth instantiation for the two remaining was costed directly against this diagnosis and declined`

REPLACE: `Reaching the pre-registered fifth instantiation for the two remaining models was costed against this diagnosis and declined`

**2.10 Section 5, no main verb before the colon**

FIND: `Executing untrusted, template-generated or scraped ground-truth code in a subprocess: an early ground-truth quality check that executed thousands of real-world ULT functions with the working directory left at the project root produced several stray files from functions performing ordinary relative-path I/O as a side effect, a lesson since fixed by always executing untrusted code from an isolated temporary directory, showing the gap between "runs in a subprocess" and "runs safely".`

REPLACE: `Running untrusted code in a subprocess is not the same as running it safely. An early ground-truth quality check executed thousands of real-world ULT functions with the working directory left at the project root. Several of those functions wrote files as a side effect of ordinary relative-path I/O. The check now runs from an isolated temporary directory.`

---

## PART 3 — ABSTRACT (simplify)

**3.1**

FIND: `This work evaluates whether a dynamic, template-based benchmark for LLM unit-test generation resists this inflation more effectively than a state-of-the-art static alternative.`

REPLACE: `This work presents DyMuT (Dynamic Mutation-based Testing), a benchmark for LLM unit-test generation, and tests whether it resists this inflation better than a state-of-the-art static alternative.`

**3.2**

FIND: `Nine models were evaluated against the dynamic benchmark and a decontaminated static baseline (ULT), and a small open-source model was fine-tuned on that baseline's ground truth to probe contamination sensitivity.`

REPLACE: `Nine models were evaluated on DyMuT and on a decontaminated static baseline (ULT). A small open-source model was then fine-tuned on ULT's ground truth to test how each benchmark responds to contamination.`

**3.3**

FIND: `The fine-tuned model gained 99.1 percentage points on the memorised static split against an 8.7-point generic improvement control, while its dynamic-benchmark score moved by exactly zero, the clearest evidence that it rejects contamination the static one absorbs.`

REPLACE: `The fine-tuned model gained 99.1 percentage points on the memorised static split, against 8.7 points on a control that measures general improvement. Its DyMuT score did not move at all. DyMuT rejects the contamination that the static benchmark absorbs.`

**3.4**

FIND: `One pre-specified prediction was contradicted: the dynamic benchmark tracked external code-generation ability more closely than the static benchmark.`

REPLACE: `One pre-specified prediction was contradicted. DyMuT tracked external code-generation ability more closely than the static benchmark did.`

**3.5**

FIND: `The findings support dynamic, template-based generation as a practical, contamination-resistant evaluation strategy for LLM test-generation research.`

REPLACE: `The findings support dynamic, template-based generation as a workable way to evaluate LLM test generation without contamination inflating the result.`

---

## PART 4 — INTRODUCTION (simplify)

**4.1**

FIND: `Once a benchmark is published, its contents leak into future training corpora: directly, when the published set is scraped from the web, and indirectly, when problems sent to commercial model APIs during evaluation are retained and reused as training signal.`

REPLACE: `Once a benchmark is published, its contents leak into future training corpora. This happens directly, when the published set is scraped from the web, and indirectly, when problems sent to commercial model APIs during evaluation are kept and reused for training.`

**4.2**

FIND: `its reported score reflects recall rather than the capability the benchmark was designed to measure`

REPLACE: `its reported score measures recall, not the capability the benchmark was built to test`

**4.3**

FIND: `Static benchmarks are vulnerable to this failure mode: once published, their exact content is a fixed target that later training runs absorb.`

REPLACE: `Static benchmarks are vulnerable to this. Once published, their exact content is a fixed target that later training runs absorb.`

**4.4**

FIND: `An LLM asked to generate unit tests for a function can appear highly effective at a task if it has memorised the function's own reference tests during training, even though it cannot do the same for a function it has not seen.`

REPLACE: `An LLM asked to write unit tests for a function can look highly capable if it memorised that function's reference tests during training. The same model may fail on a function it has not seen.`

**4.5**

FIND: `The most relevant static baseline available for this problem is UnLeakedTestBench (ULT) [3] which addresses this by construction: its authors decontaminate a set of real-world functions and pair each with a deliberately leaked twin (PLT) to make the contamination signal observable.`

REPLACE: `UnLeakedTestBench (ULT) [3] is the closest static baseline. Its authors decontaminate a set of real-world functions and pair each with a deliberately leaked twin, PLT, so that any contamination signal becomes visible.`

**4.6**

FIND: `This makes ULT/PLT the best static comparator for this work, but a decontaminated benchmark, once published, is subject to the same absorption risk that motivated its construction: nothing prevents its content from entering a future model's training data.`

REPLACE: `That design makes ULT and PLT the best static comparator here. But a decontaminated benchmark, once published, faces the same risk it was built to avoid. Nothing stops its content entering a future model's training data.`

**4.7**

FIND: `A benchmark whose problem instances are freshly generated at evaluation time, from a private template grammar rather than a fixed published set, is resistant to this failure mode in a way no static benchmark, even carefully decontaminated can remain over time.`

REPLACE: `A benchmark that generates fresh problem instances at evaluation time, from a private template grammar, avoids this. No static benchmark can, however carefully it is decontaminated.`

**4.8 — the "evaluates" sentence the supervisor flagged**

FIND: `This dissertation evaluates that claim. A dynamic, template-based benchmark for LLM unit-test generation is constructed from sixty parameterised templates spanning four cyclomatic-complexity (CC) tiers, each template capable of producing distinct, seeded problem instances scored against a reference oracle by a mutation-testing suite rather than a fixed set of expected outputs. The aim is to establish whether this generative design resists the contamination-induced score inflation that affects static benchmarks, without sacrificing the ability to discriminate genuine test-generation capability.`

REPLACE: `This dissertation builds such a benchmark and tests that claim. DyMuT is built from sixty parameterised templates spanning four cyclomatic-complexity (CC) tiers. Each template produces distinct, seeded problem instances, scored against a reference oracle by a mutation-testing suite instead of a fixed set of expected outputs. The aim is to establish whether this design resists the score inflation that contamination causes in static benchmarks, while still separating strong test generation from weak.`

**4.9 — the three objectives**

FIND: `The first is observational: compare mutation-testing performance across nine models on the dynamic benchmark against their performance on ULT, and against ULT's leaked twin PLT, to establish whether either static reading shows the contamination-consistent pattern (higher scores on the leaked variant) that the dynamic benchmark should not.`

REPLACE: `The first is observational. Compare mutation-testing performance across nine models on DyMuT, on ULT, and on ULT's leaked twin PLT, and check whether either static benchmark shows the pattern contamination would produce: higher scores on the leaked variant.`

FIND: `The second is causal: fine-tune a small open-source model directly on ULT's ground truth and measure whether its gain transfers to the dynamic benchmark or remains confined to the static one, which isolates contamination-driven inflation from any capability improvement the fine-tuning step produces.`

REPLACE: `The second is causal. Fine-tune a small open-source model on ULT's ground truth, then measure whether the gain carries over to DyMuT or stays on the static benchmark. This distinguishes inflation caused by contamination from any real capability the fine-tuning adds.`

FIND: `The third is a construct-validity check: establish whether the dynamic benchmark's ranking of models agrees with an externally validated proxy of code-generation capability, since a benchmark that resists contamination but does not measure anything recognisable would not be a useful substitute for the static benchmarks.`

REPLACE: `The third checks construct validity. Does DyMuT's ranking of models agree with an external, independently maintained measure of code-generation ability? A benchmark that resists contamination but measures nothing recognisable would not be a useful replacement.`

---

## PART 5 — SECTION 3 (simplify, plus the supervisor's "isolate" point)

**5.1 — "isolate" is too strong**

FIND: `To isolate contamination-driven score inflation causally rather than observationally, the smallest open-source model`

REPLACE: `To identify contamination-driven score inflation causally, not just observationally, the smallest open-source model`

**5.2 — "a fresh dynamic-benchmark instantiation" weakens the contribution**

FIND: `The fine-tuned checkpoint is then re-evaluated on ULT, on PLT, and on a fresh dynamic-benchmark instantiation, using a 2×3 difference-in-differences design`

REPLACE: `The fine-tuned checkpoint is then re-evaluated on ULT, on PLT, and on a fresh DyMuT instantiation, using a 2×3 difference-in-differences design`

**5.3**

FIND: `This is the property that distinguishes the benchmark from a static release: its problem space is defined by the template grammar and parameter domains, not by a fixed set of instances, so no single generated instantiation can be memorised by a future model.`

REPLACE: `This is what separates DyMuT from a static release. Its problem space is defined by the template grammar and the parameter domains, not by a fixed set of instances. No single generated instantiation can be memorised by a future model.`

**5.4**

FIND: `Correctness is oracle-by-construction: every generated instance carries its own reference implementation, generated alongside it from the same template, so scoring never depends on a separately curated expected-output set.`

REPLACE: `Correctness comes from construction. Every generated instance carries a reference implementation, produced alongside it from the same template, so scoring never depends on a separately curated set of expected outputs.`

**5.5**

FIND: `and is reported as a labelled co-primary rather than a replacement, since the two readings are different estimands that can disagree substantially for a model with a low baseline-pass rate.`

REPLACE: `and is reported as a labelled co-primary, not a replacement. The two readings measure different quantities and can disagree widely for a model with a low baseline-pass rate.`

---

## PART 6 — DISCUSSION (simplify; this is where the "sophisticated" impression is strongest)

**6.1**

FIND: `The pattern across H1–H6 is read as evidence from two distinct kinds of test: one causal, one observational.`

REPLACE: `The results come from two kinds of test, one causal and one observational.`

**6.2**

FIND: `H1's observational results, weaker and more equivocal by design, probe a different question, whether models trained by others, on unknown corpora, already carry this same effect for ULT's specific published content.`

REPLACE: `H1's observational results are weaker, and they ask a different question. Do models trained by others, on corpora nobody here can inspect, already carry this effect for ULT's published content?`

**6.3**

FIND: `The two results are not in tension: a causal probe with a single, controlled intervention can show a clean, large effect that an observational comparison across nine models of unknown training history cannot be expected to recover with the same clarity.`

REPLACE: `The two results do not conflict. A causal probe with one controlled intervention can show a large, clear effect. An observational comparison across nine models with unknown training histories cannot be expected to recover the same effect as clearly.`

**6.4**

FIND: `A further finding shows post-fine-tuning mutation score on the seen-ULT split, despite 100% verbatim reproduction of the training target, is 0.438, not 1.0.`

REPLACE: `One further finding is worth stating. After fine-tuning, the mutation score on the seen-ULT split is 0.438, not 1.0, even though the model reproduces its training target word for word.`

**6.5**

FIND: `This sets a ceiling on how much a purely memorisation-driven strategy can inflate a mutation-testing score, independent of whether the benchmark resists contamination at all.`

REPLACE: `Memorisation alone can only inflate a mutation-testing score so far, whether or not the benchmark resists contamination.`

**6.6**

FIND: `The answer is mixed: the conditional primary metric's point estimate lands inside the pre-registered validity band, though it does not reach significance at this sample size, while the coverage-adjusted co-primary exceeds it, decomposing to reveal that most of the latter agreement is really agreement about executability rather than about mutation-testing quality specifically.`

REPLACE: `The answer is mixed. The conditional primary metric lands inside the pre-registered validity band, though it does not reach significance at this sample size. The coverage-adjusted co-primary exceeds the band. Breaking that figure down shows most of its agreement is about executability, not about mutation-testing quality.`

**6.7**

FIND: `Neither reading alone settles the question; together they place the benchmark closer to its intended target, correlated with general code-generation capability.`

REPLACE: `Neither reading settles the question alone. Together they place DyMuT close to its intended target, correlated with general code-generation ability.`

**6.8**

FIND: `Mutation score throughout is conditional on baseline correctness by design (Section 3.3), which Section 4 shows materially affects cross-benchmark rank agreement (H6) and should be read as a property of the specific metric definition rather than of the benchmark's validity.`

REPLACE: `Mutation score is conditional on baseline correctness throughout. Section 4 shows this affects cross-benchmark rank agreement in H6. It is a property of the metric definition, not of the benchmark itself.`

---

## PART 7 — WORD-LEVEL SUBSTITUTIONS

Apply throughout, keeping the meaning:

| Replace | With |
|---|---|
| equivocal | mixed, or unclear |
| absorption risk | risk of being absorbed |
| discriminate genuine capability | separate strong from weak |
| recognisable to an independent evaluation | that an independent evaluation recognises |
| materially affects | changes |
| corroborated by | supported by |
| pessimistic and directly comparable | conservative and comparable |
| by construction (where it appears more than twice) | vary the phrasing |
| by design (where it appears more than twice) | vary the phrasing |

Do not remove a word where it carries a real technical meaning. "By construction"
in "oracle-by-construction" and "untestable by construction" is a term of art and
should stay.

---

## PART 8 — CONSISTENCY CHECK

- Numerals: `across 8 of the nine canonical models` mixes styles. Use words for
  both, or figures for both, consistently across the paper.
- Check that every remaining use of "the dynamic benchmark" is intentional under
  the rule in 1.1.
- Confirm the abstract, introduction and conclusion agree on every verdict after
  these edits.

---

## AFTER APPLYING

Recompile and report: page count (hard cap 8), body and full word counts,
citation gate result, cross-reference check, and confirmation that no number,
CI, effect size, verdict or disclosure changed. Most of these edits shorten the
text; the larger figures and the new table column will add some. If the paper
goes to nine pages, stop and report with a ranked cut list.
