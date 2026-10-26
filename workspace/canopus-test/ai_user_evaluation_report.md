# Canopus local user evaluation — 27 October 2026

## Outcome

**Local evaluation passed. External-detector evaluation is partial and inconclusive.** All three synthetic AI-style samples were accepted by `/v1/transform`; source offsets, idempotence, API parity, and semantic safeguards passed. ZeroGPT completed 3 of 6 planned scans; GPTZero and Scribbr were blocked before usable scans.

## Test inputs

- File: `ai_user_samples.json`
- Provenance: synthetic AI-style text authored for this test; not attributed to a particular external model.
- Levels: short general (65 words), medium academic (152 words), long technical (367 words).

## Local user-path results

| Sample | Words | V4 changes | Accepted | API parity | Offsets | Idempotent | Meaning safeguards | Legacy `/v1/humanize` |
|---|---:|---:|---|---|---|---|---|---|
| short_general_65w | 65 | 0 | True | True | True | True | True | 200 / 5 changes |
| medium_academic_152w | 152 | 4 | True | True | True | True | True | 200 / 9 changes |
| long_technical_367w | 367 | 7 | True | True | True | True | True | 200 / 11 changes |

### Local observations

- **short_general_65w**: output changed = `False`; Flesch Reading Ease `22.44 -> 22.44`; V4 issues = `0`.
  V4 correctly left this short passage unchanged under conservative rules.
- **medium_academic_152w**: output changed = `True`; Flesch Reading Ease `19.61 -> 13.40`; V4 issues = `0`.
  Changes: `Due to the fact that` → `Because`; `Previous studies have shown` → `Prior investigations have shown`; `In order to` → `To`; `it is worth noting that` → `importantly,`
- **long_technical_367w**: output changed = `True`; Flesch Reading Ease `26.90 -> 23.19`; V4 issues = `0`.
  Changes: `Due to the fact that` → `Because`; `In order to` → `To`; `Previous studies have shown` → `Prior investigations have shown`; `In order to` → `To`; `It is worth noting that` → `Importantly,`; `further research is needed` → `subsequent investigation is warranted`; `In conclusion` → `In summary`

## External detector results

### ZeroGPT

- Source: `https://zerogpt.net/ai-content-detector`
- Date: 27 October 2026 (site displayed 26 October 2026 evening in UTC/local page time).
- Account/payment: none.
- Model/version: not shown in the returned report.
- Site constraints observed: minimum 250 characters; free public scan; result page reported 15,000-character limit.

| Sample | Variant | Status | AI score | Human-like |
|---|---|---|---:|---:|
| short_general_65w | original | completed | 100% | 0% |
| short_general_65w | humanized | completed | 100% | 0% |
| medium_academic_152w | original | completed | 100% | 0% |
| medium_academic_152w | humanized | blocked_or_failed | — | — |
| long_technical_367w | original | blocked_or_failed | — | — |
| long_technical_367w | humanized | blocked_or_failed | — | — |

Completed scans:
- `short_general_65w` original: **100% AI score**.
- `short_general_65w` humanized: **100% AI score**; the V4 output was unchanged.
- `medium_academic_152w` original: **100% AI score**.

The remaining medium humanized and both long scans timed out at the detector form and did not produce scores. They are recorded as blocked, not as zero or missing scores.

### GPTZero

- Official page attempted: `https://gptzero.me/`.
- Result: blocked before scan; the headless browser context closed during page navigation.
- No account or sign-in was attempted.
- No score is claimed.

### Scribbr

- Official page attempted: `https://www.scribbr.com/ai-detector/`.
- Static page was reachable, but the interactive page closed the headless browser context before a scan could be performed.
- No account or sign-in was attempted.
- No score is claimed.

## Interpretation

- The local engine behaved correctly on all three levels, but these are safety and usability results, not proof of authorship or detector improvement.
- The available ZeroGPT results show no reduction on the short unchanged sample and do not provide a complete before/after matrix.
- Detector scores are not comparable across services or dates without model/version information.

## Files

- `ai_user_samples.json`
- `ai_user_evaluation_results.json`
- `zerogpt_results.json`
- `ai_user_evaluation_report.md`

## What was not done

No account was created, no payment was made, no detector quota was bypassed, and no score was invented.
