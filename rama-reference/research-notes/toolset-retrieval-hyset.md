# Design Note: Set-Level Tool Retrieval (HYSET) → Rama/Agent-o-rama
Source: arXiv:2607.25718v2 (Hong, Dong, Yu, Jiang, 29 Jul 2026) — full text read & verified 2026-07-31
Status: NOTE, not a build. Relevant when tool count grows large (hundreds+) or
tool-selection failures appear in traces. Substrate costs nothing to preserve now.

## The problem it solves
Per-tool relevance ranking retrieves individually-relevant, collectively-incomplete
sets. Verified stat: fine-tuned Contriever on ToolBench = 68.6% Recall@3 but only
39.7% COMP@3 (complete-set coverage). Tasks need jointly-useful SETS.

## Verified core math
- Score F(x,E) = F_set(E) + F_align(x,E)
- F_set(E) = Σ_{a<b} z_a^T M_m z_b — pairwise sum with CARDINALITY-SPECIFIC
  matrix M_m (m = |E|). Theorem 1 (Möbius): cardinality-varying matrices ⟺
  higher-order (>2) interactions, at O(M·d²) params vs O(d^M) for explicit tensors.
- F_align: cross-attention pooling of query embedding over tool embeddings;
  attention weights depend on ALL tools in E, so alignment is set-level too.
- Training: contrastive loss over negative pools (50% random size-matched /
  30% other-queries' ground truth / 20% hard negatives via embedding-neighbor
  swaps) + reward-weighted self-training: agent executes with selected set,
  LLM-judge scores, success reinforces the selection.
- Inference (two-stage, 12.4ms @ 13,860 tools): (1) top-K1 by per-tool relevance,
  then EXPAND shortlist by complementarity g(t)=max_i z_t^T M z_i — admits
  low-relevance/high-complementarity tools; (2) exhaustively score all subsets
  of the small shortlist.
- Results: COMP@5 77.55% vs 70.01% best baseline; end-to-end pass rate +13.1%
  relative. Ablations: F_set removal costs 13.1% COMP (set scoring is load-bearing);
  cardinality-specific > shared matrix > identity.

## Mapping to Rama/AOR primitives (when needed)
1. Training data = AOR traces. Every invocation's tool calls + evaluator verdict
   are already captured. successful-invocation events → depot.
2. Hypergraph = nested PStates. Co-occurrence per size bucket:
   $$tool-cooccur: [set-size][toolA][toolB] → count  (cheap version of M_m)
   Inverted index: tool → {toolset-ids}.
3. Miner = microbatch topology. Incrementally maintain reward-weighted
   co-occurrence counts (poor-man's L_self: weight by evaluator score).
4. Retrieval = router node. Two-stage shape transfers even without learned
   model: relevance shortlist → complementarity expansion from PState → pass
   set to executor node.
5. Judge = AOR evaluators. LLM-as-judge is a first-class AOR feature.

## Actionable NOW (no ML)
Add COMP-style metric to AOR evaluators: "did the agent have the complete
tool set needed", not just "were retrieved tools relevant". Measurable in
AOR datasets/experiments today.

## Honest caveats
- Co-invocation ≠ causality (Discover AI review): hypergraph learns
  frequently-together, not necessarily-together; annotation/habit bias becomes
  the compatibility geometry. Execution reward partially mitigates (reinforces
  actual success). For a personal assistant learning from own traces, habit
  bias may be acceptable or even desirable — but recognize it.
- Paper assumes static tool library; dynamic growth is open future work.
- At small tool counts (< ~50), full-library-in-context or simple routing
  likely beats all of this. Do not build early.
