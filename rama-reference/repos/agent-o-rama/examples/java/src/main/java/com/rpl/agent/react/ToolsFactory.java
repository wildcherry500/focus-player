package com.rpl.agent.react;

import com.rpl.agentorama.AgentNode;
import com.rpl.agentorama.ToolInfo;
import dev.langchain4j.agent.tool.ToolSpecification;
import dev.langchain4j.data.document.Document;
import dev.langchain4j.model.chat.request.json.JsonObjectSchema;
import dev.langchain4j.web.search.WebSearchRequest;
import dev.langchain4j.web.search.tavily.TavilyWebSearchEngine;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Factory class for creating tools used by the ReAct agent.
 *
 * This class provides web search capabilities using the Tavily search engine, allowing the agent
 * to search for information on the web and incorporate the results into its reasoning process.
 */
public class ToolsFactory {

  public static List<ToolInfo> createTools() {
    return Arrays.asList(createTavilySearchTool());
  }

  public static List<ToolSpecification> createToolSpecifications() {
    return createTools().stream().map(ToolInfo::getToolSpecification).collect(Collectors.toList());
  }

  private static ToolInfo createTavilySearchTool() {
    ToolSpecification spec =
        ToolSpecification.builder()
            .name("tavily")
            .description("Search the web")
            .parameters(
                JsonObjectSchema.builder()
                    .addStringProperty("terms", "The terms to search for")
                    .build())
            .build();

    return ToolInfo.createWithContext(spec, ToolsFactory::executeTavilySearch);
  }

  /**
   * Executes a web search using the Tavily search engine.
   *
   * @param agentNode The agent node for accessing shared objects
   * @param unused Unused parameter for compatibility
   * @param arguments The tool arguments containing search terms
   * @return Search results as concatenated text
   */
  private static String executeTavilySearch(
      AgentNode agentNode, Object unused, Map<String, Object> arguments) {
    try {
      String terms = (String) arguments.get("terms");
      if (terms == null || terms.trim().isEmpty()) {
        return "Error: No search terms provided";
      }
      TavilyWebSearchEngine tavily = agentNode.getAgentObject("tavily");
      WebSearchRequest searchRequest = WebSearchRequest.from(terms, 3);
      List<Document> searchResults = tavily.search(searchRequest).toDocuments();

      if (searchResults.isEmpty()) {
        return "No search results found for: " + terms;
      }
      return searchResults.stream().map(Document::text).collect(Collectors.joining("\n---\n"));
    } catch (Exception e) {
      return "Error during search: " + e.getMessage();
    }
  }
}
