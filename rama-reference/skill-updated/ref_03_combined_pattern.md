# Chat-o-rama Reference 03 — Combined RamaModule + AgentTopology Pattern (Java)
**Source:** chat.redplanetlabs.com  
**Date captured:** 2026-03-03  
**Language setting:** Java  
**AOR Version:** v0.7.0  

---

## Question Asked

> In Java, what is the complete and correct pattern for combining a regular Rama module (RamaModule with depots, stream topologies, and PStates) with Agent-o-rama agents in the same module? Specifically: (1) what is the exact class and interface structure - does the class extend AgentModule or implement RamaModule? (2) what is the exact order of operations inside the define() or defineAgents() method - when do you declare depots, when do you create AgentTopology, when do you call agentTopology.define()? (3) how does an agent node read from a PState that was built by a stream topology in the same module? (4) how does an agent node append to a depot in the same module? Please show a complete minimal Java example demonstrating all four of these.

---

## Answer

### (1) Class / Interface Structure

When combining Rama primitives with Agent-o-rama agents, your module class **implements `RamaModule`** (NOT extends `AgentModule`).

```
public class MyModule implements RamaModule { ... }
```

`AgentModule` is a convenience class for pure agent-only modules. When you need depots, topologies, and PStates alongside agents, you go back to `RamaModule` and create an `AgentTopology` explicitly inside `define()`.

---

### (2) Exact Order of Operations Inside `define()`

```
define(Setup setup, Topologies topologies) {
  1. Declare depots         (setup.declareDepot(...))
  2. Define stream/microbatch topologies + PStates
  3. Create AgentTopology   (AgentTopology.create(setup, topologies))
  4. Declare agent objects  (agentTopology.declareAgentObject(...))
  5. Declare stores         (agentTopology.declareKeyValueStore(...))
  6. Define agents + nodes  (agentTopology.newAgent(...).node(...))
  7. CALL agentTopology.define()   ← CRITICAL, must be last
}
```

**Key rule:** `agentTopology.define()` MUST be the last call. If you forget it, agents will not be available at runtime and there will be no error — it silently does nothing.

---

### (3) How an Agent Node Reads from a PState

Use `agentNode.getColocatedPState(String pstateName)` to get a handle to a PState declared in the same module's topology. Then use standard PState query methods.

```java
// Inside a node:
PState customerSnapshot = agentNode.getColocatedPState("$$customer-snapshot");
Map<String, Object> snapshot = (Map<String, Object>) customerSnapshot.selectOne(
    Path.key(customerId)
);
```

---

### (4) How an Agent Node Appends to a Depot

Use `agentNode.getColocatedDepot(String depotName)` to get a depot client, then call `.append(record)`.

```java
// Inside a node:
Depot eventsDepot = agentNode.getColocatedDepot("*crm-events");
eventsDepot.append(newEvent);
```

---

### Complete Minimal Java Example

