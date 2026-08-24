# Speaker Notes

Two scripts for the same sixteen-slide deck (`SLIDES.pptx`). The video script uses slides 1-13 only, a ten-minute hard cap, target 9:45. The live demo script uses all sixteen slides, fifteen minutes of presenting plus five minutes of questions.

---

## VIDEO SCRIPT (10:00 hard cap, target 9:45)

### 0:00-0:30 : Title (Slide 1)

Say your name and student number on camera, with your photo visible, then move straight to slide 1.

"My name is Yohan Sneider Sanchez Vega, student number 40492566. This is a dynamic, template-based benchmark for LLM unit-test generation, built to resist contamination-induced score inflation."

### 0:30-1:30 : The problem (Slide 2)

"A benchmark's score only means something if the model has not seen its problems. Once a benchmark is published, its content leaks into future training data, scraped from the web, or logged from API use during evaluation. The next time that benchmark is used, a model can score well by recall, not by the capability the benchmark was meant to measure. This project asks whether a benchmark can be built that a model cannot have seen in advance, because its content did not exist until the moment it was evaluated."

### 1:30-2:30 : What was built (Slide 4)

"The answer is a template-based benchmark. Sixty hand-written templates, across four complexity tiers, each generate fresh problem instances at evaluation time, with a reference oracle and precomputed mutants. A model's response passes through two gates: does the generated suite even run, and does it pass against the real function. Only then is it scored by mutation testing, how many of the function's deliberate variants the suite catches. That record feeds three experiments: the dynamic benchmark against a static comparator, that comparator against its leaked twin, and a causal fine-tuning probe."

### 2:30-4:30 : Screen capture: the pipeline on one real problem

**What to show on screen, with the commands to run:**

```bash
cat template_corpus/templates/L3/L3-clamp-seq-001.py
```

"This is one template. It builds a function that clamps values into a range, under a generic name chosen on purpose, so a model cannot rely on a familiar name like `clamp` to recognise the pattern."

```bash
grep -o '"template_id": "L3-clamp-seq-001".*"mutation_score": [0-9.]*' \
  data/results/dynamic/claude-sonnet-4-6__dynamic__zero_shot__inst1__20260714T141018.jsonl
```

"This is one real, scored response to that instance, from Claude Sonnet. `exec_rate` and the coverage fields are both 1.0, the suite ran cleanly and passed against the real function, so it reached mutation scoring: seventeen of twenty-one mutants killed, a mutation score of 0.81."

```bash
uv run python scripts/check_doc_citations.py
```

"Every number in this project's write-up is checked against output like this automatically. This is the citation gate passing on the current state of the repository."

### 4:30-5:30 : The contamination experiment (Slide 8)

"To test contamination causally, not just observe it, the smallest open-source model in the panel is fine-tuned on the static benchmark's ground-truth tests, one hundred and twelve verified training pairs. The fine-tuned checkpoint is then re-scored on the benchmark it trained on, on that benchmark's leaked twin, and on a fresh dynamic-benchmark instantiation it never saw during training."

### 5:30-8:00 : Results (Slides 9, 10, 11)

**Slide 9:** "The fine-tuned model gains ninety-nine point one percentage points on the split it trained on. A control condition on the dynamic benchmark's easier tiers shows the model does get a little better at test-writing overall, eight point seven points. But on the dynamic benchmark's hardest tier, the tier that matches the static benchmark's complexity floor, the gain is exactly zero. The training the model received does not reach the dynamic benchmark."

**Slide 10:** "The onset curve shows why. Epoch one's jump is shared across every arm, that is generic capability improving. The climb that follows, from epoch five onward, appears only on the split the model trained on. That is memorisation, and it is visible as a second, later, separate timescale in the same run."

**Slide 11:** "Six pre-registered hypotheses, nine tested outcomes. The causal result is supported, the strongest finding in the project. Two results are not supported, one is dropped as untestable by construction, and one stability result falls short of its pre-registered bar. All nine are reported here, not just the ones that came out well."

### 8:00-9:00 : Limitations and future work (Slides 12, 13)

"The causal result rests on one model and one fine-tuning method. Rank-level stability across benchmark regenerations falls short of its target, even though each model's score is highly reproducible. The benchmark's problems are template-generated, not drawn from real repositories, and the hand-inspected mutant validation was not complete at the time of writing. Future work: finish that validation, test the causal result at larger scale, add semantic-preserving mutation operators, and, pending a decision on release scope, publish the template corpus."

### 9:00-9:45 : Close

"This project shows that a dynamic, template-based, mutation-scored benchmark can resist a real, demonstrated contamination mechanism, while still tracking an external measure of code-generation capability it was never tuned against. Thank you."

---

## LIVE DEMO SCRIPT (20 minutes: 15 presenting, 5 questions)

Same spine as the video script, with the screen segment expanded and the three DEMO ONLY slides included after slide 13.

**0:00-0:30** Slide 1, as above.

**0:30-1:45** Slide 2, as above, with fuller framing: name both contamination routes (scraping and API logging) and give the Balloccu et al. figure, 42% of 255 papers reviewed.

