<!-- Source: agent-o-rama GitHub wiki (LangGraph-and-LangSmith-comparison) | Fetched: 2026-07-30 -->

# Agent-o-rama vs [LangGraph](https://www.langchain.com/langgraph) / [LangSmith](https://www.langchain.com/langsmith/observability)

## Similarities

| Feature | Summary |
|--------|----------|
| Agent definitions | Both define agents as explicit graphs of regular functions. |
| Streaming | LLM and other outputs for agent nodes can be streamed with a first-class client API. |
| Forking | Previous executions can be partially modified and executed to test logic variations. |
| Tracing | Both capture structured traces of each run with node-level details. |
| Datasets | Both enable inputs and outputs can be captured into versioned datasets. |
| Experiments | Both enable testing agents or individual nodes over datasets with arbitrary evaluators. |
| Online evaluation / actions | Both support custom hooks on production runs for online evaluation, adding to datasets, webhooks, and more. |
| Human feedback | Both have features for collecting structured and unstructured human feedback directly on runs or via human feedback queues |
| Human input | Both can pause agent execution to collect human input, then resume. |
| Telemetry | Both expose time-series metrics over agent performance, model usage, and online evaluation. |

---

## Differences

| Area | Agent-o-rama | LangGraph / LangSmith |
|------|--------------|------------------------|
| Runtime | JVM  with first-class Java and Clojure APIs | Python |
| Execution model | Distributed, parallel execution with no central coordinator | Executed inside one Python process with central state and limited ability to parallelize |
| Thread model | All agent code runs on [virtual threads](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html), making long-running and blocking code easy and efficient | Regular threads |
| Storage | Built-in, high-performance, scalable, replicated storage (any data model) or external databases | External databases only |
| Human input | Explicit function call: node suspends → waits → resumes | Exception-based breakpoint pattern |
| Deployment | Self-hosted with Rama cluster, free to use up to two nodes and easy to run locally. Deploying/updating/scaling agents are one-line CLI commands. | LangSmith SaaS or self-hosted with Enterprise plan | 
| Feature parity | Missing few-shot examples | 

