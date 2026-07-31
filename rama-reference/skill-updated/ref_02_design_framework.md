# Chat-o-rama Reference 02 — Phase 2 Design Framework & Beginner Mistakes
**Source:** chat.redplanetlabs.com  
**Date captured:** 2026-03-03  
**Language setting:** Java  
**AOR Version:** v0.7.0  

---

## Question Asked

> I am building a reusable design thinking template for someone new to Rama and Agent-o-rama. The template guides them through two phases: Phase 1 is freeform outcome thinking - what do they want the system to DO, in plain language, with no code. Phase 2 converts that into Rama and Agent-o-rama primitives in Java. For Phase 2, what are the correct ordered steps a beginner should walk through to decompose ANY business idea into the right Rama primitives? Specifically: what questions should they ask first (before touching depots or PStates), what is the right order to decide between a pure Rama backend vs an Agent-o-rama agent vs both together, and what are the most common mistakes beginners make when first mapping business logic to Rama's event sourcing and materialized view model?

---

## Docs Referenced by Chat-o-rama

- agent-development-guide: Agent Design and Development
- aor-refdoc: Agent Manager | Agent Topology Builder
- aor and rama (relationship docs)
- aor-wiki: Integrating with regular Rama modules / Adding agents to regular Rama modules / Basic pattern
- aor-refdoc-sections: Rama / Relationships
- aor-wiki-parsed: Home.md Chunk 0 | Programming-agents.md Chunk 7
- rama-shared: Terminology / Topology | About Red Planet Labs | Backups / Conclusion
- aor-wiki-chunked: Programming-agents.md Chunk 14 | Home.md Chunk 0 | Programming-agents.md Chunk 8
- aor-java-examples:
  - Java example demonstrating agent objects for sharing resources across agent nodes
  - Java example demonstrating conditional routing between different nodes in an agent graph
  - Java example demonstrating direct Rama module usage instead of AgentModule
- Agent-o-rama Documentation: Agent-o-rama User Guide / Your Journey | Rama Infrastructure / Rama: The Foundation | What is Agent-o-rama? / Agent-o-rama is Built on Rama | About Red Planet Labs | AI Integration / Advanced Patterns / Multi-Model Agents

---

## Answer: Phase 2 Template — From Business Idea → Rama + Agent-o-rama Primitives

---

### Step 0 — Clarify the "unit of work" BEFORE any Rama primitives

**Goal:** Decide what a single execution of your system is.

**Ask:**
- What is the smallest "thing" a user or external system asks us to do?
  - e.g. "Score this loan application", "Summarize this document", "Route this support ticket"
- What are the inputs to that thing? (types, validation)
- What are the outputs? (types, edge cases, error formats)
- Is the flow:
  - Mostly deterministic rules / transforms?
  - Or does it require LLM reasoning / NLU / NLG?
- Does this unit of work need to:
  - Call external APIs?
  - Call LLMs?
  - Run multiple expensive steps in parallel?

**Why this first?**
- In Agent-o-rama, this "unit of work" maps naturally to one agent invocation.
- In Rama, this helps you see whether you need continuous processing (depots + stream topologies + PStates) or just on-demand computation (agents, query topologies).

---

### Step 1 — Decide: Pure Rama, Agent-o-rama, or Both?

**Decision order:**

1. Is there **continuous or event-driven data processing**?
   - e.g. "Ingest all orders from Kafka and maintain a live dashboard", "Continuously compute risk scores as trades arrive"
   - If yes → you need **Rama depots + stream/microbatch topologies + PStates**

2. Is there an **interactive / request-response / "agentic" workflow**?
   - e.g. "User clicks a button and we orchestrate multiple LLM calls + APIs and return a result"
   - If yes → you need **Agent-o-rama agents**

3. Do you need **both**?
   - Common pattern: Rama topologies maintain materialized views (PStates) from event streams. Agents query those views and/or emit new events.

