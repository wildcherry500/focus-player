<!-- Source: agent-o-rama GitHub wiki (Interfacing-with-LLMs) | Fetched: 2026-07-30 -->

# Interfacing with LLMs

Agent-o-rama integrates with [LangChain4j](https://docs.langchain4j.dev/) for AI model interactions, automatically capturing traces and streaming model calls without requiring any special configuration.  It's important to understand that Agent-o-rama is fundamentally an orchestration tool where you write arbitrary code to integrate with any tools or services you need. So using LangChain4j is completely optional. You can use any LLM library or API client you prefer. If you choose not to use LangChain4j, you'll need to create your own wrappers to record nested operations for tracing and telemetry, but Agent-o-rama doesn't require any particular AI library or model provider.

## Automatic Tracing

When you declare LangChain4j chat models as [agent objects](Programming-agents#agent-objects), Agent-o-rama automatically wraps them to capture detailed execution information. Every model call is recorded in the agent trace with timing information, token counts, request and response data, and metadata about the model used. This information appears in the UI trace view and contributes to time-series telemetry, giving you complete visibility into how your agents interact with AI models.

## Example usage

Here's a basic example of an agent interfacing with an LLM by just doing a single prompt. It declares the model as an agent object, retrieves it in the node, and then invokes it using LangChain4j's API:

#### Java API

```java
public class AgentObjectsModule extends AgentModule {
  @Override
  protected void defineAgents(AgentTopology topology) {
    topology.declareAgentObject("openai-api-key", System.getenv("OPENAI_API_KEY"));
    topology.declareAgentObjectBuilder("openai-model", setup -> {
      String apiKey = setup.getAgentObject("openai-api-key");
      return OpenAiStreamingChatModel.builder()
                                     .apiKey(apiKey)
                                     .modelName("gpt-4o-mini")
                                     .build();
      });
    topology.newAgent("AgentWithObjects")
            .node("process", null, (AgentNode agentNode, String input) -> {
              ChatModel model = agentNode.getAgentObject("openai-model");
              String response = model.chat(input);
              agentNode.result(response);
            });
  }
}
```

#### Clojure API

```clojure
(aor/defagentmodule AgentObjectsModule
  [topology]
  (aor/declare-agent-object topology "openai-api-key" (System/getenv "OPENAI_API_KEY"))
  (aor/declare-agent-object-builder
   topology
   "openai-model"
   (fn [setup]
     (-> (OpenAiStreamingChatModel/builder)
         (.apiKey (aor/get-agent-object setup "openai-api-key"))
         (.modelName "gpt-4o-mini")
         .build)))
  (-> (aor/new-agent topology "AgentWithObjects")
      (aor/node
       "process"
       nil
       (fn [agent-node input]
         (let [model (aor/get-agent-object agent-node "openai-model")]
           (aor/result! agent-node (lc4j/chat model input)))))))
```


## Streaming Model Wrapping

When you declare a `StreamingChatModel` as an agent object, Agent-o-rama automatically wraps it to stream tokens from the model to the node for the agent. The key detail is that when you fetch the model in an agent node, you always receive a `ChatModel` interface, not `StreamingChatModel`. This design allows you to use streaming models in a blocking style within your agent nodes while clients can subscribe to streams to receive tokens in real-time.

This wrapping happens automatically when you fetch the agent object in a node. You declare it as a `StreamingChatModel` in the topology, but retrieve it as a `ChatModel` when you use it. The framework handles converting between the streaming interface and the blocking interface, capturing all streaming tokens along the way. See the [Streaming documentation](Streaming) for more details.

If you don't want streaming behavior, declare the model as a non-streaming `ChatModel` instead. The framework will still automatically trace all calls, but won't capture or forward streaming tokens.

## Structured Outputs

LangChain4j supports structured outputs through JSON schema enforcement, allowing you to define the exact structure you want the model to return. This is useful for extracting structured data or integrating with APIs that require specific schemas.

To use structured outputs, you create a JSON schema defining your desired structure and configure the model request with a `ResponseFormat` object. The model will then return responses matching that schema, making it easy to parse and use the structured data in your agent logic.

Currently, structured outputs with JSON schema enforcement only work with non-streaming chat models due to limitations in LangChain4j. If you need structured outputs, use a regular `ChatModel` rather than a `StreamingChatModel`. The framework still provides full tracing and telemetry for these structured calls, just without the streaming behavior.

Here's an example of using LangChain4j with structured outputs. This code can be used directly within agent nodes:

### Java API

```java
import dev.langchain4j.model.chat.request.ResponseFormat;
import dev.langchain4j.model.chat.request.ResponseFormatType;
import dev.langchain4j.model.chat.request.json.JsonSchema;
import dev.langchain4j.model.chat.request.json.JsonObjectSchema;
import dev.langchain4j.model.chat.request.json.JsonArraySchema;
import dev.langchain4j.model.chat.request.ChatRequest;
import dev.langchain4j.data.message.UserMessage;

JsonSchema analysisSchema = JsonSchema.builder()
  .name("QuestionAnalysis")
  .rootElement(JsonObjectSchema.builder()
    .addStringProperty("questionType", "Type of question")
    .addStringProperty("complexity", "Complexity level")
    .addProperty("mainTopics", JsonArraySchema.builder()
      .items(JsonStringSchema.builder().build())
      .build())
    .build())
  .build();

ResponseFormat responseFormat = ResponseFormat.builder()
  .type(ResponseFormatType.JSON)
  .jsonSchema(analysisSchema)
  .build();

ChatRequest request = ChatRequest.builder()
  .messages(List.of(new UserMessage("Analyze this question")))
  .responseFormat(responseFormat)
  .build();

ChatResponse response = model.chat(request);
```

### Clojure API

```clojure
(require '[com.rpl.agent-o-rama.langchain4j :as lc4j]
         '[com.rpl.agent-o-rama.langchain4j.json :as lj])

(def QuestionAnalysis
  (lj/object
   {:description "Analysis of a user question"}
   {"question_type" (lj/enum "Type of question"
                            ["factual" "analytical" "creative"])
    "complexity" (lj/enum "Complexity level"
                         ["simple" "moderate" "complex"])
    "main_topics" (lj/array "Key topics"
                           (lj/string "A main topic"))}))

(let [model (aor/get-agent-object agent-node "openai-model")
      response (lc4j/chat model
                          (lc4j/chat-request
                           [(UserMessage. "Analyze this question")]
                           {:response-format
                            (lc4j/json-response-format
                             "QuestionAnalysis"
                             QuestionAnalysis)}))]
  ;; ...
  )
```

The `com.rpl.agent-o-rama.langchain4j.json` namespace provides helper functions for building JSON schemas with types like `lj/object`, `lj/string`, `lj/number`, `lj/array`, and `lj/enum`, making it straightforward to define complex schemas in Clojure.

## Using Other Tools

Agent-o-rama doesn't require LangChain4j – you can integrate with any LLM provider or API client you prefer. If you're not using LangChain4j, you'll need to manually record nested operations for tracing and telemetry using the `recordNestedOp` method on `AgentNode`.

When you manually record nested operations, you specify the operation type, timing information, and any metadata you want to include. This information appears in traces and contributes to telemetry just like automatic LangChain4j tracing, giving you the same observability regardless of which tools you use.

### Java API

```java
topology.newAgent("MyAgent")
        .node("process", null, (AgentNode agentNode, String input) -> {
          long startTime = System.currentTimeMillis();

          String response = callCustomLLMService(input);

          long finishTime = System.currentTimeMillis();

          Map<String, Object> info = new HashMap<>();
          info.put("model", "custom-model");
          info.put("inputTokenCount", estimateTokens(input));
          info.put("outputTokenCount", estimateTokens(response));
          info.put("totalTokenCount", estimateTotalTokens(input, response));
          // add any other metadata you wish to track to the info map

          agentNode.recordNestedOp(
            NestedOpType.MODEL_CALL,
            startTime,
            finishTime,
            info
          );

          agentNode.result(response);
        });
```

### Clojure API

```clojure
(aor/node
 "process"
 nil
 (fn [agent-node input]
   (let [start-time (System/currentTimeMillis)
         ;; Call your LLM API or custom service
         response (call-custom-llm-service input)
         finish-time (System/currentTimeMillis)]

     ;; Record the operation for tracing and telemetry
     (aor/record-nested-op!
      agent-node
      :model-call
      start-time
      finish-time
      {"model" "custom-model"
       "inputTokenCount" (estimate-tokens input)
       "outputTokenCount" (estimate-tokens response)
       "totalTokenCount" (estimate-total-tokens input response)
       ;; add any other metadata you wish to track to the info map
       })

     (aor/result! agent-node response))))
```

Available operation types include `MODEL_CALL`, `TOOL_CALL`, `STORE_READ`, `STORE_WRITE`, `DB_READ`, `DB_WRITE`, `AGENT_CALL`, `HUMAN_INPUT`, and `OTHER`. Choose the type that best matches your operation, as this categorization helps organize telemetry and make traces more readable.

By manually recording nested operations, you maintain full control over how you integrate with external services while still getting the same rich tracing and telemetry that LangChain4j integration provides automatically.
