# Measured pre-2022 corpus — cs.LG — 27 October 2026

## Source and reproducibility

- **Corpus source:** `corpus_csLG_2026-10-27.json`
- **Measurement source:** `measure_corpus.py`
- **Corpus:** 500 complete arXiv abstracts, category `cs.LG`
- **Date filter:** submitted/published date from 2015-01-01 through 2022-11-30
- **Words:** 84,076
- **Sentences:** 3,618
- **Method:** deterministic standard-library measurements rerunnable from the named JSON corpus

The repository-named `extract_pre2022.py` and the previous 13-paper corpus were absent, so `extract_pre2022.py` in this directory is a reconstructed local utility. It fetches abstracts only, uses the arXiv API, and waits 3.2 seconds between paginated requests.

## Sentence rhythm

| Metric | cs.LG corpus | Previous 13-paper target | Change |
|---|---:|---:|---:|
| Mean sentence length | 23.2383 words | 21.7 | +7.1% |
| Sample SD | 9.4414 | 7.8 | +21.0% |
| CV | 0.4063 | 0.36 | +12.9% |
| Minimum | 1 | not supplied | — |
| Maximum | 83 | not supplied | — |
| Sentences ≤10 words | 4.7540% | 5% | -4.9% |
| Sentences ≥30 words | 21.8353% | 18% | +21.3% |

The larger corpus replaces the previous SD and ≥30-word targets because each differs by more than 20%. All figures above are computed from `corpus_csLG_2026-10-27.json` and written to `measured_csLG_2026-10-27.json`.

The ten most common complete abstract sentence-length sequences were all singletons in this corpus. This indicates that complete abstract-level sequences are too sparse to serve as a reliable generator target; any rhythm rule should use bounded local windows and must be ablated before implementation.

## Transition rates

Rates are occurrences per 1,000 corpus words. Counts and rates are in `measured_csLG_2026-10-27.json`.

| Phrase | Count | Per 1,000 words |
|---|---:|---:|
| furthermore | 40 | 0.4758 |
| moreover | 41 | 0.4877 |
| additionally | 12 | 0.1427 |
| however | 141 | 1.6771 |
| therefore | 24 | 0.2855 |
| finally | 51 | 0.6066 |
| in conclusion | 1 | 0.0119 |
| in summary | 0 | 0.0000 |
| in this paper | 150 | 1.7841 |
| in this work | 74 | 0.8802 |
| we propose | 178 | 2.1171 |
| we show | 83 | 0.9872 |
| we find | 14 | 0.1665 |

The corpus supports transition sparsity and deletion/avoidance experiments. It does not support swapping one formal transition for another; the existing `In conclusion -> In summary` rule is retained as rejected by the supplied historical evidence and was not reintroduced.

## Specificity

| Metric | Result |
|---|---:|
| Number tokens | 749 |
| Numbers per 1,000 words | 8.9086 |
| Papers with at least one number | 44.4% (222/500) |
| Papers naming a dataset or method | 90.8% (454/500) |
| Abstracts starting with “In this paper/work” | 6.8% (34/500) |

Dataset/method detection uses the explicit indicator expression recorded in `measured_csLG_2026-10-27.json`; it is a reproducible lexical proxy, not a claim of full semantic identification. Compared with the supplied 13-paper values, number-bearing papers differ by -27.7% and dataset/method mentions by +68.7%; the 500-paper corpus replaces those targets for `cs.LG`.

## Clause positions

A deterministic marker taxonomy was applied to the first 100 segmented sentences. This is a transparent screening measurement, not a full dependency parse.

| Position among sentences with a detected subordinate marker | Count | Share |
|---|---:|---:|
| Start | 7 | 18.9189% |
| Middle | 22 | 59.4595% |
| End | 8 | 21.6216% |

The remaining sampled sentences had no marker under the recorded taxonomy. The marker list and method are stored in `measured_csLG_2026-10-27.json`.

## Candidate patterns for later ablation

These are candidates only. None may enter the engine without the required 20+ text ablation and detector/readability/meaning evidence:

- bounded sentence-length rhythm windows targeting the measured mean/SD without forcing a fixed sequence;
- split/merge experiments that increase natural rhythm rather than word substitutions;
- conservative clause-position variation using only meaning-neutral structures;
- transition deletion/sparsity, never formal-transition rotation;
- specificity flagging for claims without an observed number, named method, dataset, or example;
- qualification and contrast-preserving edits that leave negation and modal force unchanged;
- non-formula closing suggestions, presented for review rather than automatically inserted.
