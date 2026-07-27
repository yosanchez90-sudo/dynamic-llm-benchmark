# Comparison C — canonical 2x3 DiD results

**Note:** the "Headline interpretation" section below is hand-written on top
of this script's auto-generated tables — re-running `scripts/analyze_comparison_c.py`
regenerates the whole file and will overwrite it. If re-running after new
data lands, re-add or update that section rather than losing it.

Generated: 2026-07-27T09:30:37.471973+00:00
Script: scripts/analyze_comparison_c.py

Per analysis/COMPARISON_C_ANALYSIS_PLAN.md (pre-registered 2026-07-26,
amended same day for Dynamic-arm tier composition, both before this script's
first run). Primary metric: baseline_pass_rate. Mut@K reported alongside,
secondary (see PRE-data-sparsity note in the analysis plan).

## Sources

- PRE ULT/PLT/Dynamic: base Qwen-1.5B, already-landed (2026-07-13/06-09).
- POST ULT: Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep__ult__zero_shot__instcore_400__20260726T142439.jsonl (Stage 3a).
- POST PLT: Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep__plt__zero_shot__instcore_400__20260726T224725.jsonl (Stage 3b).
- POST Dynamic: 6 files, inst1-3 x {L1L2,L3L4} (Stage 3b).
- Seen/unseen split: data/raw/ult_plt/comparison_c_seen_manifest.json (frozen).

## Headline interpretation

**The predicted pattern holds at the top and bottom of the gradient, with one
real deviation in the middle.** seen-ULT gains +99.1pp (CI [97.3, 100.0]) —
essentially every seen problem now passes baseline, matching the 112/112
(100.0%) verbatim-match finding (`data/raw/ult_plt/PROVENANCE.md`). At the
other end, Dynamic-L4 shows exactly 0.0pp gain, but this is **floor-limited,
not evidence of "no transfer"**: both PRE and POST have baseline_pass_rate
identically 0.000 (a 1.5B model can't clear the CC>=8 baseline gate at all,
before or after fine-tuning) — the ANALYSIS_PLAN.md amendment's whole reason
for adding the L1-L3 arm.

**Deviation from the strict monotone-decay prediction:** PLT's raw gain
(+22.5pp) is *larger* than unseen-ULT's (+15.6pp), not smaller —
gain(seen-ULT) > **gain(PLT) > gain(unseen-ULT)** > gain(Dynamic), not the
predicted gain(seen-ULT) > gain(unseen-ULT) > gain(PLT) > gain(Dynamic).
Reporting this as found, not smoothing it into the predicted order.

**The Dynamic-L1-L3 robustness control is the more informative read here.**
It has real (non-floor) PRE headroom (6.7%) and shows its own +8.7pp gain
(CI [5.6, 12.0]) — fine-tuning on ULT improves test-writing on completely
unrelated, never-seen Dynamic problems too. That's a genuine "fine-tuning
helps in general" effect, and subtracting it as a control changes the
picture:
- seen-ULT: 99.1pp -> **90.4pp** DiD (CI [86.5, 94.1]) — still overwhelming.
- PLT: 22.5pp -> **13.8pp** DiD (CI [7.7, 20.1]) — clearly real, CI well clear of zero.
- unseen-ULT: 15.6pp -> **6.9pp** DiD (CI [1.3, 13.0]) — barely excludes
  zero. Most of unseen-ULT's raw gain is the generic-improvement effect,
  not something ULT-content-specific; what's left is a small, borderline
  signal, not the confidently-real transfer the raw number suggested.

