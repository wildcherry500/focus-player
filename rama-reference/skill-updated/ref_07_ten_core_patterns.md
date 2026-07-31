# Reference 07 — Ten Core Agent Patterns (Implementation Cookbook)
**Purpose:** Working code and flow diagrams for every agent pattern in Agent-o-rama.  
**Complements:** ref_02 (design framework — helps you decide WHICH pattern), this file shows HOW to write each one.  
**Source:** Agent-o-rama Complete Learning Guide (verified against AOR examples).

---

## Overview: The Ten Patterns

| # | Pattern | Flow | When to use |
|---|---------|------|-------------|
| 1 | BasicAgent | A → done | Simple one-step transformation |
| 2 | ReActAgent | A → A → A → done | LLM reasoning loop with tools |
| 3 | MultiNodeAgent | A → B → C → done | Sequential processing pipeline |
| 4 | RouterAgent | A → (B or C) → D → done | Conditional branching |
| 5 | AggregationAgent | A → [B,B,B] → C → done | Parallel fan-out/fan-in |
| 6 | HumanInputAgent | A → wait → A → done | Human-in-the-loop approval |
| 7 | KeyValueStoreAgent | A → storage → done | Simple persistent memory |
| 8 | PStateStoreAgent | A → complex storage → done | Nested data structures |
| 9 | StreamingAgent | A → stream → stream → done | Real-time progress updates |
| 10 | AsyncAgent | fire multiple → collect | Client-side concurrency |

---

## Core Primitives (Used Across All Patterns)

| Method | What it does | Ends the agent? |
|--------|-------------|-----------------|
| `agentNode.emit("nodeName", data)` | Sends data to a node (can be self for looping) | No |
| `agentNode.result(data)` | Returns final output to caller | **Yes** |
| `agentNode.streamChunk(data)` | Sends incremental update to client | No |
| `agentNode.getHumanInput(prompt)` | Pauses execution, waits for human response | No |
| `agentNode.getAgentObject("name")` | Retrieves a declared agent object (LLM client, API key) | No |
| `agentNode.getStore("$$name")` | Retrieves a declared persistent store | No |
| `agentNode.getAgentClient("name")` | Gets a client to invoke another agent | No |

**Critical rule:** Every path through an agent graph MUST end with `agentNode.result(...)`. Missing this causes hanging invocations.

---

## Pattern 1: BasicAgent — Simple Transformation

The foundation. One node, one input, one result.

```java
topology.newAgent("BasicAgent")
    .node("process", null, (AgentNode agentNode, String userName) -> {
        String result = "Welcome to agent-o-rama, " + userName + "!";
        agentNode.result(result);
    });
```

**Flow:** `invoke("Alice")` → node "process" → `result("Welcome...")` → returned to caller.

**Second parameter `null`** means this node is a terminal — it doesn't emit to another node.

---

## Pattern 2: ReActAgent — Reasoning Loop with Tools

A node that emits back to itself, enabling iterative LLM reasoning.

```java
topology.newAgent("ReActAgent")
    .node("chat", "chat", (AgentNode agentNode, List<Object> inputMessages) -> {
        ChatModel openai = agentNode.getAgentObject("openai");
        // ... call LLM with inputMessages ...

        if (toolCalls != null && !toolCalls.isEmpty()) {
            // LLM wants to use a tool — LOOP
            AgentClient tools = agentNode.getAgentClient("tools");
            List<Object> toolResults = (List<Object>) tools.invoke(toolCalls);
            // Add tool results to messages and loop
            agentNode.emit("chat", nextMessages);
        } else {
            // LLM has final answer — DONE
            agentNode.result(aiMessage.text());
        }
    });
```

**Key insight:** The second parameter `"chat"` in `.node("chat", "chat", ...)` means the default emit target is itself. `emit("chat", ...)` sends the data back to the same node, creating the loop. `result(...)` breaks the loop.

**Requires agent objects** for the LLM client and a tools agent:

