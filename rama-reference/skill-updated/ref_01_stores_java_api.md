# Chat-o-rama Reference 01 — Persistent Stores Java API
**Source:** chat.redplanetlabs.com  
**Date captured:** 2026-03-03  
**Language setting:** Java  
**AOR Version:** v0.7.0  

---

## Question Asked

> In Agent-o-rama's Java API (v0.7.0), when a node needs to read from or write to persistent state shared across multiple agent invocations for the same user - such as conversation history and detected intent - what is the exact Java API pattern? Specifically: what store type should be declared (key-value, document, or something else), what is the Java method to declare it in the module, and what are the exact Java methods inside a node function to read and write fields of that store? Please show a complete minimal Java example of declaring the store and reading/writing it inside a node.

---

## Docs Referenced by Chat-o-rama

- aor-wiki-parsed: Programming-agents.md Chunk 9
- aor-refdoc-sections: Store / Key Java API | Agent Node / State Access / Persistent Stores
- aor-userdoc: Storage and Objects / Three Store Types
- rama-shared: Terminology / Metastore
- aor-refdoc: PState Store
- aor-java-examples: Java example demonstrating key-value store operations for persistent agent state
- aor-wiki-chunked: Programming-agents.md Chunk 9
- aor-wiki: Programming agents / Stores
- agent-development-guide: Agent Design and Development

---

## Answer

For persistent per-user state across multiple invocations (e.g. conversation history, detected intent) in Agent-o-rama Java v0.7.0, the recommended simple pattern is:

- Use a **Key-Value Store** when you just need a single value per key (e.g. "user-id → JSON blob of conversation state").
- Use a **Document Store** when you want multiple named fields per key (e.g. "user-id → {history, lastIntent, metadata…}") and want to update fields independently.

Below is the exact Java API pattern for the simplest case (key-value store).

---

### 1. Store type and declaration in the module

**Store type:** `com.rpl.agentorama.store.KeyValueStore<K, V>`

For per-user state, a common choice is:
- K = String (user id)
- V = Map<String, Object> (conversation state fields: history, intent, etc.)

**Declare the store in `defineAgents`:**

```java
@Override
protected void defineAgents(AgentTopology topology) {
    // Declare a key-value store for per-user conversation state
    topology.declareKeyValueStore("$$user-state", String.class, Map.class);
    // ... define agents and nodes ...
}
```

**Key points:**
- Store names **must start with `$$`**
- `declareKeyValueStore` is called on `AgentTopology`
- This creates a distributed, durable key-value store

---

### 2. Accessing the store inside a node

Inside a node function, you:
1. Get the store via `agentNode.getStore("$$user-state")`
2. Use `get`, `put`, or `update` on the store

**Relevant methods:**
- `AgentNode.getStore(String name)`
- `KeyValueStore.get(K key)`
- `KeyValueStore.put(K key, V value)`
- `KeyValueStore.update(K key, Function<V, V> updater)` — atomic read-modify-write

---

### 3. Complete minimal Java example