**Mut@K tells a different, complementary story about test *quality*.** Even
though seen-ULT reaches 100% baseline-pass and 100% verbatim reproduction,
its POST Mut@K is only **0.438** (n=112, fully defined now that every suite
passes) — memorizing ULT's own ground-truth tests verbatim does not make
them *good* tests. This is a ceiling inherited from ULT's own
repair-verified ground truth (`data/raw/ult_plt/PROVENANCE.md`'s
ground-truth-quality section), not a fine-tuning artifact: perfect
reproduction of a mediocre test suite is still a mediocre test suite.
Every other arm's POST Mut@K is measured on a small, PRE-side-limited n
(see the analysis plan's "PRE data sparsity" section) and should not be
over-interpreted — e.g. unseen-ULT's mean *drops* from 0.338 (n=7, PRE) to
0.139 (n=52, POST) simply because the 45 newly-unlocked suites are, on
average, weaker than the tiny pre-existing PRE set, not because fine-tuning
made tests worse.

**Onset curve** (`analysis/figures/comparison_c_onset_curve.png`, epochs
{0,1,3,5,10,20,30}, fixed 50-seen/50-unseen/75-Dynamic-L1L2 subsample):
seen-ULT's baseline-pass rate rises 26% (epoch 1) -> 20% (epoch 3, noise) ->
34% (epoch 5) -> 72% (epoch 10) -> 100% (epoch 20, holds through 30), while
unseen-ULT and Dynamic-L1/L2 both stay flat and noisy in the 16-23% band
throughout, never trending upward. Verbatim-match onset is sharper and
later: 2% (epoch 1) -> 2% (epoch 3) -> 14% (epoch 5) -> 62% (epoch 10) ->
100% (epoch 20) — consistent with the 1,014-example training set's ~127
gradient-steps/epoch (vs ~2 for the 16-example supplementary run), i.e.
onset arriving far earlier in training than the supplementary study's
curves, as anticipated when the dense-early/sparse-late grid was chosen.

## Primary DiD (vs Dynamic-L4, CC-matched control)

 benchmark  pre_mean  post_mean    delta  control_delta      did  did_ci_lo  did_ci_hi  n_pre  n_post  n_pre_control  n_post_control    control
  seen_ult  0.008929   1.000000 0.991071            0.0 0.991071   0.973214   1.000000    112     112            225             225 dynamic_l4
unseen_ult  0.024306   0.180556 0.156250            0.0 0.156250   0.111111   0.204861    288     288            225             225 dynamic_l4
       plt  0.075000   0.300000 0.225000            0.0 0.225000   0.172500   0.275000    400     400            225             225 dynamic_l4

## Robustness DiD (vs Dynamic-L1-L3 pooled, headroom control)

 benchmark  pre_mean  post_mean    delta  control_delta      did  did_ci_lo  did_ci_hi  n_pre  n_post  n_pre_control  n_post_control      control
  seen_ult  0.008929   1.000000 0.991071       0.087407 0.903664   0.865106   0.940741    112     112            675             675 dynamic_l1l3
unseen_ult  0.024306   0.180556 0.156250       0.087407 0.068843   0.013330   0.129769    288     288            675             675 dynamic_l1l3
       plt  0.075000   0.300000 0.225000       0.087407 0.137593   0.077130   0.201211    400     400            675             675 dynamic_l1l3

## Four-level gradient (raw gain, no control subtraction)

   benchmark  n_pre  n_post  pre_mean  post_mean     gain  gain_ci_lo  gain_ci_hi
    seen_ult    112     112  0.008929   1.000000 0.991071    0.973214    1.000000
  unseen_ult    288     288  0.024306   0.180556 0.156250    0.107639    0.204861
         plt    400     400  0.075000   0.300000 0.225000    0.172500    0.277500
  dynamic_l4    225     225  0.000000   0.000000 0.000000    0.000000    0.000000
dynamic_l1l3    675     675  0.066667   0.154074 0.087407    0.056296    0.120000

## Mut@K (secondary; n_mut_defined shows how much of n_total this covers)

   benchmark  n_total  n_mut_defined  mut_at_k side
    seen_ult      112              1  0.885714  pre
  unseen_ult      288              7  0.338192  pre
         plt      400             30  0.594996  pre
  dynamic_l4      225              0       NaN  pre
dynamic_l1l3      675             45  0.816779  pre
    seen_ult      112            112  0.437699 post
  unseen_ult      288             52  0.138737 post
         plt      400            120  0.259132 post
  dynamic_l4      225              0       NaN post
dynamic_l1l3      675            104  0.693866 post
