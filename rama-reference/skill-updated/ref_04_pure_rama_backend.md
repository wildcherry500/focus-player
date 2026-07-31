# Chat-o-rama Reference 04 — Pure Rama Backend Patterns (Java)
**Source:** chat.redplanetlabs.com  
**Date captured:** 2026-03-03  
**Language setting:** Java  

---

## Question Asked

> In Java, show the complete correct pattern for a pure Rama backend module that: (1) declares a depot partitioned by a key field, (2) defines a stream topology that sources from that depot, transforms the data, and updates two PStates - one simple key-to-value map and one key-to-list-of-events, (3) how you correctly use localTransform with Path to append to a list in a PState, and (4) how an external Java client queries a PState by key using the cluster client.

---

## Docs Referenced by Chat-o-rama

- rama-refdoc: Depot, AggregatorTopology, ISR, Module, Point Query, Tick Depot, Global Depot, Foreign Context, Task Global, Metastore, Cluster-manager, Module Dependency, Replog, Task Instance, External Depot, Cluster, Partitioner, Java Documentation (Navigator.transform, Depot.Declaration, RamaClusterManager)
- rama-examples: Basic PState example, Basic microbatch topology example
- rama-shared: Paths / Substructure navigators / Range queries, Operating Rama clusters / Accessing depots PStates and query topologies from remote Java clients
- aor-java-examples: Java example demonstrating PState store operations for complex path-based data structures

---

## Complete Module Java Class

```java
package com.example.rama;

import com.rpl.rama.Agg;
import com.rpl.rama.Depot;
import com.rpl.rama.Path;
import com.rpl.rama.PState;
import com.rpl.rama.RamaModule;
import com.rpl.rama.StreamTopology;
import com.rpl.rama.Topologies;
import com.rpl.rama.helpers.Ops;
import com.rpl.rama.test.InProcessCluster;
import com.rpl.rama.test.LaunchConfig;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Pure backend Rama module demonstrating:
 * 1. Depot partitioned by key field (hash partitioning)
 * 2. Stream topology sourcing from that depot
 * 3. Two PStates:
 *    - $$latestValue:   key -> latest value
 *    - $$eventHistory:  key -> list of events
 * 4. Correct use of localTransform with Path to append to a list
 *
 * Record format in depot: [key<String>, value<Object>]
 */
public class EventHistoryModule implements RamaModule {

    @Override
    public void define(Setup setup, Topologies topologies) {

        // (1) Declare depot partitioned by key field (first element of list)
        // Depot.hashBy(Ops.FIRST) = hash-partition by the first element
        // of the appended list (our "key").
        setup.declareDepot("*eventsDepot", Depot.hashBy(Ops.FIRST));

        // (2) Define stream topology that sources from the depot
        StreamTopology s = topologies.stream("events-stream");

        // (2a) Declare PStates inside the topology

        // Simple key -> latest value map
        // Schema: { key<String> : value<Object> }
        s.pstate("$$latestValue", PState.mapSchema(String.class, Object.class));

        // Key -> list-of-events
        // Schema: { key<String> : [event<Object>] }
        s.pstate("$$eventHistory", PState.mapSchema(String.class, List.class));

        // (2b) Stream topology: source from depot, transform, update PStates
        // Depot record is a List: [key, value]
        s.source("*eventsDepot").out("*tuple")
            // Expand list into vars *key and *value
            .each(Ops.EXPAND, "*tuple").out("*key", "*value")

            // Update $$latestValue with the latest value for the key
            .localTransform(
                "$$latestValue",
                // Path: navigate to map entry for *key and set it to *value
                Path.key("*key").termVal("*value"))

            // (3) Use localTransform + Path to append to list in $$eventHistory
            // We want: history[key] = (existingList or []) + [value]
            .localTransform(
                "$$eventHistory",
                Path
                    // Navigate to the list at key "*key"
                    .key("*key")
                    // Transform that list by appending the new value
                    .term(existing -> {
                        List<Object> list;
                        if (existing == null) {
                            list = new ArrayList<>();
                        } else {
                            list = new ArrayList<>((List<Object>) existing);
                        }
                        list.add(existing); // or wrap in richer object
                        return list;
                    })
            );
    }

    // In-process demo
    public static void main(String[] args) throws Exception {
        try (InProcessCluster cluster = InProcessCluster.create()) {
            EventHistoryModule module = new EventHistoryModule();
            cluster.launchModule(module, new LaunchConfig(2, 2));
            String moduleName = module.getClass().getName();

            // Depot client for appending events
            Depot eventsDepot = cluster.clusterDepot(moduleName, "*eventsDepot");

            // PState clients for querying
            PState latestValue  = cluster.clusterPState(moduleName, "$$latestValue");
            PState eventHistory = cluster.clusterPState(moduleName, "$$eventHistory");

            // Append some events: [key, value]
            eventsDepot.append(Arrays.asList("user-1", "login"));
            eventsDepot.append(Arrays.asList("user-1", "view-page"));
            eventsDepot.append(Arrays.asList("user-2", "signup"));
            eventsDepot.append(Arrays.asList("user-1", "logout"));

            // Query latest value for user-1
            Object latest = latestValue.selectOne(Path.key("user-1"));
            System.out.println("Latest for user-1: " + latest);

            // Query full event history list for user-1
            Object history = eventHistory.selectOne(Path.key("user-1"));
            System.out.println("History for user-1: " + history);
        }
    }
}
```