**Rule of thumb for beginners:**
- "User calls an API and gets a result" → start with **AgentModule only**
- "We process a firehose of events and keep live state" → start with **pure RamaModule**
- Both clearly present → **RamaModule + AgentTopology.create(...)**

---

### Step 2 — If using Agents: Shape the Agent Graph (no storage yet)

**Terminology:**
- **Agent graph:** The directed graph of nodes that defines an agent's execution
- **Agent node:** A single step (a Java function) that can `emit` to other nodes or `result` to finish

**Ask:**
- What are the major steps in the unit of work?
  - e.g. "classify request → maybe call LLM → call external API → format response"
- For each step: What is its single responsibility? What are its inputs and outputs?
- Do we need:
  - A **linear flow**? (most common)
  - **Branching** based on data? → routing node
  - **Parallel expensive steps**? (LLM calls, heavy APIs) → aggregation (`aggStartNode`/`aggNode`)
  - **Loops / recursion**? (e.g. iterative refinement)
  - **Human-in-the-loop**? (pause, wait for human input, resume)

**Best practice:** Keep each node small and focused. Every path through the graph MUST end with `agentNode.result(...)`.

**Simple Java example — branching agent:**

```java
import com.rpl.agentorama.AgentModule;
import com.rpl.agentorama.AgentTopology;
import com.rpl.agentorama.AgentNode;
import java.util.List;
import java.util.HashMap;
import java.util.Map;

public class RouterAgentModule extends AgentModule {
    @Override
    protected void defineAgents(AgentTopology topology) {
        topology
            .newAgent("RouterAgent")
            // Router node: decides which processing node to send to
            .node("route", List.of("handle-urgent", "handle-default"),
                (AgentNode agentNode, String message) -> {
                    if (message.startsWith("urgent:")) {
                        agentNode.emit("handle-urgent", message);
                    } else {
                        agentNode.emit("handle-default", message);
                    }
                })
            // Urgent handler
            .node("handle-urgent", "finalize",
                (AgentNode agentNode, String message) -> {
                    String content = message.substring(7);
                    Map<String, Object> processed = new HashMap<>();
                    processed.put("priority", "HIGH");
                    processed.put("message", content);
                    agentNode.emit("finalize", processed);
                })
            // Default handler
            .node("handle-default", "finalize",
                (AgentNode agentNode, String message) -> {
                    Map<String, Object> processed = new HashMap<>();
                    processed.put("priority", "NORMAL");
                    processed.put("message", message);
                    agentNode.emit("finalize", processed);
                })
            // Final node
            .node("finalize", null,
                (AgentNode agentNode, Map<String, Object> processed) -> {
                    String priority = (String) processed.get("priority");
                    String msg = (String) processed.get("message");
                    agentNode.result("[" + priority + "] " + msg);
                });
    }
}
```

---

### Step 3 — Decide Persistent State vs In-memory Data

**Only now think about Rama storage primitives and Agent-o-rama stores.**

**Terminology:**
- **PState (Rama):** A partitioned, persistent, queryable state built from depots via topologies
- **Depot (Rama):** An append-only event log / input stream
- **Store (Agent-o-rama):** Per-agent persistent state (backed by Rama) used inside agent nodes
  - Key-Value Store
  - Document Store
  - PState Store (schema-driven, partitioned)

**Ask:**
- What data must outlive a single agent invocation? (User profiles, conversation history, long-term metrics)
- Does this data need to be:
  - **Shared across many invocations / services and updated from streams?** → likely a Rama PState
  - **Local to this agent's logic and relatively simple?** → likely an Agent-o-rama store
- Do we need event sourcing (append-only events) and materialized views?
  - If yes, design: Depot(s) for events → stream/microbatch topology to build PStates → query access from agents

**Beginner-friendly rule:**
- Start with **Agent-o-rama stores** if you just need simple persistent state for this agent
- Introduce **depots + PStates** when you have external event sources or need complex, shared, queryable state across modules

