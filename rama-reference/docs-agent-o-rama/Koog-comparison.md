<!-- Source: agent-o-rama GitHub wiki (Koog-comparison) | Fetched: 2026-07-30 -->

# Agent-o-rama vs [Koog](https://github.com/JetBrains/koog)

## Similarities

| Feature | Summary |
|--------|---------|
| JVM-based | Both run on the JVM. Koog has a Kotlin API while Agent-o-rama has first-class Java and Clojure APIs.|
| Workflow model | Both support explicit agent workflows. |
| Tool integration | Both allow exposing regular methods/functions as tools. |
| Streaming | Both support streaming LLM outputs. |
| Tracing | Both provide support to trace or inspect model activity. |

---

## Differences

| Area | Agent-o-rama | Koog |
|------|--------------|------|
| Scope | Complete platform: runtime, storage, datasets, experiments, telemetry, UI. | Framework/library focused on agent logic; you bring your own infrastructure. |
| Execution model | Distributed, parallel graph execution with built-in scaling on a Rama cluster. | Runs inside your process; no distributed execution layer. |
| Human-in-the-loop | Built-in pause/resume API for requesting human input during execution. | No equivalent feature. |
| Storage | Built-in, high-performance, scalable, replicated storage (any data model) or external databases | No integrated storage engine; relies on external stores you manage. |
| Datasets | Built-in versioned datasets for capturing inputs/outputs for use in experiments | No dataset system. |
| Experiments | Built-in experiment runner for evaluating agents or individual nodes. | No experiment runner. |
| Actions / online evaluation | Easy to set up custom hooks on production runs for online evaluation, adding to datasets, webhooks, and more. | No equivalent feature |
| Telemetry | Built-in time-series telemetry for agent performance, latency, token usage, model costs, online evaluation | Provides telemetry integrations (e.g. OpenTelemetry) but no built-in time-series storage or dashboards. No online evaluation. |
| UI | Includes UI for traces, datasets, experiments, telemetry. | No built-in UI; depends on external observability tools. |
| Deployment | Runs on a Rama cluster (in-process, single-node, or distributed). Rama is the only dependency. Deploying/updating/scaling agents are one-line CLI commands. | Embedded in your application; scaling, orchestration, and clustering left to you. |
| Platform targets | Server-side JVM focus. | Kotlin Multiplatform (JVM, JS/Wasm, Android, iOS). |

---

# Missing pieces you must build yourself if using Koog alone

Koog gives you an agent framework and DSL, but you must provide the rest:

### Runtime and execution
- Distributed or parallel agent execution across threads/machines
- Backpressure, retries, timeouts, and fault-tolerance across agent steps 
- ause/resume mechanics for human-in-the-loop 

### Storage
- One or more stores for:
  - agent state  
  - datasets  
  - experiments  
  - traces  
  - telemetry  


### Deployment and operations
- Infrastructure for:
  - scaling  
  - clustering  
  - job scheduling  
  - distributed state  
  - durability  
- Rolling updates of new agent versions
- Developer tooling for local runs, testing, and debugging

### Datasets and experiments
- Versioned datasets with reproducibility guarantees  
- Experiment runner to measure agent/node performance and quality
- LLM or code-based evaluators  

### Telemetry and tracing
- Time-series metrics (latency, tokens, errors, costs) can be emitted, but you must choose and operate the backend yourself  
- Dashboards, alerting, and visualizations must be built using external tools (Prometheus, Grafana, Langfuse, OpenTelemetry backends, etc.)  
- Long-term storage and querying of traces and metrics must also be set up and maintained by your team  