```java
topology.declareAgentObject("openai-api-key", System.getenv("OPENAI_API_KEY"));
topology.declareAgentObjectBuilder("openai", setup -> {
    String key = (String) setup.getAgentObject("openai-api-key");
    return OpenAiChatModel.builder().apiKey(key).modelName("gpt-4o-mini").build();
});
```

---

## Pattern 3: MultiNodeAgent — Sequential Pipeline

Data flows through a chain of nodes. Each node can pass MORE data than it received.

```java
topology.newAgent("MultiNodeAgent")
    .node("receive", "personalize", (AgentNode agentNode, String userName) -> {
        agentNode.emit("personalize", userName);
    })
    .node("personalize", "finalize", (AgentNode agentNode, String userName) -> {
        String greeting = "Hello, " + userName + "!";
        agentNode.emit("finalize", userName, greeting);  // Emits TWO values
    })
    .node("finalize", null, (AgentNode agentNode, String userName, String greeting) -> {
        String result = greeting + " Welcome to agent-o-rama!";
        agentNode.result(result);
    });
```

**Key insight:** `emit` can send multiple values. The receiving node's lambda must declare matching parameters. Data grows as it moves through the pipeline.

---

## Pattern 4: RouterAgent — Conditional Branching

A routing node inspects input and emits to different paths. Paths reconverge at a final node.

```java
topology.newAgent("RouterAgent")
    // Router: declares MULTIPLE emit targets
    .node("route", List.of("handle-urgent", "handle-default"),
        (AgentNode agentNode, String message) -> {
            if (message.startsWith("urgent:")) {
                agentNode.emit("handle-urgent", message);
            } else {
                agentNode.emit("handle-default", message);
            }
        })
    .node("handle-urgent", "finalize", (AgentNode agentNode, String message) -> {
        Map<String, Object> processed = new HashMap<>();
        processed.put("priority", "HIGH");
        processed.put("message", message.substring(7));
        agentNode.emit("finalize", processed);
    })
    .node("handle-default", "finalize", (AgentNode agentNode, String message) -> {
        Map<String, Object> processed = new HashMap<>();
        processed.put("priority", "NORMAL");
        processed.put("message", message);
        agentNode.emit("finalize", processed);
    })
    // Both paths converge here
    .node("finalize", null, (AgentNode agentNode, Map<String, Object> processed) -> {
        agentNode.result(String.format("[%s] %s",
            processed.get("priority"), processed.get("message")));
    });
```

**Key insight:** When a node has multiple possible emit targets, pass them as `List.of("targetA", "targetB")` in the second parameter. The node's logic decides which target to emit to.

---

## Pattern 5: AggregationAgent — Parallel Fan-Out/Fan-In

For parallelizing expensive work (multiple LLM calls, heavy API calls). Uses three special node types.

```java
topology.newAgent("AggregationAgent")
    // Fan-out: emits MULTIPLE times, each triggers parallel processing
    .aggStartNode("distribute-work", "process-chunk",
        (AgentNode agentNode, Map<String, Object> request) -> {
            List<List<Integer>> chunks = splitIntoChunks(data, chunkSize);
            for (List<Integer> chunk : chunks) {
                agentNode.emit("process-chunk", chunk);
            }
            return null;  // aggStartNode returns a value passed to aggNode
        })
    // Each emission runs in parallel
    .node("process-chunk", "collect-results",
        (AgentNode agentNode, List<Integer> chunk) -> {
            Map<String, Object> result = processChunk(chunk);
            agentNode.emit("collect-results", result);
        })
    // Fan-in: collects all parallel results
    .aggNode("collect-results", null, BuiltIn.LIST_AGG,
        (AgentNode agentNode, List<Map<String, Object>> aggregatedResults,
         Object startNodeResult) -> {
            Map<String, Object> finalResult = combineResults(aggregatedResults);
            agentNode.result(finalResult);
        });
```

