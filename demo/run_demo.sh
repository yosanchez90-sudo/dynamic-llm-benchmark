#!/usr/bin/env bash
# Live code demonstration, in three parts.
#
#   Part 1  Does the mechanism work?      steps 1-6
#   Part 2  What does it buy you?         step  7
#   Part 3  Can you trust the numbers?    step  8
#
# Run from the repository root, with the project venv active:
#   source .venv/bin/activate
#   ./demo/run_demo.sh
#
# Press ENTER between steps. Nothing here calls a model API; every test
# suite is a file on disk, written and verified in advance.

# No -e: step 8 runs a check that is SUPPOSED to fail, and -e would kill
# the script at exactly the moment the demo is making its point.
set -uo pipefail

T=L2-clamp-001      # 10 mutants, confirmed by execution
A=1101              # the instance a model "memorised"
B=4207              # a fresh instance drawn at evaluation time
C=3003              # a third, for the surface-variation point

# Set to 0 to skip the equivalent-mutant aside in step 5 if you are running long.
SHOW_EQUIVALENT=1

# --- Step 8 configuration ---------------------------------------------------
# Verified 2026-09-03: this anchor appears exactly once in the document, and
# swapping 9 -> 11 makes the gate report one MISMATCH and exit non-zero.
# n_models is used deliberately: the live corpus holds only ten distinct
# n_models values, so an invented one genuinely fails to match. Most p-values
# and correlations do NOT work here -- with 448 live p-values, almost any
# number you invent coincidentally matches something and the gate still passes.
CITED_DOC="analysis/RQ5_INTERPRETATION.md"
REAL_TEXT="n_models=9: exec_rate"
FAKE_TEXT="n_models=11: exec_rate"

step () { echo; echo "--- $1"; echo; read -r; }
part () { echo; echo "==============================================================="; \
          echo "  PART $1 - $2"; \
          echo "==============================================================="; read -r; }

clear || true   # don't let a missing/unset TERM abort the whole demo

###############################################################################
part 1 "Does the mechanism work?"
###############################################################################

step "1/8  The template. Sixty of these, fifteen per complexity tier."
cat "template_corpus/templates/L2/${T}.py"

step "2/8  Three seeds, one template. Surface changes, structure holds."
python demo/show_instance.py --template "$T" --seed "$A"
python demo/show_instance.py --template "$T" --seed "$B" --no-mutants
python demo/show_instance.py --template "$T" --seed "$C" --no-mutants

step "3/8  The same seed twice. Different seeds differ; one seed reproduces."
python demo/show_instance.py --template "$T" --seed "$A" --quiet > /tmp/dymut_a1.txt
python demo/show_instance.py --template "$T" --seed "$A" --quiet > /tmp/dymut_a2.txt
if diff -q /tmp/dymut_a1.txt /tmp/dymut_a2.txt > /dev/null; then
    echo "  diff: empty - byte-identical source, CC and mutant set."
else
    echo "  DIFF NON-EMPTY - investigate before presenting."
    diff /tmp/dymut_a1.txt /tmp/dymut_a2.txt | head -20
fi

step "4/8  A suite written for seed ${A}. Both gates pass; now the mutants."
python demo/score_suite.py --template "$T" --seed "$A" \
    --suite demo/suite_seed_${A}.py --label "written for seed ${A}"

step "5/8  One survivor is catchable. Here is the assertion that catches it."
diff -u demo/suite_seed_${A}.py demo/suite_seed_${A}_plus.py | tail -n +4
echo
read -r
python demo/score_suite.py --template "$T" --seed "$A" \
    --suite demo/suite_seed_${A}_plus.py --label "one assertion added"

if [ "$SHOW_EQUIVALENT" = "1" ]; then
    echo
    echo "--- ...and one that nothing can catch. M1, still alive:"
    echo
    read -r
    python demo/show_instance.py --template "$T" --seed "$A" --show-mutant 1
    echo "  At elem=66 the original takes the else-branch and returns elem (66)."
    echo "  The mutant takes the if-branch and returns the ceiling (66). Same value."
    echo "  No return-value assertion can separate them: an equivalent mutant."
    echo "  The 120-mutant hand inspection reached this template and judged a ROR"
    echo "  mutant on it equivalent for the same reason (row 53, seed 102)."
    echo "  That is why the raw score is a conservative floor, applied uniformly."
fi

step "6/8  The SAME suite against seed ${B} - raw, then with the import repaired."
python demo/score_suite.py --template "$T" --seed "$B" \
    --suite demo/suite_seed_${A}.py --label "memorised, unmodified"
python demo/score_suite.py --template "$T" --seed "$B" \
    --suite demo/suite_seed_${A}_import_fixed.py --label "memorised, import repaired"

###############################################################################
part 2 "What does it buy you?"
###############################################################################

step "7/8  The whole evaluation set, regenerated, one number apart."
python demo/compare_instantiations.py

###############################################################################
part 3 "Can you trust the numbers?"
###############################################################################

step "8/8  Every number in the write-up is checked against live pipeline output."

# Restore the document no matter how this step ends, including Ctrl-C.
restore_doc () {
    if ! git diff --quiet -- "$CITED_DOC" 2>/dev/null; then
        git checkout -- "$CITED_DOC" && echo "  (restored $CITED_DOC)"
    fi
}
trap restore_doc EXIT INT TERM

if [ -n "$(git status --porcelain "$CITED_DOC" 2>/dev/null)" ]; then
    echo "  SKIPPED: $CITED_DOC has uncommitted changes; refusing to edit it."
elif [ "$(grep -c -- "$REAL_TEXT" "$CITED_DOC")" != "1" ]; then
    echo "  SKIPPED: expected exactly one occurrence of '$REAL_TEXT'"
    echo "  in $CITED_DOC. The document has moved on; re-pick the anchor."
else
    echo "  \$ python scripts/check_doc_citations.py"
    python scripts/check_doc_citations.py | tail -3

    echo
    echo "  Now change one number by hand:  n_models=9  ->  n_models=11"
    echo
    read -r
    sed -i "s/${REAL_TEXT}/${FAKE_TEXT}/" "$CITED_DOC"
    git --no-pager diff --unified=0 -- "$CITED_DOC" | tail -4

    echo
    read -r
    echo "  \$ python scripts/check_doc_citations.py"
    python scripts/check_doc_citations.py | grep -E "MISMATCH|^TOTAL:|^GATE:" | cut -c1-100

    echo
    echo "  The asset build stops here. The number cannot reach the write-up."
    restore_doc
fi
trap - EXIT INT TERM
echo
