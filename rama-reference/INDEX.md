# Rama + Agent-o-rama Reference System — INDEX

Purpose: Claude/Claude Code has NO Rama or Agent-o-rama knowledge in training data.
This directory is the source of truth. **Never guess Rama APIs — read these files.**
Primary language: **Java**. (Clojure material kept where it clarifies concepts.)

Every extracted doc has its source URL stamped at the top. For version-sensitive
details (exact signatures, Maven coordinates, config keys), verify against the
live source before writing final code.

## Live-fetch verification URLs
- Rama docs: https://redplanetlabs.com/docs/~/index.html
- Rama Javadoc: https://redplanetlabs.com/javadoc/index.html (fetch specific classes as needed)
- Agent-o-rama repo + wiki: https://github.com/redplanetlabs/agent-o-rama
- Downloads/Maven coordinates: https://redplanetlabs.com/docs/~/downloads-maven-local-dev.html

- **BRIDGE-clojure-to-java.md** — read this before using any Clojure-targeted material (RPL skill, clj-* docs) in this Java project

## Directory map

### docs-rama-site/ — Official Rama documentation (34 pages, markdown)
Core concepts, in recommended reading order:
- terminology.md, why-use-rama.md — orientation
- tutorial1..6.md — the official Java tutorial sequence
- depots.md — event logs (names start with `*`)
- pstates.md — partitioned indexed state (names start with `$$`), schemas, subindexing, reactive queries
- paths.md — the Path API for querying/transforming PStates (READ BEFORE any PState query code)
- stream.md, microbatch.md — the two ETL topology types and their guarantees
- query.md — query topologies (cross-partition, on-demand)
- intermediate-dataflow.md — dataflow language deep dive
- aggregators.md — accumulators vs combiners, built-ins
- partitioners.md — controlling where computation runs
- serialization.md — custom types across the cluster
- testing.md — InProcessCluster patterns
- integrating.md — external systems, module dependencies: module-dependencies.md
- rest.md — REST API to depots/PStates
- Operations: acid.md, replication.md, backups.md, operating-rama.md, heterogenous-clusters.md, all-configs.md
- downloads-maven-local-dev.md — Maven deps, local dev setup
- clj-*.md — Clojure API equivalents (secondary; useful for reading Clojure examples)

### docs-agent-o-rama/ — Complete Agent-o-rama wiki (markdown)
- Home.md, Quickstart.md — start here
- Programming-agents.md — THE core reference: nodes, emits, graphs, virtual threads
- Agent-client-API.md — invoking agents from client code
- Tools.md — tool definition and use
- Interfacing-with-LLMs.md — LangChain4j integration
- Streaming.md — streaming model output to clients
- Human‐in‐the‐loop.md, Human-feedback.md — pause/resume patterns
- Datasets,-evaluators,-and-experiments.md — evaluation framework
- Actions,-rules,-and-telemetry.md — online evaluation and monitoring
- Integrating-with-regular-Rama-modules.md — combined RamaModule + AgentTopology
- *-comparison.md — vs LangGraph/LangSmith, LangChain4j, Spring AI, Koog, Embabel, LangGraph4j

### repos/agent-o-rama/ — Full source + runnable examples
- examples/java/src/main/java/ — 24 working Java examples: BasicAgent, MultiNodeAgent,
  RouterAgent, AggregationAgent, KeyValueStoreAgent, DocumentStoreAgent, PStateStoreAgent,
  AgentObjectsAgent, LangChain4jAgent, StreamingAgent, StreamingLangchain4jAgent,
  StructuredLangchain4jAgent, HumanInputAgent, AsyncAgent, MirrorAgent, RecordOpAgent,
  MultiAggAgent, RamaModuleAgent, TinyJavaTopologyExample, ReAct + Research agents.
  **Prefer adapting these over writing from scratch.**
- examples/clj/ — Clojure equivalents

### repos/rama-demo-gallery/ — Short, thoroughly-commented Rama use-case demos

### repos/rama-ai-learn/ — RPL's own harness for teaching LLMs Rama
- plugins/rama-skill/skills/rama/ — **RPL's own Rama skill: SKILL.md + ~35 reference files**
  (aggregators, paths, pstate-schema, microbatch, query-topologies, testing, troubleshooting,
  depot-design, patterns, phased build methodology). Clojure-targeted but conceptually
  authoritative — written by Rama's creators specifically for AI agents.
- challenges/ — realistic Rama build problems with reference implementations (large test
  data pruned)

### skill-updated/ — Updated claude.ai skill (install via Claude settings > Capabilities)
- SKILL.md + ref_01..07 — curated Java patterns, corrected for macOS/M4

## Rules that prevent the classic failures
1. Depot names start with `*`; PState/store names start with `$$`.
2. In AgentModule graphs: every branch must end in `agentNode.result(...)`.
3. Combined modules: `agentTopology.define()` must be the LAST call in `define()`.
4. Aggregation (aggStartNode/aggNode) only for parallel LLM/API fan-out — it's expensive.
5. Tests: use InProcessCluster; wait with `waitForMicrobatchProcessedCount` for microbatch.