| Node type | Method | Purpose |
|-----------|--------|---------|
| `aggStartNode` | `.aggStartNode(name, target, fn)` | Starts aggregation, emits multiple times to fan out |
| Regular `node` | `.node(name, target, fn)` | Runs in parallel for each fan-out emission |
| `aggNode` | `.aggNode(name, target, aggregator, fn)` | Collects all results using an aggregator |

**WARNING (from ref_02):** Aggregation has HIGH coordination overhead. Only use for expensive parallel operations (LLM calls, heavy APIs). For simple data loops, use a regular loop inside one node.

---

## Pattern 6: HumanInputAgent — Human-in-the-Loop

Pauses agent execution and waits for a human response.

```java
topology.newAgent("HumanInputAgent")
    .node("chat", null, (AgentNode agentNode, String userMessage) -> {
        ChatModel openai = agentNode.getAgentObject("openai");
        String response = openai.chat(userMessage);

        // PAUSES HERE — waits for human input
        String input = agentNode.getHumanInput(
            "AI Response: " + response + "\n\nWas this helpful? (y/n): ");

        boolean helpful = input.equals("y");
        Map<String, Object> result = new HashMap<>();
        result.put("response", response);
        result.put("helpful", helpful);
        agentNode.result(result);
    });
```

**Client-side handling** (programmatic, not interactive terminal):

```java
AgentInvoke invoke = agent.initiate(input);            // Start without blocking
Object step = agent.nextStep(invoke);                  // Get next step
if (step instanceof HumanInputRequest) {
    HumanInputRequest req = (HumanInputRequest) step;
    agent.provideHumanInput(req, "y");                 // Supply human answer
}
// Continue checking nextStep until complete
```

| Client method | Purpose |
|--------------|---------|
| `agent.initiate(input)` | Starts agent non-blocking, returns handle |
| `agent.nextStep(invoke)` | Gets next step (may be HumanInputRequest) |
| `agent.provideHumanInput(request, response)` | Supplies the human's answer |
| `agent.isAgentInvokeComplete(invoke)` | Checks if agent is done |

---

## Pattern 7: KeyValueStoreAgent — Simple Persistent Memory

Data that survives across invocations. Declare once, read/write in any node.

```java
// In defineAgents():
topology.declareKeyValueStore("$$counters", String.class, Long.class);

topology.newAgent("KeyValueStoreAgent")
    .node("manage-counter", null,
        (AgentNode agentNode, Map<String, Object> request) -> {
            KeyValueStore<String, Long> store = agentNode.getStore("$$counters");
            String name = (String) request.get("counterName");
            String op = (String) request.get("operation");

            switch (op) {
                case "GET":
                    Long value = store.get(name);
                    agentNode.result(value);
                    break;
                case "INCREMENT":
                    Long current = store.get(name);
                    if (current == null) current = 0L;
                    store.put(name, current + 1);
                    agentNode.result(current + 1);
                    break;
            }
        });
```

**Persistence is automatic:** `INCREMENT "page-views"` three times → `GET "page-views"` returns 3, even across separate program runs.

For the full KeyValueStore API, see ref_01.

---

## Pattern 8: PStateStoreAgent — Nested Data Structures

For complex hierarchical data with path-based queries and updates. More powerful than KeyValueStore.

### Declaring a nested schema

```java
topology.declarePStateStore(
    "$$organizations",
    PState.mapSchema(
        String.class,  // company-id
        PState.fixedKeysSchema(
            "name", String.class,
            "departments", PState.mapSchema(
                String.class,  // dept-id
                PState.fixedKeysSchema(
                    "name", String.class,
                    "employees", PState.mapSchema(
                        String.class,  // emp-id
                        PState.fixedKeysSchema(
                            "name", String.class,
                            "salary", Long.class
                        )))))));
```

### Path-based operations

```java
PStateStore orgStore = agentNode.getStore("$$organizations");

// Read a specific value deep in the structure
String companyName = (String) orgStore.selectOne(
    companyId, Path.key(companyId, "name"));

// Update a specific nested field
orgStore.transform(companyId,
    Path.key(companyId, "departments", deptId, "name").termVal(deptName));

// Query across the structure — get ALL employee names in a company
List<String> names = orgStore.select(companyId,
    Path.key(companyId, "departments").mapVals()
        .key("employees").mapVals().key("name"));
```

