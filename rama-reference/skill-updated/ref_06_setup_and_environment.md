# Reference 06 — Setup, Environment & Troubleshooting
**Purpose:** Operational guide for getting Agent-o-rama running locally.  
**Complements:** The main SKILL.md (design thinking) and refs 01–05 (API patterns).  
**Source:** Agent-o-rama quickstart wiki, verified project setup, Chat-o-rama.

---

## Prerequisites

| Requirement | Version | Why |
|-------------|---------|-----|
| Java | 21+ (25 works) | Agent nodes use virtual threads |
| Maven | 3.x | Dependency management; required for correct classpath |
| Git | Any | Clone the AOR repository |
| LLM API Key | Varies | OpenAI, Gemini, or Anthropic — set as environment variable |

---

## Getting Started

### Clone and navigate

```bash
# Clone the repository
git clone https://github.com/redplanetlabs/agent-o-rama.git

# Navigate to the Java examples
cd agent-o-rama/examples/java
```

### Set environment variables

**macOS (temporary, current shell session):**
```bash
export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=your_key_here
export TAVILY_API_KEY=tvly-...
```

**macOS (permanent):** add the `export` lines above to `~/.zshrc` (default shell on macOS), then `source ~/.zshrc`.

**Windows equivalent, for reference:** `set VAR=value` for the session, or System Properties → Environment Variables → New for permanent.

**IntelliJ:** Run Configuration → Environment Variables field.

**Best practice:** Store model names as environment variables too (e.g. `GEMINI_MODEL_NAME`), since Google's model naming changes frequently.

---

## Running Examples

### From command line (recommended)

```bash
cd agent-o-rama/examples/java

# Run a specific example
mvn exec:java -Dexec.mainClass="com.rpl.agent.basic.BasicAgent"
```

### From IntelliJ

**IMPORTANT:** Running directly from IntelliJ's green arrow often fails with `NoClassDefFoundError` because Rama's dependency has `<scope>provided</scope>` in the pom.xml. See Troubleshooting below.

### Key examples in the repository

| Example | What it demonstrates |
|---------|---------------------|
| `basic/BasicAgent` | Simplest agent — no LLM, just structure |
| `basic/LangChain4jAgent` | LangChain4j with streaming |
| `react/ReActModule` | ReAct loop with web search (needs Tavily API key) |
| `research/` | Multi-step research agent |

---

## LLM Integration via LangChain4j

Agent-o-rama uses LangChain4j for LLM access. Any model LangChain4j supports can be used.

### Gemini setup

```xml
<!-- pom.xml dependency -->
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j-google-ai-gemini</artifactId>
    <version>1.8.0</version>  <!-- verify against your project's working version -->
</dependency>
```

```java
// Non-streaming
topology.declareAgentObjectBuilder("gemini-model", setup -> {
    return GoogleAiGeminiChatModel.builder()
        .apiKey(System.getenv("GOOGLE_API_KEY"))
        .modelName(System.getenv("GEMINI_MODEL_NAME"))  // e.g. "gemini-2.0-flash"
        .build();
});

// Streaming
topology.declareAgentObjectBuilder("gemini-model", setup -> {
    return GoogleAiGeminiStreamingChatModel.builder()
        .apiKey(System.getenv("GOOGLE_API_KEY"))
        .modelName(System.getenv("GEMINI_MODEL_NAME"))
        .build();
});
```

### OpenAI setup

```xml
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j-open-ai</artifactId>
    <version>1.8.0</version>
</dependency>
```

```java
topology.declareAgentObjectBuilder("openai-model", setup -> {
    return OpenAiChatModel.builder()
        .apiKey(System.getenv("OPENAI_API_KEY"))
        .modelName("gpt-4o-mini")
        .build();
});
```

### Accessing in a node

```java
.node("process", null, (AgentNode agentNode, String input) -> {
    ChatModel model = agentNode.getAgentObject("gemini-model");
    String response = model.chat(input);
    agentNode.result(response);
});
```

---

## The Web UI (Port 1974)

Enable observability by wrapping your code with `UI.start(ipc)`:

```java
try (InProcessCluster ipc = InProcessCluster.create();
     AutoCloseable ui = UI.start(ipc)) {
    // Agents launch here
    // UI available at http://localhost:1974
}
```

**Without** `UI.start(ipc)`, no traces are recorded.

The UI shows: invocation history, execution traces (step-by-step), token usage per LLM call, timing per node, tool calls and their results. All data persists in Rama PStates across restarts.

---

## Starting a New Project (Not from Examples)

When creating a fresh project (not modifying the examples), the safest approach is to **copy a working `pom.xml`** from either:
- The AOR examples directory (`agent-o-rama/examples/java/pom.xml`)
- A verified working project (e.g. a personal assistant already compiling on AOR)

Key things in the pom.xml:
- Rama dependency with `<scope>provided</scope>` — this is intentional for deployment but causes IDE issues locally
- Agent-o-rama dependency
- LangChain4j provider dependency matching your chosen LLM
- Java 21+ compiler source/target

---

## Troubleshooting

### NoClassDefFoundError: com/rpl/rama/RamaModule

**Cause:** Rama's dependency has `<scope>provided</scope>` in pom.xml. Maven includes it at compile time but excludes it from the runtime classpath. IntelliJ's Run button uses that classpath, so the class isn't found.

**Solutions (pick one):**
1. **Run via Maven** (recommended): `mvn exec:java -Dexec.mainClass="..."`
2. **Check for a `run-example` script** in the examples directory
3. **Temporarily remove `<scope>provided</scope>`** from the Rama dependency in pom.xml for local development — add it back before deploying

### Maven dependencies not resolving in IntelliJ

Right-click `pom.xml` → Maven → Reload Project. Or: `Ctrl+Shift+A` → "Reload All Maven Projects".

### Port 1974 already in use

A previous run didn't shut down cleanly. Kill the Java process holding the port, or restart IntelliJ.

### Serialization errors in PState stores

Rama's serializer requires mutable collection types. Use `ArrayList` and `HashMap`, **not** `List.of()` or `Map.of()`:

```java
// WRONG — will fail at runtime
meta.put("skills", List.of("java", "clojure"));

// CORRECT
meta.put("skills", Arrays.asList("java", "clojure"));

// Also correct
meta.put("skills", new ArrayList<>(List.of("java", "clojure")));
```

---

## Resources

| Resource | URL |
|----------|-----|
| Quickstart | https://github.com/redplanetlabs/agent-o-rama/wiki/Quickstart |
| Programming Agents wiki | https://github.com/redplanetlabs/agent-o-rama/wiki/Programming-agents |
| Javadoc | https://redplanetlabs.com/aor/javadoc/index.html |
| Rama Docs | https://redplanetlabs.com/docs/ |
| Chat-o-rama (AI assistant) | https://chat.redplanetlabs.com |