```java
package com.example.agent;

import com.rpl.agentorama.AgentClient;
import com.rpl.agentorama.AgentManager;
import com.rpl.agentorama.AgentModule;
import com.rpl.agentorama.AgentNode;
import com.rpl.agentorama.AgentTopology;
import com.rpl.agentorama.store.KeyValueStore;
import com.rpl.rama.test.InProcessCluster;
import com.rpl.rama.test.LaunchConfig;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class ConversationStateAgent {

    public static Map<String, Object> createRequest(
            String userId, String userMessage, String detectedIntent) {
        Map<String, Object> req = new HashMap<>();
        req.put("userId", userId);
        req.put("userMessage", userMessage);
        req.put("detectedIntent", detectedIntent);
        return req;
    }

    public static class ConversationModule extends AgentModule {
        @Override
        protected void defineAgents(AgentTopology topology) {
            // 1. Declare a key-value store for per-user state:
            //    key = userId (String)
            //    value = Map<String, Object> representing the user's conversation state
            topology.declareKeyValueStore("$$user-state", String.class, Map.class);

            topology
                .newAgent("ConversationAgent")
                .node(
                    "update-state",
                    null,
                    (AgentNode agentNode, Map<String, Object> request) -> {
                        // 2. Get the store inside the node
                        @SuppressWarnings("unchecked")
                        KeyValueStore<String, Map<String, Object>> userStateStore =
                            agentNode.getStore("$$user-state");

                        String userId = (String) request.get("userId");
                        String userMessage = (String) request.get("userMessage");
                        String detectedIntent = (String) request.get("detectedIntent");

                        // 3. Read existing state for this user
                        Map<String, Object> state = userStateStore.get(userId);
                        if (state == null) {
                            state = new HashMap<>();
                            state.put("history", new ArrayList<Map<String, String>>());
                            state.put("lastIntent", null);
                        }

                        // 4. Update conversation history
                        @SuppressWarnings("unchecked")
                        List<Map<String, String>> history =
                            (List<Map<String, String>>) state.get("history");
                        if (history == null) {
                            history = new ArrayList<>();
                            state.put("history", history);
                        }
                        Map<String, String> messageEntry = new HashMap<>();
                        messageEntry.put("role", "user");
                        messageEntry.put("content", userMessage);
                        history.add(messageEntry);

                        // 5. Update detected intent
                        state.put("lastIntent", detectedIntent);

                        // 6. Write updated state back to the store
                        userStateStore.put(userId, state);

                        // 7. Return the updated state as the result
                        Map<String, Object> result = new HashMap<>();
                        result.put("userId", userId);
                        result.put("state", state);
                        agentNode.result(result);
                    });
        }
    }

    public static void main(String[] args) throws Exception {
        try (InProcessCluster ipc = InProcessCluster.create()) {
            ConversationModule module = new ConversationModule();
            ipc.launchModule(module, new LaunchConfig(1, 1));
            String moduleName = module.getModuleName();
            AgentManager manager = AgentManager.create(ipc, moduleName);
            AgentClient agent = manager.getAgentClient("ConversationAgent");

            // First invocation for user "u1"
            Map<String, Object> r1 = (Map<String, Object>)
                agent.invoke(createRequest("u1", "Hi there", "greeting"));
            System.out.println("First result: " + r1);

            // Second invocation for same user "u1" - state is persisted
            Map<String, Object> r2 = (Map<String, Object>)
                agent.invoke(createRequest("u1", "What's the weather?", "ask_weather"));
            System.out.println("Second result: " + r2);
        }
    }
}
```

---

### 4. When to consider Document or PState stores

**Document Store:**
- "Values are maps with their own schema for each field. You can perform operations on individual nested values without reading or writing the entire document."
- Use `AgentTopology.declareDocumentStore(...)` and `AgentNode.getStore(...)` similarly.
- Good fit if you want strongly typed fields like `"history", List.class, "lastIntent", String.class`, etc.

**PState Store:**
- More advanced, schema-driven, path-based access with `select`, `selectOne`, `transform`.
- Use `declarePStateStore` and `PStateStore` if you need complex queries and transactional updates across nested structures.

**For conversation history + detected intent per user:** the key-value store pattern above is the simplest and fully supported in the Java API as of v0.7.0.

---

## Key Rules Summary

| Rule | Detail |
|------|--------|
| Store names | Must start with `$$` |
| Declaration location | `topology.declareKeyValueStore(...)` in `defineAgents()` |
| Access in node | `agentNode.getStore("$$name")` |
| Read | `store.get(key)` |
| Write | `store.put(key, value)` |
| Atomic update | `store.update(key, fn)` |
| Document store | `topology.declareDocumentStore(...)` — named fields per key |
| PState store | `topology.declarePStateStore(...)` — complex schema, path queries |