```java
import com.rpl.rama.*;
import com.rpl.rama.module.*;
import com.rpl.rama.ops.*;
import com.rpl.agentorama.*;
import com.rpl.agentorama.store.*;
import java.util.*;

public class CombinedModule implements RamaModule {

    @Override
    public String getModuleName() { return "CombinedModule"; }

    @Override
    public void define(Setup setup, Topologies topologies) {

        // ── Step 1: Declare depots ──────────────────────────────────────
        setup.declareDepot("*events", Depot.hashBy(Extractors.field("entityId")));

        // ── Step 2: Stream topology + PState ───────────────────────────
        StreamTopology stream = topologies.stream("event-projections");

        // PState: entityId → latest snapshot map
        stream.pstate("$$entity-snapshot", PState.mapSchema(
            String.class,    // key: entityId
            Object.class     // value: snapshot map
        ));

        stream.source("*events").out("*event")
              .hashPartition("*event", Extractors.field("entityId"))
              .localTransform("$$entity-snapshot",
                  Path.key(Extractors.field("entityId"))
                      .termVal(Extractors.field("payload")));

        // ── Step 3: Create AgentTopology ───────────────────────────────
        AgentTopology agentTopology = AgentTopology.create(setup, topologies);

        // ── Step 4: Declare agent objects ──────────────────────────────
        agentTopology.declareAgentObject(
            "openai-api-key",
            System.getenv("OPENAI_API_KEY")
        );

        // ── Step 5: Declare stores ─────────────────────────────────────
        agentTopology.declareKeyValueStore(
            "$$agent-state", String.class, Map.class
        );

        // ── Step 6: Define agents ──────────────────────────────────────
        agentTopology
            .newAgent("CombinedAgent")

            // Node 1: Load snapshot from PState + agent store
            .node("load-context", "process",
                (AgentNode agentNode, Map<String, Object> request) -> {
                    String entityId = (String) request.get("entityId");

                    // (3) Read from PState built by stream topology
                    PState snapshotPState =
                        agentNode.getColocatedPState("$$entity-snapshot");
                    Map<String, Object> snapshot =
                        (Map<String, Object>) snapshotPState.selectOne(
                            Path.key(entityId));

                    // Read from agent store
                    @SuppressWarnings("unchecked")
                    KeyValueStore<String, Map<String, Object>> store =
                        agentNode.getStore("$$agent-state");
                    Map<String, Object> agentState = store.get(entityId);

                    // Pass combined context forward
                    Map<String, Object> context = new HashMap<>();
                    context.put("entityId", entityId);
                    context.put("snapshot", snapshot);
                    context.put("agentState", agentState);
                    context.put("request", request);
                    agentNode.emit("process", context);
                })

            // Node 2: Do work, emit new event back to depot
            .node("process", "finalize",
                (AgentNode agentNode, Map<String, Object> context) -> {
                    String entityId = (String) context.get("entityId");
                    Map<String, Object> snapshot =
                        (Map<String, Object>) context.get("snapshot");

                    // Build a new event
                    Map<String, Object> newEvent = new HashMap<>();
                    newEvent.put("entityId", entityId);
                    newEvent.put("eventType", "AgentProcessed");
                    newEvent.put("payload", Map.of("processedAt",
                        System.currentTimeMillis()));

                    // (4) Append to depot in same module
                    Depot eventsDepot =
                        agentNode.getColocatedDepot("*events");
                    eventsDepot.append(newEvent);

                    // Update agent store
                    @SuppressWarnings("unchecked")
                    KeyValueStore<String, Map<String, Object>> store =
                        agentNode.getStore("$$agent-state");
                    Map<String, Object> agentState = new HashMap<>();
                    agentState.put("lastProcessed",
                        System.currentTimeMillis());
                    store.put(entityId, agentState);

                    agentNode.emit("finalize", Map.of(
                        "entityId", entityId,
                        "newEvent", newEvent
                    ));
                })

            // Node 3: Terminal - return result
            .node("finalize", null,
                (AgentNode agentNode, Map<String, Object> result) -> {
                    agentNode.result(result);
                });

        // ── Step 7: MUST call define() last ───────────────────────────
        agentTopology.define();
    }
}
```

---

## Key Rules Summary

| Concern | Rule |
|---------|------|
| Class structure | `implements RamaModule` (not extends AgentModule) when combining |
| Order | depots → topologies/PStates → AgentTopology.create → objects → stores → agents → `agentTopology.define()` |
| PState access in node | `agentNode.getColocatedPState("$$name")` then `.selectOne(Path.key(...))` |
| Depot access in node | `agentNode.getColocatedDepot("*name")` then `.append(record)` |
| Critical gotcha | `agentTopology.define()` MUST be last — silent failure if omitted |
| Depot naming | Must start with `*` |
| PState naming | Must start with `$$` |
| Store naming | Must start with `$$` |
