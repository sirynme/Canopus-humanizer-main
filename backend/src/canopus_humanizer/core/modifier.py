"""canopus-humanizer text transformation engine."""

import random
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from canopus_humanizer.config import GLOBAL_CONFIG, ConfigNamespace
from canopus_humanizer.core.protection import ConservativeProtectionLayer
from canopus_humanizer.core.rules import (
    APPOSITIVES,
    CONJUNCTIONS,
    DETERMINERS,
    DISCOURSE_MARKERS,
    HEDGE_WORDS,
    NOMINALIZATIONS,
    PHRASES,
    PROTECTED_TERMS,
    SYNONYMS,
    TRANSITIONS,
)


class DocumentModifier:
    """Core transformation engine for text processing."""

    def __init__(self, config: Optional[ConfigNamespace] = None, seed: Optional[int] = None):
        self.config = config or GLOBAL_CONFIG
        self.rng = random.Random(seed if seed is not None else 42)
        
        # State tracking
        self.changes_log: List[Dict[str, Any]] = []
        self._used_appositives: Set[str] = set()
        self._used_discourse_replacements: Dict[str, Set[str]] = {}
        self._latex_placeholders: List[str] = []

        # Operational Transformation Counters
        self.phrase_rewrite_count = 0
        self.synonym_count = 0
        self.clause_reorder_count = 0
        self.determiner_swap_count = 0
        self.compound_split_count = 0
        self.hedge_word_count = 0
        self.ngram_break_count = 0
        self.voice_transform_count = 0
        self.sentence_fusion_count = 0
        self.transition_inject_count = 0
        self.clause_word_reorder_count = 0
        self.nominalization_count = 0
        self.appositive_count = 0
        self.discourse_rotate_count = 0
        self.citation_count = 0

    @property
    def total_transforms(self) -> int:
        return (
            self.phrase_rewrite_count
            + self.synonym_count
            + self.clause_reorder_count
            + self.determiner_swap_count
            + self.compound_split_count
            + self.hedge_word_count
            + self.ngram_break_count
            + self.voice_transform_count
            + self.sentence_fusion_count
            + self.transition_inject_count
            + self.clause_word_reorder_count
            + self.nominalization_count
            + self.appositive_count
            + self.discourse_rotate_count
            + self.citation_count
        )

    # --------------------------------------------------------------------------
    # STAGE 1: LaTeX & Formatting Protection
    # --------------------------------------------------------------------------
    def _protect_latex(self, text: str) -> str:
        """Mask equations, macros, and citations with zero-byte placeholders."""
        self._latex_placeholders = []

        def repl(match):
            placeholder = f"\x00_LTX_{len(self._latex_placeholders)}_\x00"
            self._latex_placeholders.append(match.group(0))
            return placeholder

        # 1. Math environments: $$...$$, $...$, \[...\], \(...\)
        text = re.sub(r"\$\$[\s\S]*?\$\$|\$[^\$\n]+?\$|\\\[[\s\S]*?\\\]|\\\(.*?\\\)", repl, text)
        # 2. LaTeX commands: \begin{...}...\end{...}, \cite{...}, \ref{...}, \command{...}
        text = re.sub(r"\\begin\{[a-zA-Z*]+\}[\s\S]*?\\end\{[a-zA-Z*]+\}", repl, text)
        text = re.sub(r"\\[a-zA-Z]+\*?(?:\[.*?\])?(?:\{.*?\})*", repl, text)
        # 3. HTML/XML Tags
        text = re.sub(r"<[^>]+>", repl, text)
        return text

    def _restore_latex(self, text: str) -> str:
        """Restore all masked placeholders."""
        for idx, original in enumerate(self._latex_placeholders):
            placeholder = f"\x00_LTX_{idx}_\x00"
            text = text.replace(placeholder, original)
        return text

    # --------------------------------------------------------------------------
    # STAGE 2: Multi-Word Phrase Rewrites
    # --------------------------------------------------------------------------
    def _apply_phrase_rewrites(self, text: str) -> str:
        if not self.config.ENABLE_PHRASE_REWRITE:
            return text

        for pattern, replacement in PHRASES:
            if re.search(pattern, text, flags=re.IGNORECASE):
                def replace_case(m):
                    orig = m.group(0)
                    rep = replacement
                    if orig.isupper():
                        rep = rep.upper()
                    elif orig[0].isupper():
                        rep = rep[0].upper() + rep[1:]
                    self.phrase_rewrite_count += 1
                    self.changes_log.append({"stage": "phrase_rewrite", "from": orig, "to": rep})
                    return rep

                text = re.sub(pattern, replace_case, text, flags=re.IGNORECASE)
        return text

    # --------------------------------------------------------------------------
    # STAGE 3: Rare Academic Synonym Substitution
    # --------------------------------------------------------------------------
    def _apply_synonyms(self, text: str, protected_terms: Optional[Set[str]] = None) -> str:
        if not self.config.ENABLE_SYNONYMS:
            return text

        effective_protected = PROTECTED_TERMS | (protected_terms or set())
        fire_threshold = (self.config.INTENSITY / 100.0) * self.config.SYNONYM_ALIGNMENT

        words = re.findall(r"\b\w+\b|[^\w\s]|\s+", text)
        modified_tokens = []

        for token in words:
            lower_token = token.lower()
            if (
                token.isalpha()
                and lower_token in SYNONYMS
                and lower_token not in effective_protected
                and token not in effective_protected
                and "\x00" not in token
            ):
                if self.rng.random() < fire_threshold:
                    candidates = SYNONYMS[lower_token]
                    choice = self.rng.choice(candidates)
                    if token.isupper():
                        choice = choice.upper()
                    elif token[0].isupper():
                        choice = choice[0].upper() + choice[1:]

                    self.synonym_count += 1
                    self.changes_log.append({"stage": "synonym", "from": token, "to": choice})
                    modified_tokens.append(choice)
                    continue

            modified_tokens.append(token)

        return "".join(modified_tokens)

    # --------------------------------------------------------------------------
    # STAGE 4: Clause Reordering (Subordinate Shift)
    # --------------------------------------------------------------------------
    def _reorder_clauses(self, text: str) -> str:
        if not self.config.ENABLE_CLAUSE_REORDER or len(text) < 60 or "\x00" in text:
            return text

        if self.rng.random() > 0.25:
            return text

        # Match: [Main Clause], [Conjunction] [Subordinate Clause].
        for conj in CONJUNCTIONS:
            pattern = rf"^([A-Z][^,]+?),\s+({re.escape(conj)}\s+[^.]+?)(\.|\?|!)$"
            match = re.match(pattern, text)
            if match:
                main_clause, sub_clause, punct = match.groups()
                # Subordinate shifted to front: Conj sub_clause, main_clause.
                conj_first = sub_clause[0].upper() + sub_clause[1:]
                main_lower = main_clause[0].lower() + main_clause[1:]
                reordered = f"{conj_first}, {main_lower}{punct}"
                self.clause_reorder_count += 1
                self.changes_log.append({"stage": "clause_reorder", "from": text, "to": reordered})
                return reordered
        return text

    # --------------------------------------------------------------------------
    # STAGE 5: Determiner Rotation (Article & Quantifier Swaps)
    # --------------------------------------------------------------------------
    def _swap_determiners(self, text: str) -> str:
        if not self.config.ENABLE_DETERMINER_SWAP or "\x00" in text:
            return text

        for det, alternatives in DETERMINERS.items():
            pattern = rf"\b{re.escape(det)}\b"
            if re.search(pattern, text, flags=re.IGNORECASE):
                if self.rng.random() < 0.40:
                    def det_repl(m):
                        orig = m.group(0)
                        choice = self.rng.choice(alternatives)
                        if orig.isupper():
                            choice = choice.upper()
                        elif orig[0].isupper():
                            choice = choice[0].upper() + choice[1:]
                        self.determiner_swap_count += 1
                        self.changes_log.append({"stage": "determiner_swap", "from": orig, "to": choice})
                        return choice

                    text = re.sub(pattern, det_repl, text, count=1, flags=re.IGNORECASE)
        return text

    # --------------------------------------------------------------------------
    # STAGE 6: Compound Sentence Splitting (Burstiness Variance)
    # --------------------------------------------------------------------------
    def _split_compound_sentences(self, text: str) -> str:
        if not self.config.ENABLE_SPLIT_COMPOUND or len(text) < 90 or "\x00" in text:
            return text

        if self.rng.random() > 0.30:
            return text

        # Split on "; " or ", and ", ", but "
        split_pattern = r"(?<=[a-zA-Z0-9]),\s+(and|furthermore|moreover|consequently|whereas)\s+"
        if re.search(split_pattern, text, flags=re.IGNORECASE):
            parts = re.split(split_pattern, text, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 3:
                first_sentence = parts[0].strip()
                connector = parts[1].strip().capitalize()
                second_sentence = parts[2].strip()
                split_res = f"{first_sentence}. {connector}, {second_sentence}"
                self.compound_split_count += 1
                self.changes_log.append({"stage": "split_compound", "from": text, "to": split_res})
                return split_res
        return text

    # --------------------------------------------------------------------------
    # STAGE 7: Hedge Word Injection (Entropy Boost)
    # --------------------------------------------------------------------------
    def _insert_hedge_words(self, text: str) -> str:
        if not getattr(self.config, "ENABLE_HEDGE_WORDS", False) or len(text) < 70 or "\x00" in text or not HEDGE_WORDS:
            return text

        if self.rng.random() > 0.30:
            return text

        # Inject after a naturally occurring comma
        comma_matches = list(re.finditer(r",\s+", text))
        if comma_matches:
            target = self.rng.choice(comma_matches)
            hedge = self.rng.choice(HEDGE_WORDS)
            pos = target.end()
            text = text[:pos] + f"{hedge}, " + text[pos:]
            self.hedge_word_count += 1
            self.changes_log.append({"stage": "hedge_word_inject", "hedge": hedge})
        return text

    # --------------------------------------------------------------------------
    # STAGE 8: N-Gram Adjustment
    # --------------------------------------------------------------------------
    def _break_ngram_chains(self, text: str) -> str:
        if not self.config.ENABLE_NGRAM_AUDIT or "\x00" in text:
            return text

        words = text.split()
        if len(words) < 8:
            return text

        # Break unbroken chains exceeding 5 words by injecting an academic adverb or permuting
        new_words = []
        i = 0
        while i < len(words):
            new_words.append(words[i])
            if (i > 0) and (i % 6 == 0) and self.rng.random() < 0.35:
                adverb = self.rng.choice(["broadly", "reliably", "manifestly", "empirically", "inherently"])
                new_words.append(adverb)
                self.ngram_break_count += 1
            i += 1

        return " ".join(new_words)

    # --------------------------------------------------------------------------
    # STAGE 9: Active <-> Passive Voice Transformation
    # --------------------------------------------------------------------------
    def _transform_voice(self, text: str) -> str:
        if not self.config.ENABLE_VOICE_TRANSFORM or len(text) < 60 or "\x00" in text:
            return text

        if self.rng.random() > self.config.VOICE_TRANSFORM_RATE:
            return text

        # Regex patterns for active -> passive
        # "We analyzed the results" -> "The results were analyzed"
        active_pattern = r"\b(we|the researchers|this study|our team)\s+(analyzed|demonstrated|investigated|evaluated|computed|observed|formulated)\s+(the\s+[^,\.]+)"
        match = re.search(active_pattern, text, flags=re.IGNORECASE)
        if match:
            subject, verb, obj = match.groups()
            obj_capitalized = obj[0].upper() + obj[1:]
            is_plural = obj.strip().lower().endswith(("results", "findings", "observations", "data", "models", "clusters", "records", "samples", "methods", "algorithms", "values", "statistics"))
            aux = "were" if is_plural else "was"
            passive_repl = f"{obj_capitalized} {aux} {verb.lower()}"
            text = text[:match.start()] + passive_repl + text[match.end():]
            self.voice_transform_count += 1
            self.changes_log.append({"stage": "voice_transform", "from": match.group(0), "to": passive_repl})
        return text

    # --------------------------------------------------------------------------
    # STAGE 10: Sentence Fusion (Anti-Burstiness Merger)
    # --------------------------------------------------------------------------
    def fuse_adjacent_sentences(self, sentences: List[str]) -> List[str]:
        if not self.config.ENABLE_SENTENCE_FUSION or len(sentences) < 2:
            return sentences

        fused = []
        i = 0
        while i < len(sentences):
            curr = sentences[i].strip()
            # Safeguard: never fuse structural headings or numbered items
            is_heading_or_list = bool(
                re.match(r"^(?:\d+\.\s+|RQ\d+:|H[01]:|[-*•]\s+)", curr, flags=re.IGNORECASE) or
                (i < len(sentences) - 1 and re.match(r"^(?:\d+\.\s+|RQ\d+:|H[01]:|[-*•]\s+)", sentences[i + 1].strip(), flags=re.IGNORECASE))
            )
            if (
                not is_heading_or_list
                and i < len(sentences) - 1
                and len(curr) < 80
                and len(sentences[i + 1].strip()) < 80
                and "\x00" not in curr
                and "\x00" not in sentences[i + 1]
                and self.rng.random() < self.config.SENTENCE_FUSION_RATE
            ):
                nxt = sentences[i + 1].strip()
                connector = self.rng.choice([
                    ", which consequently",
                    ", thereby requiring",
                    ", thus leading to",
                    ", and as a result"
                ])
                # Lowercase start of next sentence if regular word
                cleaned_nxt = nxt[0].lower() + nxt[1:] if nxt and nxt[0].isupper() else nxt
                merged = curr.rstrip(".!?") + connector + " " + cleaned_nxt
                fused.append(merged)
                self.sentence_fusion_count += 1
                self.changes_log.append({"stage": "sentence_fusion", "fused": merged[:60]})
                i += 2
            else:
                fused.append(curr)
                i += 1
        return fused

    # --------------------------------------------------------------------------
    # STAGE 11: Transition Phrase Injection
    # --------------------------------------------------------------------------
    def _inject_transitions(self, text: str) -> str:
        if not self.config.ENABLE_TRANSITION_INJECT or len(text) < 70 or "\x00" in text:
            return text

        if self.rng.random() > self.config.TRANSITION_INJECT_RATE:
            return text

        # Select a category
        cat = self.rng.choice(list(TRANSITIONS.keys())) if TRANSITIONS else None
        if not cat:
            return text

        candidates = TRANSITIONS[cat]
        phrase = self.rng.choice(candidates)
        prefix = phrase[0].upper() + phrase[1:]

        # Insert at sentence start if not already preceded by transition
        if not re.match(r"^(Moreover|Furthermore|However|Therefore|Thus|Indeed|In addition),", text, flags=re.IGNORECASE):
            text = f"{prefix}, {text[0].lower() + text[1:]}"
            self.transition_inject_count += 1
            self.changes_log.append({"stage": "transition_inject", "phrase": prefix})
        return text

    # --------------------------------------------------------------------------
    # STAGE 12: Clause-Level Word Reordering
    # --------------------------------------------------------------------------
    def _reorder_within_clause(self, text: str) -> str:
        if not self.config.ENABLE_WORD_REORDER or len(text) < 80 or "\x00" in text:
            return text

        if self.rng.random() > self.config.WORD_REORDER_RATE:
            return text

        # Target: "In/For/Using/By/With/Through X, [clause]" -> "[clause], in/for/using/by/with/through X"
        prep_pattern = r"^(In|For|Using|By|With|Through)\s+([^,]+),\s+([^.]+)(\.|\?|!)$"
        match = re.match(prep_pattern, text)
        if match:
            prep, modifier, clause, punct = match.groups()
            clause_capitalized = clause[0].upper() + clause[1:]
            reordered = f"{clause_capitalized}, {prep.lower()} {modifier}{punct}"
            self.clause_word_reorder_count += 1
            self.changes_log.append({"stage": "reorder_within_clause", "from": text, "to": reordered})
            return reordered
        return text

    # --------------------------------------------------------------------------
    # STAGE 13: Nominalization / De-nominalization
    # --------------------------------------------------------------------------
    def _nominalize(self, text: str) -> str:
        if not self.config.ENABLE_NOMINALIZATION or len(text) < 40 or "\x00" in text:
            return text

        if self.rng.random() > self.config.NOMINALIZATION_RATE:
            return text

        # Look for "We [verb](ed|d|ing) the [target]" -> "An [noun] of the [target] was conducted"
        for verb, noun in NOMINALIZATIONS.items():
            stem = verb[:-1] if verb.endswith("e") else verb
            pattern = rf"\b(we|the team|researchers)\s+(?:{re.escape(verb)}|{re.escape(stem)}ed|{re.escape(stem)}d|{re.escape(stem)}ing)\s+the\s+([^,\.]+)"
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                target = match.group(2).strip()
                article = "An" if noun[0].lower() in "aeiou" else "A"
                replacement = f"{article} {noun} of the {target} was conducted"
                text = text[:match.start()] + replacement + text[match.end():]
                self.nominalization_count += 1
                self.changes_log.append({"stage": "nominalization", "from": match.group(0), "to": replacement})
                break
        return text

    # --------------------------------------------------------------------------
    # STAGE 14: Appositive Clause Injection
    # --------------------------------------------------------------------------
    def _inject_appositives(self, text: str) -> str:
        if not self.config.ENABLE_APPOSITIVE or "\x00" in text:
            return text

        if self.rng.random() > self.config.APPOSITIVE_RATE:
            return text

        for term, appositive in APPOSITIVES.items():
            if term not in self._used_appositives and re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE):
                pattern = rf"(\b{re.escape(term)}\b)"
                replacement = rf"\1, {appositive},"
                text = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
                self._used_appositives.add(term)
                self.appositive_count += 1
                self.changes_log.append({"stage": "appositive_inject", "term": term})
                break
        return text

    # --------------------------------------------------------------------------
    # STAGE 15: Discourse Marker Rotation
    # --------------------------------------------------------------------------
    def _rotate_discourse_markers(self, text: str) -> str:
        if not self.config.ENABLE_DISCOURSE_ROTATE or "\x00" in text:
            return text

        if self.rng.random() > self.config.DISCOURSE_ROTATE_RATE:
            return text

        for marker, alternatives in DISCOURSE_MARKERS.items():
            pattern = rf"\b{re.escape(marker)},\s*"
            if re.search(pattern, text, flags=re.IGNORECASE):
                used = self._used_discourse_replacements.setdefault(marker, set())
                avail = [a for a in alternatives if a not in used] or alternatives
                choice = self.rng.choice(avail)
                used.add(choice)

                def dm_repl(m):
                    self.discourse_rotate_count += 1
                    self.changes_log.append({"stage": "discourse_rotate", "from": marker, "to": choice})
                    return f"{choice}, "

                text = re.sub(pattern, dm_repl, text, count=1, flags=re.IGNORECASE)
        return text

    # --------------------------------------------------------------------------
    # STAGE 17: Citation Injection
    # --------------------------------------------------------------------------
    def _maybe_add_citation(
        self,
        text: str,
        enable_citations: bool = False,
        citation_format: str = "IEEE [1]",
        current_index: int = 1
    ) -> str:
        if not enable_citations:
            return text

        marker = f" [{current_index}]" if "IEEE" in citation_format else f" (Ref. {current_index})"
        if "LaTeX" in citation_format:
            marker = f" \\cite{{ref_{current_index}}}"

        # Place before terminal period if present
        if text.endswith((".", "!", "?")):
            text = text[:-1] + marker + text[-1]
        else:
            text = text + marker

        self.citation_count += 1
        return text

    # --------------------------------------------------------------------------
    # UNIFIED EXECUTION PIPELINE
    # --------------------------------------------------------------------------
    def _apply_transforms_to_protected(self, text: str, protected_terms: Optional[Set[str]] = None) -> str:
        """Executes active stages on protected text."""
        # Step 2: Multi-word phrase rewrites
        if getattr(self.config, "ENABLE_PHRASE_REWRITE", True):
            text = self._apply_phrase_rewrites(text)

        # Step 3: Rare academic synonyms
        if getattr(self.config, "ENABLE_SYNONYMS", True):
            text = self._apply_synonyms(text, protected_terms=protected_terms)

        # Step 4: Reorder clauses
        if getattr(self.config, "ENABLE_CLAUSE_REORDER", False):
            text = self._reorder_clauses(text)

        # Step 5: Swap determiners
        if getattr(self.config, "ENABLE_DETERMINER_SWAP", True):
            text = self._swap_determiners(text)

        # Step 6: Split compound sentences
        if getattr(self.config, "ENABLE_SPLIT_COMPOUND", False):
            text = self._split_compound_sentences(text)

        # Step 7: Insert hedge words
        if getattr(self.config, "ENABLE_HEDGE_WORDS", False):
            text = self._insert_hedge_words(text)

        # Step 8: Break 5-gram chains
        if getattr(self.config, "ENABLE_NGRAM_AUDIT", False):
            text = self._break_ngram_chains(text)

        # Step 9: Active <-> Passive voice transform
        if getattr(self.config, "ENABLE_VOICE_TRANSFORM", False):
            text = self._transform_voice(text)

        # Step 11: Transition injection
        if getattr(self.config, "ENABLE_TRANSITION_INJECT", False):
            text = self._inject_transitions(text)

        # Step 12: Reorder within clause
        if getattr(self.config, "ENABLE_WORD_REORDER", False):
            text = self._reorder_within_clause(text)

        # Step 13: Nominalization
        if getattr(self.config, "ENABLE_NOMINALIZATION", False):
            text = self._nominalize(text)

        # Step 14: Appositive injection
        if getattr(self.config, "ENABLE_APPOSITIVE", False):
            text = self._inject_appositives(text)

        # Step 15: Rotate discourse markers
        if getattr(self.config, "ENABLE_DISCOURSE_ROTATE", True):
            text = self._rotate_discourse_markers(text)

        return text

    def modify_line(
        self,
        line: str,
        protected_terms: Optional[Set[str]] = None,
        enable_citations: bool = False,
        citation_format: str = "IEEE [1]",
        citation_index: int = 1
    ) -> str:
        """Executes the transformation sequence on a single sentence or text unit."""
        if not line or not line.strip():
            return line

        # If line already contains placeholders, it is part of a pre-protected block
        if "\x00_PROT_" in line:
            text = self._apply_transforms_to_protected(line, protected_terms=protected_terms)
            if enable_citations and getattr(self.config, "ENABLE_CITATION_SHIELDING", False):
                text = self._maybe_add_citation(text, enable_citations=True, citation_format=citation_format, current_index=citation_index)
            return text

        layer = ConservativeProtectionLayer(additional_protected_terms=protected_terms)
        protected_text, _ = layer.protect(line)

        transformed = self._apply_transforms_to_protected(protected_text, protected_terms=protected_terms)

        restored_text, ok_rest = layer.restore(transformed, original_raw_text=line)
        if not ok_rest:
            return line

        text = restored_text
        if enable_citations and getattr(self.config, "ENABLE_CITATION_SHIELDING", False):
            text = self._maybe_add_citation(text, enable_citations=True, citation_format=citation_format, current_index=citation_index)

        return text

    def modify_document(
        self,
        text: str,
        protected_terms: Optional[Set[str]] = None,
        enable_citations: bool = False,
        citation_format: str = "IEEE [1]",
        max_citations: int = 2
    ) -> str:
        """Transforms a full multi-sentence document with paragraph and fusion preservation."""
        if not text or not text.strip():
            return text

        if (
            getattr(self.config, "ENABLE_PHRASE_REWRITE", True)
            or getattr(self.config, "ENABLE_SYNONYMS", True)
        ) and not (SYNONYMS or PHRASES):
            import warnings
            warnings.warn(
                "Legacy rules failed to load or are empty in DocumentModifier; "
                "transformations cannot be applied and text will remain unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

        paragraphs = text.split("\n\n")
        processed_paragraphs = []
        citation_idx = 1

        for para in paragraphs:
            if not para.strip():
                processed_paragraphs.append(para)
                continue

            # Multi-tier protection at paragraph level preserves math, environments, and headings
            layer = ConservativeProtectionLayer(additional_protected_terms=protected_terms)
            prot_para, _ = layer.protect(para)

            # Split paragraph into sentences on protected string
            sentence_splits = re.split(r"(?<=[.!?])\s+", prot_para.strip())
            
            # Stage 10: Sentence fusion across adjacent short sentences
            fused_sentences = self.fuse_adjacent_sentences(sentence_splits)

            modified_sentences = []
            for sent in fused_sentences:
                should_cite = enable_citations and (citation_idx <= max_citations) and (self.rng.random() < 0.5 or len(fused_sentences) <= max_citations)
                mod_sent = self.modify_line(
                    sent,
                    protected_terms=protected_terms,
                    enable_citations=should_cite,
                    citation_format=citation_format,
                    citation_index=citation_idx
                )
                if should_cite and getattr(self.config, "ENABLE_CITATION_SHIELDING", False):
                    citation_idx += 1
                modified_sentences.append(mod_sent)

            para_transformed = " ".join(modified_sentences)
            restored_para, ok_rest = layer.restore(para_transformed, original_raw_text=para)
            if not ok_rest:
                processed_paragraphs.append(para)
            else:
                processed_paragraphs.append(restored_para)

        return "\n\n".join(processed_paragraphs)