**1:45-3:00** Slide 4, as above, tracing the whole diagram including the ULT/PLT input branch and the two gate-failure exits.

**3:00-3:30** Slide 5. Show the template-and-instance slide instead of only describing it: point out the generic function name and the docstring, and connect it to slide 2's contamination framing.

**3:30-4:30** Slide 6. Walk the two gates on screen, then show a second real example, a response that fails the baseline gate, to make the exclusion concrete: any row in a results file with `"baseline_passed": false` and `"mutation_score": null`.

**4:30-7:30** Screen capture, expanded. Run the same three commands as the video script, then add:

```bash
uv run pytest tests/ --collect-only -q | tail -3
```

"A hundred and thirty-six tests, covering the scoring harness, the deduplication logic, and the tier-aware resume matcher, among others."

```bash
tail -30 analysis/METRICS_AND_FINDINGS_EXPLAINED.md
```

Scroll to the error ledger and pick one row live, the decoding-setting bug is the strongest story: what broke, what it cost, what changed.

**7:30-8:30** Slide 8, as above.

**8:30-12:00** Slides 9, 10, 11, as above, at a slightly slower pace, taking questions if any arise naturally.

**12:00-13:00** Slides 12 and 13, as above.

**13:00-15:00** DEMO ONLY, slides 14 to 16. Open the repository structure on screen (slide 14), show the citation gate and the test suite running live if not shown yet (slide 15), and close with the honest retrospective (slide 16): what would be built first with the same time again.

**15:00-20:00** Questions.

### Ten likely assessor questions, with short answers

**1. Why is H1's first test not supported?**
The rank-based effect size favours the dynamic benchmark, opposite to the prediction, though not significantly (p = 0.7422, n = 8). A naive comparison of raw column means looks like it favours the static benchmark instead, but that mean is dominated by two outlier models; the rank statistic the pre-registered test uses is not.

**2. Why did H5 miss its stability threshold?**
Mean pairwise rank agreement across benchmark regenerations reaches 0.583 against a bar of 0.7. A diagnostic check found several models clustered so close together in score that no ranking instrument could reliably order them from this data alone. Each model's score is still highly reproducible; it is close rankings between similarly scoring models that the benchmark cannot resolve.

**3. Why was H4 dropped?**
The static benchmark contains no problems below the complexity floor the hypothesis needed to compare against, a filter the source benchmark's authors applied. A tier-by-benchmark interaction cannot be estimated when one side has no variation in the tier variable. The supervisor approved treating it as untestable by construction. Forcing a model that could not answer the question was not the alternative taken.

**4. What does the conditional-versus-unconditional metric issue mean?**
The project's primary metric averages mutation score only over problems whose suite passes the baseline gate. A second reading scores every attempted problem, including a zero for a suite that never passed. A model with a low pass rate can look strong under the first reading and weak under the second, since the first reading is only ever computed over the problems that model succeeded at. Both are reported so neither reading is mistaken for the whole picture.

**5. How do you know the reported numbers are correct?**
Eleven real measurement bugs were found and fixed over the project, each logged with what it cost and what changed. Every hand-typed number in the write-up is checked automatically against the live pipeline output by a citation gate, which fails the build if a number no longer matches anything the pipeline currently produces.

**6. Why templates instead of real-world code?**
Real, scraped code is a fixed artefact once assembled into a corpus, and can leak the same way any benchmark can. A template grammar lets a fresh problem instance be generated at evaluation time, from content that need never be published. The cost is disclosed plainly: template-generated code may not carry the full structural variety of production code.

**7. Why only one model in the causal fine-tuning experiment?**
Compute budget, and the smallest model was chosen on purpose so a memorisation signal, if present, would not be masked by a larger model's capability. Whether the same clean separation between memorisation and transfer holds at larger scale is untested here, and is named plainly as a limitation.

**8. Why does the dynamic benchmark track the external proxy better than the static benchmark does, when the prediction was the opposite?**
That is H6's second clause, and the result contradicts the prediction: the dynamic benchmark's agreement with BigCodeBench is as strong as, or stronger than, the static benchmark's agreement, on every metric and scope tested. It is reported as found, and read as a favourable result, not a failed prediction, since it means contamination resistance was not bought at the cost of measuring nothing recognisable.

**9. What would you do differently with more time?**
Build the citation gate and full decoding-configuration logging in week one, not after the incidents that made them necessary. Budget the fifth benchmark instantiation from the start, since stability turned out to be the result with the least margin to spare. Start the mutant hand-inspection earlier so it did not compete with write-up time.

**10. What is the equivalent-mutant validation, and why is it not finished?**
Some mutants generated by the seven operators are semantically equivalent to the original function and cannot be killed by any correct suite, which would depress a mutation score without reflecting a real quality gap. A hand-inspected sample of a hundred and twenty mutants is meant to produce a corrected companion score alongside the raw headline figure. It is manual work, was not complete at the time of writing, and the raw score is reported alone. No placeholder stands in for the missing companion figure.
