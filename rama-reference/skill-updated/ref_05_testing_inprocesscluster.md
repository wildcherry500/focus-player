# Chat-o-rama Reference 05 — Testing with InProcessCluster (Java)
**Source:** chat.redplanetlabs.com  
**Date captured:** 2026-03-03  
**Language setting:** Java  
**AOR Version:** v0.7.0  

---

## Question Asked

> In Java, what is the complete correct pattern for unit testing a Rama module and an Agent-o-rama AgentModule using InProcessCluster? Please show: (1) the exact Maven dependency coordinates needed for InProcessCluster and JUnit, (2) a complete JUnit test class that launches a pure RamaModule, appends records to a depot, waits for stream topology processing to complete, and then queries a PState to assert the result, (3) a complete JUnit test class that launches an AgentModule, invokes an agent, and asserts on the result, (4) any important gotchas specific to running these tests in IntelliJ on macOS such as classpath issues, module naming, or LaunchConfig settings.

---

## Docs Referenced by Chat-o-rama

- Agent-o-rama Documentation: Agent Declaration / Agent Module, Rama Infrastructure / Cluster Manager, Client Interaction / Agent Manager
- aor-refdoc: Agent Module, Agent Manager, IPC (In-Process Cluster)
- agent-development-guide: Agent Design and Development
- Java Documentation: com.rpl.rama.test.InProcessCluster
- aor-wiki: Integrating with regular Rama modules / Adding agents to regular Rama modules / Basic pattern
- aor-wiki-parsed: Quickstart.md Chunk 0, Programming-agents.md Chunks 7 & 13
- rama-shared: About Red Planet Labs, Terminology / Module instance, Terminology / Cluster
- aor-java-examples: agent objects, async agent initiation, direct Rama module usage

---

## The Universal InProcessCluster Test Pattern

All three test types follow the same skeleton:

```
1. InProcessCluster.create()
2. launchModule(module, new LaunchConfig(tasks, threads))
3. Get the right clients (clusterDepot, clusterPState, AgentManager, AgentClient)
4. Drive the module (append to depot, invoke agent)
5. Wait for processing if needed (waitForMicrobatchProcessedCount)
6. Assert on results
7. ipc auto-closes via try-with-resources
```

---

## Pattern 1: Testing a Pure Rama Module

### Module Under Test

```java
package com.example.rama;

import com.rpl.rama.Depot;
import com.rpl.rama.Path;
import com.rpl.rama.PState;
import com.rpl.rama.RamaModule;
import com.rpl.rama.module.MicrobatchTopology;
import com.rpl.rama.module.Topologies;

public class SumModule implements RamaModule {

    @Override
    public String getModuleName() { return "SumModule"; }

    @Override
    public void define(Setup setup, Topologies topologies) {
        // 1) Declare depot at module level
        setup.declareDepot("*numbers-depot", Depot.random());

        // 2) Declare microbatch topology
        MicrobatchTopology t = topologies.microbatch("numbers-topology");

        // 3) Declare PState inside topology
        t.pstate("$$sum", PState.mapSchema(String.class, Long.class));

        // 4) Topology logic: accumulate sum
        t.source("*numbers-depot").out("*n")
            .localTransform("$$sum",
                Path.key("total").term(existing -> {
                    Long current = (existing == null) ? 0L : (Long) existing;
                    return current + (Long) t.var("*n");
                }));
    }
}
```

### JUnit Test

```java
package com.example.rama;

import com.rpl.rama.Depot;
import com.rpl.rama.Path;
import com.rpl.rama.PState;
import com.rpl.rama.test.InProcessCluster;
import com.rpl.rama.test.LaunchConfig;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class SumModuleTest {

    @Test
    public void testSumModule() throws Exception {
        try (InProcessCluster ipc = InProcessCluster.create()) {

            // 1) Launch module
            SumModule module = new SumModule();
            ipc.launchModule(module, new LaunchConfig(1, 1));
            String moduleName = module.getModuleName();

            // 2) Get depot and PState clients from IPC
            Depot numbersDepot = ipc.clusterDepot(moduleName, "*numbers-depot");
            PState sumPState   = ipc.clusterPState(moduleName, "$$sum");

            // 3) Append some numbers
            numbersDepot.append(10L);
            numbersDepot.append(5L);
            numbersDepot.append(7L);

            // 4) CRITICAL: wait for microbatch to process all 3 records
            ipc.waitForMicrobatchProcessedCount(moduleName, "numbers-topology", 3);

            // 5) Query PState and assert
            Long total = (Long) sumPState.selectOne(Path.key("total"));
            assertEquals(22L, total);
        }
    }
}
```

### Key Concepts

| Concept | Detail |
|---------|--------|
| `InProcessCluster.create()` | Runs a full Rama cluster in-process for tests |
| `launchModule(module, LaunchConfig)` | Starts your module with given tasks/threads |
| `clusterDepot(moduleName, "*name")` | Client for appending to a depot |
| `clusterPState(moduleName, "$$name")` | Client for querying a PState |
| `waitForMicrobatchProcessedCount(moduleName, topologyName, count)` | **CRITICAL** — blocks until microbatch has processed N records. Required for deterministic tests |
| Stream topologies | Use `waitForStreamProcessedCount` instead of microbatch variant |

---

## Pattern 2: Testing a Pure AgentModule

### AgentModule Under Test