---

### Step 4 — Decide External Integrations → Agent Objects

**Terminology:**
- **Agent object:** A shared resource (LLM model, DB client, HTTP client) managed by Agent-o-rama
  - Can be static (simple value) or built via a builder
  - Can be thread-safe (single instance) or pooled

**Ask:**
- Which external systems do we call? (LLMs, vector DBs, REST APIs, internal services)
- For each: Is the client thread-safe? Is it expensive to create?
- Do LLM calls need tools (functions) that call other APIs?

**Pattern:**
- `declareAgentObject` for simple static values (e.g. API keys)
- `declareAgentObjectBuilder` for clients/models

**Java example — LLM as agent object:**

```java
import com.rpl.agentorama.*;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.openai.OpenAiChatModel;

public class LlmAgentModule extends AgentModule {
    @Override
    protected void defineAgents(AgentTopology topology) {
        // Static API key
        topology.declareAgentObject("openai-api-key", System.getenv("OPENAI_API_KEY"));

        // Model builder (pooled by default)
        topology.declareAgentObjectBuilder("openai-model", setup -> {
            String apiKey = (String) setup.getAgentObject("openai-api-key");
            return OpenAiChatModel.builder()
                .apiKey(apiKey)
                .modelName("gpt-4o-mini")
                .build();
        });

        topology.newAgent("LlmAgent")
            .node("process", null,
                (AgentNode agentNode, String input) -> {
                    ChatModel model = (ChatModel) agentNode.getAgentObject("openai-model");
                    String response = model.chat(input);
                    agentNode.result(response);
                });
    }
}
```

---

### Step 5 — If you need Rama + Agents together: integration pattern

**When you've identified both:**
- Continuous/event processing (depots, PStates)
- Interactive agent workflows

**Use:** `RamaModule` + `AgentTopology.create(...)`

**Questions:**
- What events do we ingest? → depots
- What long-lived views do we need? → PStates
- Which parts are interactive workflows? → agents

**Java example — Rama module with an agent:**

```java
import com.rpl.rama.Depot;
import com.rpl.rama.RamaModule;
import com.rpl.rama.module.StreamTopology;
import com.rpl.agentorama.AgentTopology;
import com.rpl.agentorama.AgentNode;
import java.util.HashMap;

public class FeedbackModule implements RamaModule {
    @Override
    public String getModuleName() { return "FeedbackModule"; }

    @Override
    public void define(Setup setup, Topologies topologies) {
        // 1) Rama primitives
        setup.declareDepot("*feedback-events", Depot.random());
        // Define stream/microbatch topologies here to build PStates...

        // 2) Agent topology on top of Rama
        AgentTopology agentTopology = AgentTopology.create(setup, topologies);

        agentTopology
            .newAgent("FeedbackAgent")
            .node("process-feedback", null,
                (AgentNode agentNode, String feedbackText) -> {
                    HashMap<String, Object> response = new HashMap<>();
                    response.put("status", "success");
                    response.put("message", "Processed: " + feedbackText);
                    response.put("length", feedbackText.length());
                    agentNode.result(response);
                });

        // 3) CRITICAL: Must call define() at the end
        agentTopology.define();
    }
}
```

---

### Step 6 — Cross-cutting: Parallelism and Aggregation

**Only consider aggregation when you have expensive parallelizable work (e.g. multiple LLM calls).**

**Ask:**
- Do we have multiple independent expensive operations that can run in parallel?
- Is the overhead of coordination worth it?
- ⚠️ **Aggregation is VERY expensive** and should NOT be used for simple data loops.

**If yes:** design an `aggStartNode` that fans out work + `aggNode`(s) that process and aggregate.  
**If not:** just use a normal loop inside a single node.

---

### Step 7 — Implementation checklist