---

## External Java Client (Remote Query)

```java
import com.rpl.rama.Path;
import com.rpl.rama.PState;
import com.rpl.rama.RamaClusterManager;

public class EventHistoryClient {
    public static void main(String[] args) throws Exception {
        // Connect to the Rama cluster (uses rama.yaml on classpath)
        try (RamaClusterManager manager = RamaClusterManager.open()) {
            String moduleName = "com.example.rama.EventHistoryModule";

            // (4) Get PState client for $$eventHistory
            PState eventHistory =
                manager.clusterPState(moduleName, "$$eventHistory");

            String key = "user-1";

            // Point query: fetch list-of-events for this key
            Object history = eventHistory.selectOne(Path.key(key));
            System.out.println("History for " + key + ": " + history);

            // Similarly, query $$latestValue
            PState latestValue =
                manager.clusterPState(moduleName, "$$latestValue");
            Object latest = latestValue.selectOne(Path.key(key));
            System.out.println("Latest for " + key + ": " + latest);
        }
    }
}
```

---

## Key Concepts Explained

### Depot declaration
```java
setup.declareDepot("*eventsDepot", Depot.hashBy(Ops.FIRST));
```
- `Depot.hashBy(Ops.FIRST)` — partition by the first element of each appended list
- Ensures all events for the same key land on the same task/partition

### PState declaration (inside topology)
```java
s.pstate("$$latestValue",  PState.mapSchema(String.class, Object.class));
s.pstate("$$eventHistory", PState.mapSchema(String.class, List.class));
```
- Must be declared **inside** the topology (`s.pstate(...)` not `setup.pstate(...)`)
- Names must start with `$$`

### localTransform — simple overwrite
```java
.localTransform("$$latestValue", Path.key("*key").termVal("*value"))
```
- `Path.key("*key")` — navigate to this map entry
- `.termVal("*value")` — set it to the value of `*value`

### localTransform — append to list
```java
.localTransform("$$eventHistory",
    Path.key("*key").term(existing -> {
        List<Object> list = existing == null
            ? new ArrayList<>()
            : new ArrayList<>((List<Object>) existing);
        list.add(newEvent);
        return list;
    }))
```
- `Path.key("*key").term(fn)` — navigate to entry and transform with lambda
- Handle `null` (key not yet seen) explicitly

### External PState query
```java
PState ps = manager.clusterPState(moduleName, "$$name");
Object result = ps.selectOne(Path.key(key));
```
- `selectOne` = **point query** — targets exactly one partition, low-latency
- `RamaClusterManager.open()` reads connection from `rama.yaml` on classpath

---

## Naming Convention Summary

| Thing | Prefix | Example |
|-------|--------|---------|
| Depot | `*` | `*eventsDepot` |
| PState | `$$` | `$$latestValue` |
| Agent Store | `$$` | `$$user-state` |
| Topology var | `*` | `*key`, `*value` |