```java
package com.example.agent;

import com.rpl.agentorama.AgentModule;
import com.rpl.agentorama.AgentNode;
import com.rpl.agentorama.AgentTopology;

public class EchoAgentModule extends AgentModule {

    @Override
    protected void defineAgents(AgentTopology topology) {
        topology
            .newAgent("EchoAgent")
            .node("process", null,
                (AgentNode agentNode, String input) -> {
                    agentNode.result("Echo: " + input);
                });
    }
}
```

### JUnit Test

```java
package com.example.agent;

import com.rpl.agentorama.AgentClient;
import com.rpl.agentorama.AgentManager;
import com.rpl.rama.test.InProcessCluster;
import com.rpl.rama.test.LaunchConfig;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class EchoAgentModuleTest {

    @Test
    public void testEchoAgent() throws Exception {
        try (InProcessCluster ipc = InProcessCluster.create()) {

            // 1) Launch the AgentModule
            EchoAgentModule module = new EchoAgentModule();
            ipc.launchModule(module, new LaunchConfig(1, 1));
            String moduleName = module.getModuleName();

            // 2) Create AgentManager bound to this IPC and module
            AgentManager manager = AgentManager.create(ipc, moduleName);

            // 3) Get AgentClient for our agent
            AgentClient echoAgent = manager.getAgentClient("EchoAgent");

            // 4) Invoke synchronously and assert
            Object result = echoAgent.invoke("hello");
            assertEquals("Echo: hello", result);
        }
    }
}
```

### Key Concepts

| Concept | Detail |
|---------|--------|
| `AgentModule` | Extend this for pure agent-only modules |
| `AgentManager.create(ipc, moduleName)` | Creates manager for agents in a module running on IPC |
| `manager.getAgentClient("AgentName")` | Gets per-agent client |
| `echoAgent.invoke(input)` | Synchronous — blocks until result is returned |
| `echoAgent.initiate(input)` + `echoAgent.result()` | Async variant — initiate returns immediately, result blocks |
| No `waitForMicrobatch...` needed | Agent invocations are synchronous by default |

---

## Pattern 3: Testing Integrated RamaModule + Agents

### Integrated Module

```java
package com.example.integrated;

import com.rpl.agentorama.AgentTopology;
import com.rpl.agentorama.AgentNode;
import com.rpl.rama.Depot;
import com.rpl.rama.RamaModule;
import com.rpl.rama.module.Topologies;

public class IntegratedModule implements RamaModule {

    @Override
    public String getModuleName() { return "IntegratedModule"; }

    @Override
    public void define(Setup setup, Topologies topologies) {
        // Regular Rama depot
        setup.declareDepot("*example-depot", Depot.random());

        // Create AgentTopology manually (not via AgentModule)
        AgentTopology agentTopology = AgentTopology.create(setup, topologies);

        // Define agents
        agentTopology
            .newAgent("FeedbackAgent")
            .node("process-feedback", null,
                (AgentNode agentNode, String feedbackText) -> {
                    agentNode.result("Processed: " + feedbackText);
                });

        // CRITICAL: must call define() last
        agentTopology.define();
    }
}
```

### JUnit Test

```java
package com.example.integrated;

import com.rpl.agentorama.AgentClient;
import com.rpl.agentorama.AgentManager;
import com.rpl.rama.Depot;
import com.rpl.rama.test.InProcessCluster;
import com.rpl.rama.test.LaunchConfig;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class IntegratedModuleTest {

    @Test
    public void testFeedbackAgent() throws Exception {
        try (InProcessCluster ipc = InProcessCluster.create()) {

            // 1) Launch integrated RamaModule
            IntegratedModule module = new IntegratedModule();
            ipc.launchModule(module, new LaunchConfig(1, 1));
            String moduleName = module.getModuleName();

            // 2) Use Rama depot client if needed
            Depot depot = ipc.clusterDepot(moduleName, "*example-depot");
            depot.append("some data");

            // 3) Use AgentManager for agents
            AgentManager manager = AgentManager.create(ipc, moduleName);
            AgentClient feedbackAgent = manager.getAgentClient("FeedbackAgent");

            Object result = feedbackAgent.invoke("Great product!");
            assertEquals("Processed: Great product!", result);
        }
    }
}
```

---

## Summary: Which Pattern to Use

| Your module type | Test pattern |
|-----------------|--------------|
| `implements RamaModule` (pure Rama) | Pattern 1 — clusterDepot + clusterPState + waitForMicrobatch |
| `extends AgentModule` (pure agents) | Pattern 2 — AgentManager + AgentClient + invoke |
| `implements RamaModule` + `AgentTopology.create(...)` | Pattern 3 — both Rama clients AND AgentManager/AgentClient |

---

## IntelliJ / macOS Gotchas

Based on Chat-o-rama docs, key things to watch:

1. **Module naming** — always implement `getModuleName()` explicitly and use it consistently: `module.getModuleName()` not hardcoded strings
2. **LaunchConfig(tasks, threads)** — for local testing, `(1, 1)` is simplest; use `(2, 2)` if testing partitioned behavior
3. **try-with-resources** — always wrap `InProcessCluster` in try-with-resources; it must be closed or port/thread leaks occur
4. **waitForMicrobatchProcessedCount** — easy to forget for microbatch topologies; tests will be flaky without it
5. **agentTopology.define()** — silent failure if omitted in integrated modules; agents simply won't be available
6. **Maven dependency** — use the `rama-test` artifact for `InProcessCluster`; it is a separate artifact from the main `rama` dependency