For each agent:
- [ ] Inputs/outputs clearly typed
- [ ] Graph shape defined (nodes, routing, result paths)
- [ ] Stores declared only when needed (names start with `$$`)
- [ ] Agent objects declared for each external integration
- [ ] Update mode chosen if you care about in-flight executions on deploy:
  - `CONTINUE` (default), `RESTART`, or `DROP`

```java
topology.newAgent("MyAgent")
    .setUpdateMode(UpdateMode.CONTINUE) // or RESTART or DROP
    .node("process", null, (AgentNode agentNode, String input) -> {
        agentNode.result("processed: " + input);
    });
```

---

## Common Beginner Mistakes (and template fixes)

### 1. Jumping straight to depots/PStates without asking "do I need streams?"
- **Symptom:** Over-engineering simple request/response flows with full event sourcing
- **Template fix:** Force Step 1 decision: "Is there continuous event processing?" If not, stay in AgentModule land.

### 2. Using aggregation for simple data processing
- **Symptom:** Using `aggStartNode`/`aggNode` to parallelize trivial loops
- **Problem:** Aggregation has HIGH coordination overhead; meant only for expensive operations (LLMs, heavy APIs)
- **Template fix:** Ask "Is each parallel task expensive (LLM/API)?" If no → use a simple loop in one node.

### 3. Over-using persistent state
- **Symptom:** Storing everything in stores/PStates instead of passing data between nodes
- **Problem:** Unnecessary complexity and I/O
- **Template fix:** Step 3 explicitly asks: "What must outlive a single invocation?" Everything else stays in-memory.

### 4. Not separating concerns in nodes
- **Symptom:** One giant node that does everything
- **Problem:** Hard to trace, debug, and evolve
- **Template fix:** Step 2: "One responsibility per node; define inputs/outputs per node."

### 5. Treating agent objects as regular objects (ignoring thread safety)
- **Symptom:** Sharing non-thread-safe clients without pooling or reset
- **Problem:** Race conditions, corrupted state
- **Template fix:** Ask: "Is this client thread-safe?" "Do I need to reset per invocation?" (use `resetForNewInvocation()` pattern from docs)

### 6. Forgetting to finalize agent topology in RamaModule
- **Symptom:** Agents not available at runtime when using RamaModule
- **Problem:** `AgentTopology.define()` not called
- **Template fix:** In "Rama + Agents together" step, checklist item: ✅ "Call `agentTopology.define()` at the end of `define()`."

### 7. Not ensuring every path ends with `result`
- **Symptom:** Some branches emit but never call result → hanging invocations
- **Template fix:** In graph design step, require a "path audit": draw all branches and mark where `result` is called.

---

## Reusable Phase 2 Worksheet Structure

```
1. Unit of Work Definition
   - Describe one user/system request
   - List inputs/outputs

2. Backend Choice
   - Do you have continuous event streams? (Y/N)
   - Do you have interactive workflows? (Y/N)
   - Decision: Pure Agent-o-rama / Pure Rama / Both

3. Agent Graph Sketch (if using agents)
   - List nodes, each with:
     - Name
     - Responsibility
     - Inputs
     - Outputs
     - Possible next nodes

4. State Design
   - For each piece of data:
     - Lifetime: per-invocation vs long-lived
     - Scope: local to agent vs shared system-wide
     - Choice: in-memory / Agent store / PState

5. External Integrations
   - List integrations
   - For each: agent object name, thread-safe? pooled? needs tools?

6. Parallelism
   - List expensive steps
   - Can they run in parallel?
   - If yes → consider aggregation; otherwise keep sequential

7. Implementation Checklist
   - All nodes defined?
   - All paths end in result?
   - Stores named with "$$"?
   - AgentTopology.define() called (if using RamaModule)?
   - Update mode chosen?
```

**Key insight from Chat-o-rama:** Keep beginners in the right order:
**requirements → agent graph → state → integrations → Rama primitives**
instead of starting from depots/PStates and trying to "fit" the business idea into them.
