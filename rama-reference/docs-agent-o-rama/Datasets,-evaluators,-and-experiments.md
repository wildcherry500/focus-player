<!-- Source: agent-o-rama GitHub wiki (Datasets,-evaluators,-and-experiments) | Fetched: 2026-07-30 -->

# Datasets, Evaluators, and Experiments

Building reliable LLM agents requires systematic evaluation. Without proper testing, you can't know if your agent is actually improving or if changes are making things worse. Agent-o-rama's evaluation framework addresses the core challenges of LLM agent development:

- **Subjective Assessment**: Manual testing is time-consuming and inconsistent
- **Edge Case Discovery**: Real-world usage reveals unexpected behaviors
- **Regression Detection**: Changes can break previously working functionality
- **Performance Measurement**: Quantifying improvement requires systematic metrics

This page explodes Agent-o-rama's features for evaluating agent performance systematically and rigorously:

- **Structured Datasets**: Organized test cases with inputs and optional reference outputs
- **Evaluators**: Measure performance using either custom functions or LLM judges
- **Experiments**: Run controlled tests across different agents and configurations

## Table of Contents
- [Datasets](#datasets)
- [Remote datasets](#remote-datasets)
- [Evaluators](#evaluators)
- [Experiments](#experiments)
- [Comparative experiments](#comparative-experiments)

## Datasets

Datasets are collections of structured examples used for testing and evaluating agents. Each example contains input data, an optional reference output, and any number of tags. Experiments are able to run on entire datasets or subsets of a dataset.

Reference outputs are the "correct" or expected responses for a given input. They serve multiple purposes:

- **Quality Assessment**: Compare agent outputs against known good responses
- **Regression Testing**: Ensure changes don't break previously working functionality
- **Performance Measurement**: Quantify how close agent outputs are to ideal responses

There are many cases where you don't have a good reference output for an example, which is why its optional. Perhaps you're just collecting a set of real world prompts, or you want a subject matter expert to review the example and develop a reference output later.

### Creating Datasets

Datasets can be created through the UI or programmatically. Each dataset has a name, description, and optional [JSON schemas](https://json-schema.org/) for input and output validation. Configuring JSON schemas is highly recommended to prevent mistakes.

![Dataset Creation UI](images/dataset-creation.png)

Here are examples of simple JSON schemas for common use cases:

**Object Schema:**
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "User's question or request"
    },
    "context": {
      "type": "object",
      "properties": {
        "user_type": {"type": "string"},
        "priority": {"type": "string", "enum": ["low", "medium", "high"]}
      }
    }
  },
  "required": ["query"]
}
```

**String Schema:**
```json
{
  "type": "string",
  "maxLength": 1000
}
```

#### Java API

```java
AgentManager manager = AgentManager.create(cluster, moduleName);

// Create a dataset with JSON schemas for validation
UUID datasetId = manager.createDataset(
    "customer-support-examples",
    "Customer support conversation examples for testing response quality",
    "{\"type\": \"object\", \"properties\": {\"query\": {\"type\": \"string\"}, \"context\": {\"type\": \"object\"}}}",
    "{\"type\": \"string\", \"maxLength\": 1000}"
);
```

#### Clojure API

```clojure
(def manager (aor/agent-manager cluster module-name))

;; Create a dataset with JSON schemas for validation
(def dataset-id
  (aor/create-dataset! manager
    "customer-support-examples"
    {:description "Customer support conversation examples for testing response quality"
     :input-json-schema "{\"type\": \"object\", \"properties\": {\"query\": {\"type\": \"string\"}, \"context\": {\"type\": \"object\"}}}"
     :output-json-schema "{\"type\": \"string\", \"maxLength\": 1000}"}))
```

### Adding Examples

There are several ways to add examples to datasets:

#### 1. Manually via the UI

From the dataset page, you can add an example manually:

![Add from Trace](images/add-dataset-manual.png)


#### 2. From an agent or node in a trace

You can also add an example from the trace UI:

![Add from Trace](images/add-dataset-trace.png)

On the right is a button to add the input/output of the agent as a whole, and on the bottom is a button to add just the input/output for the selected node. In either case, it brings up a dialog to select the dataset to add to and lets you edit the input/output before submitting it.

#### 3. Bulk import from a JSONL file

You can import from JSON files via the UI:

![Bulk Import UI](images/bulk-import.png)

A [JSONL](https://jsonlines.org/) file encodes a JSON-encoded example on each line with "input", "output", and "tags" fields, like so:

```json
{"input": "The Earth orbits the Sun.", "output": "factual"}
{"input": "Fish can breathe underwater.", "output": "factual", "tags": ["tag1", "tag2"]}
{"input": "Bananas are made of steel.", "output": "nonsense", "tags": ["tag1"]}
```


#### 4. Programmatically

You can add examples programmatically using the AgentManager API. This is useful for automated data collection or integration with other systems.

**Java:**
```java
// Add a single example with reference output and tags
AddDatasetExampleOptions options = new AddDatasetExampleOptions();
options.referenceOutput = new HashMap<String, Object>() {{
    put("response", "You can reset your password by clicking 'Forgot Password' on the login page.");
    put("confidence", 0.95);
}};

UUID exampleId = manager.addDatasetExample(datasetId,
    "How do I reset my password?"
    options);
```

**Clojure:**
```clojure
;; Add a single example with reference output and tags
(aor/add-dataset-example! manager dataset-id
  "How do I reset my password?"
  {:reference-output {"response" "You can reset your password by clicking 'Forgot Password' on the login page."
                      "confidence" 0.95}
   :tags #{"password" "authentication" "common"}})
```

#### 5. Add a filtered sample from production runs with an online action

You can automatically collect examples from production agent runs using [actions](Actions,-rules,-and-telemetry). Actions are rules that run automatically when certain conditions are met during agent execution. You could use actions to:

**Example Use Cases:**
- Collect successful customer support interactions
- Make a dataset of all high latency interactions for later analysis
- Make a dataset of 0.1% of all runs
- Capture edge cases that caused agent failures

This enables continuous agent improvement based on actual performance in production.

### Dataset Snapshots

Snapshots create immutable versions of datasets at specific points in time, enabling reproducible experiments and version control. You can snapshot datasets in the UI:

![Dataset Snapshots](images/new-snapshot.png)


You can also snapshot datasets programmatically ([Javadoc](https://redplanetlabs.com/aor/javadoc/com/rpl/agentorama/AgentManager.html#snapshotDataset(java.util.UUID,java.lang.String,java.lang.String)) and [Clojuredoc](https://redplanetlabs.com/aor/clojuredoc/com.rpl.agent-o-rama.html#var-snapshot-dataset.21)).

### Example Management

You can edit example inputs/outputs/tags at any time either via the UI or programmatically, and the UI allows you to search for examples by a matching string.


## Remote datasets

When creating a dataset, there's an option to create a remote dataset:

![Remote Datasets](images/remote-dataset.png)

A remote dataset can be on a different module in the same cluster, or it can be on a module in a different cluster. When you provide the location in this form, it creates a local proxy for that dataset which you can use to run experiments against its examples.

Note that creating a remote dataset on a different cluster requires that cluster to be using the same version of Rama.

When creating an experiment on a remote dataset, there's also an option when selecting evaluators to select remote evaluators. This uses the evaluator definitions from that remote module locally. This requires that you have the same evaluator builders defined locally. Using remote evaluators saves a step during testing of having to create those evaluators in your local environment before running the experiment.

The primary use case for remote datasets are to test agents or new versions of agents in [IPC](Programming-agents#local-development) before deploying to a production cluster.

## Evaluators

Evaluators are arbitrary functions that measure agent performance by analyzing outputs and producing scores. They're the core of systematic agent evaluation. They're used for both offline experiments against datasets and for [online evaluation](Actions,-rules,-and-telemetry) of production runs. They can be anything from a simple custom Java function checking for a regular expression match to an LLM judge prompted to provide a score for helpfulness.

Evaluators are created through a two-step process:

1. **Select an Evaluator Builder**: Choose from built-in builders or a custom builder declared as part of the module
2. **Create an Evaluator Instance**: Provide a name and parameters to instantiate the evaluator

Evaluator builders define what parameters the evaluator accepts, a description of what it does (displayed in the UI), and the actual evaluation logic.

You can declare your own evaluator builders in your module to create evaluators tailored to your specific needs.

### What Evaluators Do

Evaluators can be run against an agent as a whole or a particular node of an agent execution. These are classified generally as "runs".

Evaluators take the run input, example reference output (if there is one), and the run output, and return a map of score names to score values. For an agent, the run outputs is just the result of the agent. For a node, the run output is the agent result if the node set it, or otherwise a list of emit information that looks like:

```
[{"node": "node2", "args": ["arg1", 2]}, {"node": "node3", "args": [1]}]
```

This shows which nodes were emitted to with which arguemnts and in which order.

Evaluators return maps where each key is a score name and each value is a score. Scores can be:

- **Numbers**: Quantitative metrics (0.0 to 1.0, 1 to 10, percentages, etc.)
- **Booleans**: Binary classifications (true/false, pass/fail)
- **Strings**: Categorical classifications ("factual" vs "nonsense", "toxic" vs "non-toxic")

**Examples:**
```clojure
;; Number scores for quantitative assessment
{"accuracy" 0.85, "helpfulness" 8.5, "relevance" 0.92}

;; Boolean scores for binary classification  
{"concise?" true, "factual?" false, "appropriate?" true}

;; String scores for categorical classification
{"sentiment" "positive", "category" "technical", "quality" "high"}
```

Most evaluators return just one score, but there are cases where you may want an evaluator to compute multiple scores at the same time. For instance, you may want an LLM to judge both "relevance" and "completeness".

There are three types of evaluators:

#### Regular Evaluators

Regular evaluators assess an individual agent or node run. They receive three inputs:

1. **Input**: The input to the agent
2. **Reference Output**: The "correct" or expected output from the example, if one exists
3. **Run Output**: What the run actually produced

**Example Scenario:**
- **Input**: `"What is the capital of France?"`
- **Reference output**: `"Paris"`
- **Run Output**: `{"answer": "The capital of France is Paris.", "confidence": 0.95}`
- **Evaluator Result**: `{"accuracy": 0.95}`

#### Comparative Evaluators

Comparative evaluators are used in [comparative experiments](#comparative-experiments). Sometimes its easier to say which response is better than to independently score each response individually. For example, consider these two responses to "How can I fall asleep faster at night?"

```
Response 1
----------
Try keeping a consistent bedtime and avoiding screens before bed.


Response 2
----------
Go to bed at the same time each night, keep your room dark and cool, and avoid screens or bright lights for at least 30 minutes before bed. If your mind is racing, try a simple routine like slow breathing or writing down tomorrow’s tasks. Avoid caffeine after noon and heavy meals close to bedtime — consistency and calm are what cue your body to sleep faster.
```

Individually, they would both score high for being accurate, helpful, and concise. But response 2 is clearly better.

Comparative evaluators receive as input:
1. **Input**: The input to the run
2. **Reference Output**: The "correct" or expected output from the example, if one exists.
3. **Multiple Run Outputs**: A list of outputs to compare

Just like other evaluator types, comparative evaluators return a map of scores. The `"index"` score is treated specially in the UI, as in the comparative experiment results it will highlight the winning output. For example, `{"index": 1}` means the second output (index 1) is the best.

#### Summary Evaluators

Some metrics can only be calculated by looking at all examples together, like false positive rate, precision, and recall scores. Those cannot be scored by looking at one example at a time. Summary evaluators are able to calculate these kinds of scores.

Summary evaluators receive a list of all the individual example runs from the experiment. Each example run contains the input, reference output, and output.

**Example Scenario:**
- **Input**: 100 question-answering examples
- **Individual Results**: Each example gets scored individually
- **Summary Evaluation**: Calculate accuracy across all examples
- **Result**: `{"accuracy": 0.87}`


### Creating Evaluators

You can create evaluators in the evaluators section of the UI. After selecting an evaluator builder, this dialog comes up:

![Create evaluator](images/create-evaluator-conciseness.png)

An evaluator is given a name, description, and values for all parameters for the selected evaluator builder. Additionally, you need to specify how to extract data from the input, reference output, and outputs.

The input, reference output, and output may not be in the shape necessary for the evaluator function. For example, consider the built-in "aor/conciseness" evaluator. This requires the output to be a plain string so it can check the length. But perhaps your agent outputs data of the form:

```
{"result": "abcdef",
 "metadata": {"confidence": 0.8, "documents-searched": 25}}
```

Rather than have to write the same evaluator again for a slightly different input shape, the input/reference output/output lets you use the same evaluator builder on data of any shape.

[JSON paths](https://en.wikipedia.org/wiki/JSONPath) are used to specify what data to extract. For this particular example, the JSON path would be `$.result`.

Evaluator builders may not look at all of the input, reference output, and output (e.g. "aor/conciseness" only looks at the output), and their definitions specify which JSON paths need to be provided. In this screenshot you can see it only requests a JSON path for the output. JSON paths default to `$`, which just passes the whole object in as the argument.

### Built-in Evaluator Builders

Agent-o-rama provides several built-in evaluator builders for common evaluation tasks:

#### LLM Judge
**Type**: Regular
**Purpose**: Uses LLM to assess output quality

**Parameters:**
- `model`: Name of the model to use (must be declared as an agent object)
- `prompt`: Evaluation prompt with %input, %output, %referenceOutput variables
- `temperature`: Model temperature (default: 0.0)
- `outputSchema`: JSON schema for the output (default: single "score" field 0-10)

**Example Use Cases:**
- Rate helpfulness on a scale of 1-10
- Check if output is factual vs. opinion
- Assess creativity or engagement

![LLM Judge Configuration](images/create-evaluator-llm-judge.png)

#### Conciseness
**Type**: Regular  
**Purpose**: Checks if outputs meet length requirements

**Parameters:**
- `threshold`: Maximum character length allowed

![Concisenss evaluator](images/create-evaluator-conciseness.png)

#### F1 Score
**Type**: Summary  
**Purpose**: Measures [F1 score](https://en.wikipedia.org/wiki/F-score), precision, and recall

**Parameters:**
- `positiveValue`: Value considered a positive classification, e.g. "toxic" for a task where the possible outputs are "toxic" or "not toxic"

![F1 Score Configuration](images/create-evaluator-f1.png)



### Custom Evaluator Builders

You can declare custom evaluator builders in your agent topology to create evaluators tailored to your specific needs. Custom evaluators give you complete control over the evaluation logic and can access any agent objects declared in your topology like LLMs, stores, or databases.

**Evaluator Function Signatures:**

The function signature depends on the evaluator type. All custom evaluators receive a fetcher object as their first argument, which provides access to all declared agent objects (models, stores, databases, etc.) using the [same API](Programming-agents#agent-objects) as used within node functions. The remaining arguments depend on the evaluator type:

- **Regular Evaluators**: `(fetcher, input, referenceOutput, output) -> Map<String, Object>`
- **Comparative Evaluators**: `(fetcher, input, referenceOutput, outputs) -> Map<String, Object>`
- **Summary Evaluators**: `(fetcher, exampleRuns) -> Map<String, Object>`

The evaluator builder is a function taking in a params map that returns the evaluator function. The parms map is always a map of param name (string) to param value (also string).

The Java API allows you to specify whatever types you want for the input, referenceOutput, and output args.

**Regular Evaluator Example:**

```java
topology.declareEvaluatorBuilder("accuracy-checker",
    "Checks if output contains the correct answer",
    (Map<String, String> params) -> {
        return (AgentObjectFetcher fetcher, Integer input, String referenceOutput, Map output) -> {
            // Custom evaluation logic here
            return new HashMap<String, Object>() {{
                put("accuracy", 0.85);
            }};
        };
    },
    EvaluatorBuilderOptions.param("threshold", "Accuracy threshold", "0.8"));
```

```clojure
(aor/declare-evaluator-builder
  topology
  "accuracy-checker"
  "Checks if output contains the correct answer"
  (fn [params]
    (fn [fetcher input reference-output output]
      ;; Custom evaluation logic here
      {"accuracy" 0.85}))
  {:params {"threshold" {:description "Accuracy threshold" :default "0.8"}}})
```

**Comparative Evaluator Example:**

```java
topology.declareComparativeEvaluatorBuilder("quality-ranker",
    "Ranks outputs by quality",
    (Map<String, String> params) -> {
        return (AgentObjectFetcher fetcher, Object input, String referenceOutput, List<Object> outputs) -> {
            // Custom comparison logic here
            return new HashMap<String, Object>() {{
                put("index", 1);  // Second output is best
                put("confidence", 0.9);
            }};
        };
    },
    EvaluatorBuilderOptions.param("model", "Model to use for ranking", "gpt-4"));
```

```clojure
(aor/declare-comparative-evaluator-builder
  topology
  "quality-ranker"
  "Ranks outputs by quality"
  (fn [params]
    (fn [fetcher input reference-output outputs]
      ;; Custom comparison logic here
      {"index" 1 "confidence" 0.9}))
  {:params {"model" {:description "Model to use for ranking" :default "gpt-4"}}})
```

**Summary Evaluator Example:**

Summary evaluators analyze collections of example runs to provide overall metrics. In Clojure, the fields of `example-runs` can be accessed with `:input`, `:reference-output`, and `:output`.

```java
topology.declareSummaryEvaluatorBuilder("overall-quality",
    "Calculates overall quality metrics",
    (Map<String, String> params) -> {
        return (AgentObjectFetcher fetcher, List<ExampleRun> exampleRuns) -> {
            // Custom summary logic here
            return new HashMap<String, Object>() {{
                put("average_score", 0.82);
                put("consistency", 0.75);
            }};
        };
    },
    EvaluatorBuilderOptions.param("metric", "Quality metric to use", "helpfulness"));
```

```clojure
(aor/declare-summary-evaluator-builder
  topology
  "overall-quality"
  "Calculates overall quality metrics"
  (fn [params]
    (fn [fetcher example-runs]
      ;; Custom summary logic here
      {"average_score" 0.82 "consistency" 0.75}))
  {:params {"metric" {:description "Quality metric to use" :default "helpfulness"}}})
```


## Experiments

Experiments evaluate performance by running agents or individual nodes against datasets and applying evaluators to measure results. Experiments are part of the dataset UI, and starting one brings up this form (zoomed out so all fields are visible):


![Experiment UI](images/experiment-form.png)


You can select to run the experiment against a particular snapshot, against all examples in the dataset, against a particular tag, or against the specific examples that were selected before clicking on "Run New Experiment".

Next, you set up the targets of the experiment. For a regular experiment, there's only one target, and for a comparative experiment you can have any number of targets. Each target is either an agent or a particular node within an agent. For each target you can optionally provide [metadata](Programming-agents#metadata) for its execution, and then you must provide templates for the input arguments. Input argument templates specify how to translate an example's input, which is one object, into arguments to the agent/node, which is a list of parameters.

### JSON Path Templates

Input arguments are specified with "JSON Path templates". JSON path templates are not a standard like JSON paths, but are an Agent-o-rama specific way to provide a flexible way to specify input arguments. A JSON path template simply specifies each argument as normal JSON, but any nested JSON paths are substituted with the result of running that path on the example input. For example, suppose the example input is:

```
{"name": "Jack Benny",
 "age": 39}
```

Now suppose the agent takes in three arguments. Suppose you set the input arguments like so:

```
Input arg 1: $.name
Input arg 2: {"model": "openai"}
Input arg 3: {"user-age": "$.age", "foo": "$$"}
```

The agent will run with the arguments `("Jack Benny", {"model": "openai"}, {"user-age": 39, "foo": "$"})`. Note that it's not running with JSON strings, but with those objects. The last arg also demonstrates how escape a literal "$" without it being interpreted as a JSON path with "$$".

Next, you select any number of evaluators to use. Regular experiments can only use **regular** or **summary** evaluators, while comparative experiments can only use **comparative** evaluators.

Finally, you can specify the amount of concurrency to use for the experiment and the number of repetitions for each examples. Limiting concurrency can help avoid hitting model API rate limits, but the higher it is the faster the experiment will run. The number of repetitions setting controls how many times each example is run, which can reduce noise and produce a more accurate view of performance.


### Experiment Results

Experiment results look like this:

![Experiment Results](images/experiment-results.png)

For each example run, you can see the example input, the example reference output, and the output from the agent or node target. Along with each output is the result of each evaluator, how long that run took, and the number of tokens used.

You can view a complete trace for each example run by clicking on "View Trace" in the input box. This lets you see detailed info on how exactly that agent or node produced its result. Likewise, you can see a trace for each evaluator run by clicking on the evaluator result. This can be really helpful to understand if your evaluators are working correctly, especially for evaluators that use LLMs.

At the top of the page are aggregate results like average/P99 latencies of runs and the average tokens used. If there were any summary evaluators configured for the experiment, those will also display at the top.

This view will also display any failed runs or any evaluators that had an error during their execution.

The experiments listing page shows additional info:

![Experiment Listing](images/experiment-listing.png)

Along with the aggregated latency/token stats, each row shows an aggregation of each eval. So if you had an eval that scores "helpfulness" from 0 to 10, you'll see the average of all those scores in that row. If an eval scored as a boolean value, like a score named "concise?", you'll see the fraction of values that were true for that eval.

Finally, the top of the listing automatically displays charts showing the trend across all he displayed experiments. You can control which experiments are displayed by using the search box, and the charts will automatically update.


### Comparative experiments

Comparative experiments evaluate two or more targets side-by-side on the same dataset examples, enabling you to compare different agents or nodes against each other. They're useful when it's easier to determine which output is better than to independently score each output against a fixed standard. You can view and create comparative experiments on the datasets page on the UI.

Rather than having to establish what constitutes a "good" score in isolation, a comparative experiment can tell you directly whether the new version produces better outputs than the current one. This is valuable for subjective tasks like creative writing, where defining objective quality metrics is difficult, but judges can reliably say which version is better.

The main differences between regular and comparative experiments are in how targets and evaluators are configured. For comparative experiments, you can specify any number of targets instead of just one. Each target can be an entire agent or a specific node within an agent, and you can mix and match as needed. You might compare three different agents, or the same agent with three different sets of metadata or parameter configurations. You could also compare a full agent against a specific node within another agent to understand how individual components perform.

When configuring a comparative experiment, each target requires the same input argument templates as regular experiments, mapping the dataset example input to the target's function arguments. The experiment runs each example against all targets and collects all outputs before evaluation.

Comparative experiments can only use comparative evaluators, not regular or summary evaluators. This restriction is because comparative evaluators are specifically designed to rank multiple outputs relative to each other. Regular evaluators score individual outputs independently, while summary evaluators analyze metrics across all examples, neither of which aligns with how comparative experiments work.

Comparative evaluators return the same map of scores as other evaluator types, but with one important distinction: the "index" score receives special treatment in the UI. The index score indicates which output is the best, with 0 meaning the first output, 1 meaning the second output, and so on. In the comparative experiment results view, the winning output is highlighted with a green background, making it immediately clear which target performed best for each example. This visual highlighting makes it easy to scan through results and see patterns in which configurations or agents are winning across different types of inputs.

If multiple evaluators are configured, each can return its own index score, and the UI allows you to select which evaluator's index to use for highlighting. This is useful when different evaluators might have different criteria for what makes an output "best"—perhaps one evaluator prioritizes accuracy while another prioritizes conciseness.
