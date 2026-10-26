# Canopus autonomous run — 27 October 2026

## Outcome
**Failed — no writing-engine change proposed.** The corpus and measurement gates passed for one field, but the mandatory fixed evaluation inputs and 20+ text ablation set are absent, and the public clean clone is broken before test collection.

## Corpus: field, n papers, date range, file

- **Field:** `cs.LG`
- **Count:** 500 complete abstracts
- **Date range:** 2015-01-01 through 2022-11-30
- **File:** `workspace/canopus-test/corpus_csLG_2026-10-27.json`
- **Source:** arXiv API, abstracts only
- **Fetch utility:** `workspace/canopus-test/extract_pre2022.py` (reconstructed because the named original was absent)
- **Gate:** passed — one field, ≥500 records, complete records, all within the date filter

The requested `samples_original.json`, `human-pattern-library.json`, `pre2022-corpus.json`, `measured_patterns_2026-10-27.md`, and `results_v4_combined.md` were not present in the repository or local home directory.

## Measured targets (new vs previous, with % change)

Full reproducible measurements are in `workspace/canopus-test/measured_csLG_2026-10-27.md` and `measured_csLG_2026-10-27.json`, computed by `measure_corpus.py` from the named corpus file.

- Mean sentence length: 23.2383 vs 21.7, **+7.1%**
- Sentence SD: 9.4414 vs 7.8, **+21.0%** — larger corpus replaces target
- CV: 0.4063 vs 0.36, **+12.9%**
- Sentences ≤10 words: 4.7540% vs 5%, **-4.9%**
- Sentences ≥30 words: 21.8353% vs 18%, **+21.3%** — larger corpus replaces target
- Papers with numbers: 44.4% vs 61.5% from the supplied 13-paper summary, **-27.7%** — larger corpus replaces target
- Papers naming a dataset/method: 90.8% vs 53.8%, **+68.7%** — larger corpus replaces target

## Patterns tested (kept / rejected, with ablation scores)

**No candidate pattern was ablated.** The runbook requires at least 20 texts: the three fixed standard samples plus 17 longer same-field texts. Those files are absent. No detector scores, readability ratings, or meaning-preservation results were fabricated.

Candidate families identified from the measured corpus are recorded as unvalidated candidates in `measured_csLG_2026-10-27.md`: bounded rhythm windows, restructuring, transition deletion/sparsity, specificity flagging, qualification/contrast preservation, and review-only closing suggestions.

The existing `In conclusion -> In summary` transformation remains rejected based on the supplied historical evidence; it was not changed or reintroduced.

## Engine change proposed (files, stages, or “none”)

**None.** The mandatory ablation gate was not met. No production engine file, ruleset, test, or existing fixture was changed.

A local reliability-only patch was tested in the scratch clone: importing `Any` and `Optional` in `engine/planner.py`. This is not proposed as a writing-quality improvement, although it is required for the public branch to import successfully.

## Evaluation: before/after table (samples x detectors x lengths)

| Evaluation set | ZeroGPT | GPTZero | Scribbr | Status |
|---|---|---|---|---|
| Three fixed standard samples | Not run — files absent | Not run — files absent | Not run | Blocked |
| Five or more 300–500+ word texts | Not run — files absent | Not run — files absent | Not run | Blocked |
| Three pre-2022 human controls | Not run — files absent | Not run — files absent | Not run | Blocked |

No detector account was created, no sign-in was attempted, and no detector score is claimed.

## Readability & meaning ratings (with quoted evidence)

Not rated. The required before/after evaluation texts are unavailable, and no output was accepted as a candidate change. The corpus measurement is descriptive and does not establish human authorship or detector performance.

## Verification and clean-clone gate

1. Fresh clone from `sirynme/Canopus-humanizer-main` at `ccfe349965610af78ec44e3d4d166d5a6140ae62` — completed.
2. As-pushed test run before patch — **failed** during collection with 21 errors. Root error:
   `NameError: name 'Optional' is not defined` at `backend/src/canopus_humanizer/engine/planner.py:24`; the same file also referenced `Any` without importing it.
3. Local scratch patch adding `Any, Optional` — applied only in `/tmp/opencode/canopus-auto-20261027`.
4. Patched scratch full suite — **115 passed, 1 warning**.
5. Patched scratch API startup — passed.
6. Patched scratch `/v1/transform` smoke test — passed; protected `98.6%` and `[1]`, returned accepted output with one change.

The current workspace contains unrelated uncommitted user changes and its available virtual environment lacks the test/API dependencies, so it was not used to replace the clean-clone evidence.

## Gates checklist

- [x] Corpus ≥500 papers, 100% pre-Dec-2022, one field, source file named
- [x] Metrics recomputed from the corpus file, not hand-typed
- [ ] Every new pattern has ablation evidence on 20+ texts — blocked: inputs absent
- [x] Rejected patterns recorded, including “In summary”
- [ ] Tests pass from an unmodified clean clone — failed on public `ccfe349`
- [x] Patched scratch tests pass, API starts, and one transform succeeds
- [x] No existing test deleted or weakened
- [ ] Meaning checks pass on 100% of candidate outputs — no candidate outputs
- [ ] Detector scores reported with detector, date, model, warnings — scans blocked by missing fixed inputs
- [x] No account created, no payment, no push, no send
- [x] Run report delivered despite failure

## Caveats: detector model changes, warnings, drift, blocks

- No detector was contacted; therefore no detector model/version or score is reported.
- The supplied previous detector figures were treated as historical context only, not re-measured results.
- The previous 13-paper corpus and pattern library were unavailable.
- The clause-position result is a transparent marker-rule screen over 100 sentences, not a full syntactic parse.
- The public branch has a reproducible import defect before collection; the local fix was not pushed.
- One Starlette/httpx deprecation warning appeared in the patched scratch suite.

## What I did NOT do

I did not push, merge, deploy, email, post, create an account, sign in, pay, or contact a detector. I did not modify the current repository’s existing tracked files.

## Decision needed from Sohail

Provide or approve the missing fixed evaluation bundle and the original 13-paper measurement/library files. Separately approve `workspace/canopus-test/planner_import_fix.patch`, applied with `git apply workspace/canopus-test/planner_import_fix.patch`, if the reliability fix should be proposed upstream. No writing-pattern diff is ready for approval.