### KeyValueStore vs PStateStore

| | KeyValueStore | PStateStore |
|---|---|---|
| Structure | Simple key → value | Complex nested maps |
| Read | `store.get(key)` | `store.selectOne(partition, Path...)` |
| Write | `store.put(key, value)` | `store.transform(partition, Path...termVal(value))` |
| Best for | Counters, flags, simple state | Hierarchical domain models |

**Serialization rule:** Use `ArrayList` and `HashMap`, not `List.of()` or `Map.of()`. Rama's serializer requires mutable types.

---

## Pattern 9: StreamingAgent — Real-Time Updates

Send incremental progress to the client during long-running operations.

### Server side

```java
topology.newAgent("StreamingAgent")
    .node("process-data", null, (AgentNode agentNode, Map<String, Object> request) -> {
        int totalChunks = calculateChunks(request);

        for (int i = 0; i < totalChunks; i++) {
            // ... process chunk ...

            Map<String, Object> progress = new HashMap<>();
            progress.put("chunkNumber", i);
            progress.put("progress", (double)(i + 1) / totalChunks);
            agentNode.streamChunk(progress);  // Client receives this immediately
        }

        agentNode.result(finalSummary);  // Final result ends the agent
    });
```

### Client side

```java
AgentInvoke invoke = agent.initiate(request);  // Non-blocking start

// Subscribe to streaming chunks
agent.stream(invoke, "process-data",
    (allChunks, newChunks, reset, complete) -> {
        for (Object chunk : newChunks) {
            Map<String, Object> data = (Map<String, Object>) chunk;
            System.out.println("Progress: " + data.get("progress"));
        }
    });

// Wait for final result
Map<String, Object> result = agent.result(invoke);
```

| Method | Ends agent? | Use for |
|--------|------------|---------|
| `agentNode.streamChunk(data)` | No | Progress updates, partial results |
| `agentNode.result(data)` | Yes | Final output |

---

## Pattern 10: AsyncAgent — Client-Side Concurrency

Fire multiple agent invocations simultaneously from the client. Each runs independently.

```java
// NON-BLOCKING: fire off multiple invocations immediately
AgentInvoke task1 = agent.initiate("Data Processing");
AgentInvoke task2 = agent.initiate("Report Generation");
AgentInvoke task3 = agent.initiate("Email Sending");

// All three run concurrently

// BLOCKING: collect results (can request in any order)
String result3 = (String) agent.result(task3);  // blocks until task3 done
String result2 = (String) agent.result(task2);
String result1 = (String) agent.result(task1);
```

| Method | Behavior |
|--------|----------|
| `agent.invoke(input)` | Blocking — waits for result, returns it |
| `agent.initiate(input)` | Non-blocking — returns `AgentInvoke` handle immediately |
| `agent.result(invoke)` | Blocking — waits for that specific invoke to complete |

### AsyncAgent vs AggregationAgent

| | AsyncAgent | AggregationAgent |
|---|---|---|
| Where concurrency happens | Client fires multiple agents externally | Agent internally fans out work |
| Who manages parallelism | Your code | Agent-o-rama framework |
| Use when | Running independent agents simultaneously | Splitting one task into parallel sub-tasks |

---

## Combining Patterns

Real applications combine patterns. A common architecture:

```
User Request
     ↓
RouterAgent (decide type)
     ↓
┌────┴────┐
↓         ↓
Simple    Complex
↓         ↓
BasicAgent   ReActAgent (with tools)
↓         ↓
└────┬────┘
     ↓
StreamingAgent (show progress)
     ↓
HumanInputAgent (verify)
     ↓
PStateStoreAgent (save)
     ↓
Return Result
```

The design framework in ref_02 helps you decide which patterns to combine. This file shows how to implement each one.
