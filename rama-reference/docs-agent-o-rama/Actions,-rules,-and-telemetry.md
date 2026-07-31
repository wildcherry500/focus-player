<!-- Source: agent-o-rama GitHub wiki (Actions,-rules,-and-telemetry) | Fetched: 2026-07-30 -->

# Actions, Rules, and Telemetry

Agent-o-rama's actions and rules system enables you to set up automatic actions that run on production agent or node executions. You define filtering criteria to select which runs should trigger actions, and the system automatically executes those actions asynchronously.

This system is useful for everything from running evaluators on production runs to triggering webhooks to running whatever custom logic you need. You might use actions to continuously evaluate agent quality, automatically add interesting examples to training datasets, or send alerts when errors occur.

## Table of Contents
- [Rules and Actions](#rules-and-actions)
- [Built-in Actions](#built-in-actions)
- [Custom Actions](#custom-actions)
- [Action Logs](#action-logs)
- [Time-Series Telemetry](#time-series-telemetry)

## Rules and Actions

Rules specify when to run an action. When an agent execution completes, the system evaluates all active rules against that execution. If the filter matches the run, the action executes with access to the run's inputs, outputs, metadata, timing information, and any feedback from other actions. The system maintains per-task cursors that track processing progress, ensuring actions only run once per matching execution even across cluster restarts or module updates.

Rules can be configured to run an action against either the entire agent execution or individual node executions within an agent, giving you fine-grained control over what gets processed. When targeting a specific node, the action receives data from just that node's execution, including its inputs, outputs, and any nested operations like model calls or database queries.

### Creating a rule

Rules are created on the "Rules/Actions" page for an agent. The form to create a rule looks like this:

![Create rule](images/create-rule.png)

The initial fields in the form are:

1. **Rule name**: this names the rule, and if the rule performs online evaluation can also be referenced by other rules as a dependency
2. **Scope**: Specify whether to run on the agent as a whole or on particular node runs of the agent
3. **Status filter**: Whether to execute on successful runs, failed runs, or all runs
4. **Sampling rate**: Number between 0 and 1.0 specifying on what percentage of runs to execute
5. **Start time**: How far back to start applying the rule. This is used to backfill application of the rule, especially for online evaluation where you may want to know about production performance in the past.
6. **Action**: Select which action to run when the rule matches. The list of actions includes built-in actions as well as any custom actions declared in the module. Upon selecting an action, you will be prompted to provide the parameters for the action builder.

The last section is to specify filters for the rule, which is optional. If you don't specify any filters, it will match all runs for the preceding criteria. Filters are able to be based on the input/output of the run, the stats on the run (e.g. latency, token counts), the results of other rules doing online evaluation, and more. Filters can be composed with "and", "not", and "or" to specify even more fine-grained behavior. For example, here are filters set up to only match runs with a latency more than 5s and with a feedback score filter from another rule (zoomed out so you can see most of the form):

![Create rule](images/filters-example.png)



## Built-in Actions

### aor/eval

The `aor/eval` action runs an evaluator on an agent or node execution and attaches the resulting feedback to that execution. This enables continuous evaluation of agent performance in production, with the feedback viewable in traces and contributing to agent analytics. Selecting this action simply requires specifying which evaluator to use.

### aor/add-to-dataset

The `aor/add-to-dataset` action automatically adds agent or node runs to a dataset. This is particularly useful for building training datasets from production usage, collecting edge cases that surfaced in real deployments, or systematically gathering examples for future experimentation.

![Add to Dataset Action Builder](images/add-to-dataset-action.png)

The action requires specifying which dataset to add to as well as [JSON path templates](Datasets,-evaluators,-and-experiments#experiments) for the input and output for the new example. The JSON path templates allow the input/output from the run to be transformed to the shape desired for the dataset.

The input to the run is a list of arguments to the agent or node. For an agent, the output is the agent result. For a node, the run output is the agent result if the node set it, or otherwise a list of emit information that looks like:

```
[{"node": "node2", "args": ["arg1", 2]}, {"node": "node3", "args": [1]}]
```

If you set the JSON path template for the input to `$[0]`, then the example's input will be the first argument to the run. Setting the output JOSN path template to `{"result": "$[0].args[0]"}` would set the example's output to `{"result": "arg1"}` when run on the above node emit example.

### aor/webhook

The `aor/webhook` action posts a JSON payload to an external URL, enabling integration with things like monitoring systems and alerting platforms.

![Webhook Action Builder](images/webhook-action.png)

You configure the URL, timeout, HTTP headers, and the payload template. The template can include placeholders that get replaced with the actual input, output, and comprehensive run information including timing, feedback, and operation details.

## Custom Actions

You can declare custom action builders in your agent topology to create actions tailored to your specific needs. Action builders are similar to evaluator builders - they take in a params map and return the function to perform the action.

The action function receives four arguments. The first is a fetcher object that provides access to all declared agent objects like models, stores, or databases. The second is the input from the agent or node execution. The third is the run's output. The last is a "run info" object containing comprehensive metadata about the execution like stats, feedback, and timing information.

Actions return a map with string keys. This map gets recorded in the action log for any rules using this builder, allowing you to track what each action produced and use that information in dependent actions or telemetry queries. More information about action logs is in the next section.

Here's an example of declaring a custom action in a module:

#### Java API

```java
@Override
protected void defineAgents(AgentTopology topology) {
  topology.declareActionBuilder("print-action",
    "Prints info about the run to stdout",
    (Map<String, String> params) -> {
      String logLevel = params.get("logLevel");
      return (AgentObjectFetcher fetcher, Object input, Object output, RunInfo runInfo) -> {
        // Custom action logic here
        System.out.println(String.format("[%s] Agent: %s, Latency: %d ms",
          logLevel, runInfo.getAgentName(), runInfo.getLatencyMillis()));

        return new HashMap<String, Object>() {{
          put("logged", true);
        }};
      };
    },
    ActionBuilderOptions.params("logLevel", "Log level (info/debug)", "info"));
}
```

#### Clojure API

```clojure
(aor/defagentmodule MyModule
  [topology]
  (aor/declare-action-builder
    topology
    "print-action"
    "Prints info about the run to stdout"
    (fn [params]
      (let [log-level (get params "logLevel")]
        (fn [fetcher input output run-info]
          ;; Custom action logic here
          (println (format "[%s] Agent: %s, Latency: %s ms"
                           log-level
                           (:agent-name run-info)
                           (:latency-millis run-info)))

          {"logged" true})))
    {:params {"logLevel" {:description "Log level (info/debug)" :default "info"}}})

  ;; ... rest of module definition ...
  )
```


## Action Logs

Every action execution is logged with detailed information about what happened. The action log includes when the action started and finished, which agent or node execution it processed, whether it succeeded or failed, and any information returned from the action.

Action logs are accessible from the list of rules for the agent:

![Rules list](images/rules-list.png)

Clicking on "View" in the "Action Log" column goes to this page:

![Action](images/action-log.png)

From here you can navigate to the trace of the agent run associated with each log and see detailed information about the action's execution.

When actions fail, the error information is captured in the log, making it easy to understand what went wrong without needing to query external systems. The logs include both the exception message and stack trace, providing full context for troubleshooting.

## Time-Series Telemetry


The analytics page for an agent shows time-series telemetry from all agent and node executions, aggregating a wide variety metrics at multiple granularities. Agent-level metrics include success rates, end-to-end latency, token counts, and time-to-first-token for streaming responses. Model-level metrics track call counts, success rates, and latencies for LLM interactions. Store and database operations are tracked with read and write latencies,

![Metrics dashboards 1](images/telemetry1.png)
![Metrics dashboards 2](images/telemetry2.png)
![Metrics dashboards 3](images/telemetry3.png)

You can change the granularity and time window viewed for all charts. Additionally, you can split all charts by any [metadata](Programming-agents#metadata) key used across all agent invocations:

![Metrics dashboards 1](images/telemetry-metadata.png)

In this case, one of the metadata keys is "model", and there are twice as many invokes with "openai" as the other models. You're able to see how the choice of model changes agent latency, token counts, or any other metric.

Besides being a parameter for agent execution, metadata also is used for analytics to provide further capabilities. Agent-o-rama automatically aggregates per metadata value as well as for the time bucket as a whole.

At most five metadata values are tracked per bucket, so metadata telemetry works best for low-cardinality metadata keys.

### Evaluator Telemetry

When rules run evaluators on agent executions, the resulting feedback scores automatically become additional telemetry metrics at the bottom of the analytics page. Each evaluator rule produces time-series data for every score it generates, enabling continuous monitoring of quality metrics alongside operational metrics.

![Evaluator telemetry](images/telemetry-eval.png)
