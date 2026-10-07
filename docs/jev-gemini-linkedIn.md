# Generative vs. Discriminative AI: Solving the "Hallucination" Problem in UI Highlighting

At Rotpunkt Translate, we are building an AI-assisted translation tool for the kitchen manufacturing industry. A critical feature of the UI is a side-by-side translation preview where specific terminology is visually highlighted for the human reviewer. 

While exact glossary matches (F1) and "Do Not Translate" brands (F2) are easily handled via deterministic regex, extracting contextual terminology required an AI pipeline.

## The Goal (F3 & F4)
We needed to automatically highlight two complex categories of words in the translated English text:
*   **F3 (Kitchen Trade Terms):** Highly technical manufacturing jargon (e.g., "melamine resin coated", "ABS edge banding") that aren't in a strict glossary but require specialized knowledge.
*   **F4 (Ambiguous Terms):** Generic structural words (e.g., "filler panel", "fascia") whose exact translation depends heavily on their physical location in the kitchen layout, requiring human review.

**Input:** `"If dealing with a blind corner, use the filler panel to bridge the gap before attaching the fascia."`
**Expected Output:** Highlight `"blind corner"` (F4), `"filler panel"` (F4), and `"fascia"` (F4).

---

## Approach 1: Gemini 3.5 Flash Lite (Generative LLM)

Our first attempt used a standard generative approach (Zero-shot and Few-shot) where the LLM was asked to read the text and return a JSON array of substrings to highlight.

**The Implementation:**
We batched sentences and used the Gemini SDK with the following prompt structure:
```text
You are a translation QA assistant for a kitchen manufacturer.
Extract words from the segments into these categories:
- "kitchen_trade_term": Technical manufacturing material or jargon.
- "ambiguous_term": Words with multiple valid translations in a kitchen context.

Return a JSON array of arrays containing {"text": "...", "type": "..."}.
If a segment has no matches, return an empty array [].
```

**The Metrics (Eval on 100 Segments):**
*   **F3 (Trade Terms):** Precision 0.0%, Recall 0.0%
*   **F4 (Ambiguous Terms):** Precision 28.6%, Recall 25.0%
*   **Clean (Negative Control):** Precision 0.0% (7 False Positives)
*   **Runtime:** ~1.5 - 2.5 seconds per batch.

**Identified Issues:**
1.  **Sycophancy (The False Positive Problem):** The LLM felt compelled to "succeed" by finding an answer. When given perfectly standard text (like a warranty warning), it hallucinated matches, flagging words like `"warranty"` or `"dry"` as ambiguous.
2.  **String Matching:** Generative LLMs struggle with exact string extraction boundaries. They would extract `"melamine"` instead of the full `"melamine resin coated"`, causing strict evaluation logic to fail.

---

## Approach 2: JEV (Discriminative AI)

To fix the hallucinations, we switched to **JEV**, a discriminative "System One" model by TypeSafe AI (via OpenRouter). JEV doesn't generate text; it mathematically scores probability distributions for multiple-choice questions.

**The Implementation (N-grams + 2-Stage Hierarchical + Trimming):**
Instead of asking the AI to extract words, we explicitly chunked the sentence into 1, 2, and 3-grams (e.g., `"filler"`, `"panel"`, `"filler panel"`) and asked JEV to score them.

*   **Stage 1 (The Gatekeeper):** We asked JEV if the chunk was `specialized` (kitchen part/layout) or `generic` (standard everyday words like 'the', 'dry', 'attach').
*   **Stage 2 (The Classifier):** For chunks that passed Stage 1, we asked if they were a `kitchen_trade_term` or `ambiguous_term`.
*   **Boundary Trimming:** If a 3-gram like `"filler panel to"` survived Stage 2, we used the Stage 1 scores of its individual words to mathematically trim off the generic word (`"to"`), leaving perfect highlight bounds.

**The Metrics:**
By using a Raw Probability threshold of `>= 0.60` (60% certainty), the results were phenomenal:

*   **F3 (Trade Terms):** Precision 89.7%, Recall 100.0%
*   **F4 (Ambiguous Terms):** Precision 87.2%, Recall 87.2%
*   **Clean (Negative Control):** Precision 100.0% (0 False Positives)
*   **Runtime:** ~500ms for 44 parallel chunk evaluations.

**The Findings:**
Because JEV relies on isolated probability scoring rather than generative text fulfillment, **the false positive problem completely disappeared**. It confidently assigned >99% probability to `"none"` for normal text, leaving our UI clean while capturing the exact bounds of complex kitchen jargon.