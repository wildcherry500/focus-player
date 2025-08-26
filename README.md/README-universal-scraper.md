# Universal Documentation Scraper - AI-Enhanced Edition

A powerful Python-based web scraper designed to download and convert entire documentation websites into multiple formats (Markdown, JSON, HTML) with **optional Landing.ai integration** for AI-powered document processing. Perfect for building knowledge graphs, LLM training datasets, and database integration with Rama backends.

**Three Versions Available:**
- **Basic**: `universal-scraper.py` - Fast HTML→Markdown conversion
- **Enhanced**: `universal-scraper-enhanced.py` - Multi-format output with JSON/HTML
- **AI-Enhanced**: `universal-scraper-ai-enhanced.py` - Adds Landing.ai for complex documents

Originally built for Red Planet Labs documentation, now evolved into a complete documentation processing toolkit.

## Features

### Core Capabilities
- 🌐 **Universal Compatibility**: Works with any documentation website
- 📝 **Multi-Format Output**: Saves in Markdown, JSON, and HTML formats
- 🗂️ **Structured Data Extraction**: Creates JSON with hierarchical content structure
- 🔗 **Content Graph Generation**: Builds relationship graphs for knowledge bases
- 📊 **Metadata Extraction**: Captures page metadata, OpenGraph data, and more
- 🖼️ **Image Preservation**: Downloads and organizes all images locally

### AI-Enhanced Processing
- 🤖 **Landing.ai Integration**: Advanced document processing for PDFs and complex layouts
- 📋 **Schema-Based Extraction**: Extract specific fields using predefined or custom schemas
- 📄 **Complex Document Handling**: Process research papers, technical manuals, financial documents
- 🎯 **Selective Processing**: Cost-optimized - only process complex documents with AI
- 📐 **Visual Grounding**: Exact coordinate tracking for compliance and verification
- 💰 **Cost Tracking**: Monitor estimated API usage costs

### Technical Features
- 🤖 **Robots.txt Compliance**: Respects website crawling rules
- 📁 **Organized Output**: Maintains original site structure in format-specific directories
- 🔄 **Site Index Generation**: Creates comprehensive site structure JSON
- 📈 **Progress Tracking**: Real-time progress updates and detailed logging

## Requirements

### Basic Requirements
- Python 3.6+
- Required packages:
  ```bash
  pip install requests beautifulsoup4
  ```

### AI-Enhanced Features (Optional)

**⚠️ Required for AI-Enhanced Version Only**

If you want to use `universal-scraper-ai-enhanced.py`, you need a Landing.ai API key:

#### Step 1: Install the AI Library
```bash
pip install agentic-doc
```

#### Step 2: Get Your FREE Landing.ai API Key
1. **Visit**: [https://docs.landing.ai/ade/agentic-api-key](https://docs.landing.ai/ade/agentic-api-key)
2. **Sign up** for a free Landing.ai account
3. **Copy your API key** from the dashboard

#### Step 3: Set Your API Key
**Option A: Environment Variable (Recommended)**
```bash
# Add to your ~/.bash_profile, ~/.zshrc, or ~/.bashrc
export VISION_AGENT_API_KEY=your-actual-api-key-here

# Or set for current session only
export VISION_AGENT_API_KEY=your-actual-api-key-here
```

**Option B: Create .env File**
```bash
# Create .env file in your project directory
echo "VISION_AGENT_API_KEY=your-actual-api-key-here" > .env
```

#### Step 4: Verify Setup
```bash
# Test that the API key is set
python -c "import os; print('API Key:', os.getenv('VISION_AGENT_API_KEY', 'NOT SET'))"
```

#### Step 5: Test with AI Features
```bash
# Simple test to verify everything works
python universal-scraper-ai-enhanced.py --url https://example.com --landing-ai --formats json
```

**💡 Free Tier Information:**
- Landing.ai provides free credits for new users
- Approximately $0.01 per page processed
- Perfect for testing and small projects
- Check [Landing.ai pricing](https://landing.ai/pricing) for current limits

## Quick Start Guide

### Step 1: Choose Your Version

**For beginners or simple HTML sites:**
```bash
# Use the basic scraper
python universal-scraper.py --url https://docs.example.com/
```

**For structured data and knowledge graphs:**
```bash
# Use the enhanced scraper
python universal-scraper-enhanced.py --url https://docs.example.com/ --formats json,md
```

**For AI-powered document processing:**
```bash
# Use the AI-enhanced scraper (requires API key)
python universal-scraper-ai-enhanced.py --url https://docs.example.com/ --landing-ai
```

### Step 2: Installation

#### Basic Installation (All Versions)
```bash
# Install core dependencies
pip install requests beautifulsoup4
```

#### AI Features (Optional)
```bash
# Only if you want Landing.ai integration
pip install agentic-doc

# Get your free API key from Landing.ai
# Visit: https://docs.landing.ai/ade/agentic-api-key
export VISION_AGENT_API_KEY=<your-api-key>
```

### Step 3: Choose Your Use Case

| Use Case | Recommended Version | Command |
|----------|-------------------|----------|
| **Simple documentation backup** | Basic | `python universal-scraper.py --url URL` |
| **Knowledge graph building** | Enhanced | `python universal-scraper-enhanced.py --url URL --formats json` |
| **Research paper processing** | AI-Enhanced | `python universal-scraper-ai-enhanced.py --url URL --landing-ai --landing-ai-schema research_paper` |
| **Technical manual extraction** | AI-Enhanced | `python universal-scraper-ai-enhanced.py --url URL --landing-ai --landing-ai-schema technical_manual` |
| **Mixed content sites** | AI-Enhanced | `python universal-scraper-ai-enhanced.py --url URL --formats json,md --landing-ai --landing-ai-filter "*.pdf"` |

## Usage

## Understanding the Three Versions

### Version Comparison

| Feature | Basic | Enhanced | AI-Enhanced |
|---------|-------|----------|-------------|
| **HTML → Markdown** | ✅ | ✅ | ✅ |
| **JSON Output** | ❌ | ✅ | ✅ |
| **HTML Preservation** | ❌ | ✅ | ✅ |
| **Site Index Generation** | ❌ | ✅ | ✅ |
| **Content Graph** | ❌ | ✅ | ✅ |
| **PDF Processing** | ❌ | ❌ | ✅ |
| **AI Document Extraction** | ❌ | ❌ | ✅ |
| **Schema-Based Extraction** | ❌ | ❌ | ✅ |
| **Cost** | Free | Free | API costs apply |

### When to Use Each Version

#### 🟢 Use **Basic** (`universal-scraper.py`) when:
- You just need clean Markdown files
- Scraping simple HTML documentation
- No budget for API calls
- Quick one-time conversion

#### 🟡 Use **Enhanced** (`universal-scraper-enhanced.py`) when:
- Building knowledge graphs or databases
- Need structured JSON output
- Want to preserve original HTML
- Creating LLM training datasets
- Using with Rama or graph databases

#### 🔴 Use **AI-Enhanced** (`universal-scraper-ai-enhanced.py`) when:
- Processing research papers with complex layouts
- Extracting data from PDFs and technical documents
- Need precise table and figure extraction
- Working with financial or legal documents
- Require schema-based field extraction

### Basic Usage Examples

## Step-by-Step Usage Guide

### Scenario 1: Simple Documentation Backup
**Goal**: Convert HTML docs to clean Markdown files

```bash
# Step 1: Use the basic scraper
python universal-scraper.py --url https://docs.example.com/

# Result: Clean Markdown files in auto-generated directory
```

### Scenario 2: Building a Knowledge Graph
**Goal**: Create structured JSON for database integration

```bash
# Step 1: Use enhanced scraper with JSON output
python universal-scraper-enhanced.py \
  --url https://docs.example.com/ \
  --formats json \
  --include-metadata

# Step 2: Use the generated files
# - site_index.json: Complete site structure
# - content_graph.json: Node/edge relationships
# - json/*.json: Structured page content
```

### Scenario 3: Research Paper Processing
**Goal**: Extract structured data from academic papers

```bash
# Step 1: Get Landing.ai API key (free tier available)
# Visit: https://docs.landing.ai/ade/agentic-api-key
export VISION_AGENT_API_KEY=your-key-here

# Step 2: Install AI dependencies
pip install agentic-doc

# Step 3: Run AI-enhanced scraper
python universal-scraper-ai-enhanced.py \
  --url https://arxiv.org/papers/ \
  --formats json,md \
  --landing-ai \
  --landing-ai-schema research_paper

# Result: 
# - Regular HTML pages → Markdown/JSON (free)
# - PDF papers → AI-processed with extracted figures, equations, references
```

### Scenario 4: Cost-Optimized Mixed Processing
**Goal**: Use AI only for complex documents, HTML parsing for regular pages

```bash
# Process only PDFs with Landing.ai, everything else with standard parsing
python universal-scraper-ai-enhanced.py \
  --url https://docs.example.com/ \
  --formats md,json \
  --landing-ai \
  --landing-ai-filter "*.pdf" \
  --include-metadata

# Cost: Only pay for PDF processing, HTML pages are free
```

### Scenario 5: Custom Data Extraction
**Goal**: Extract specific fields using custom schema

```bash
# Step 1: Create your schema (see schemas/ directory for examples)
# Step 2: Run with custom schema
python universal-scraper-ai-enhanced.py \
  --url https://docs.example.com/ \
  --landing-ai \
  --landing-ai-schema ./my-custom-schema.json
```

## Complete Examples by Use Case

### Academic Research
```bash
# Extract structured data from research papers
python universal-scraper-ai-enhanced.py \
  --url https://arxiv.org/papers/ \
  --formats json \
  --landing-ai \
  --landing-ai-schema research_paper \
  --output academic_papers
```

### Technical Documentation
```bash
# Process API docs and technical manuals
python universal-scraper-ai-enhanced.py \
  --url https://docs.kubernetes.io/ \
  --formats md,json \
  --landing-ai \
  --landing-ai-schema technical_manual \
  --landing-ai-filter "*.pdf,*.docx"
```

### Financial Document Processing
```bash
# Extract data from financial documents
python universal-scraper-ai-enhanced.py \
  --url https://investor-docs.company.com/ \
  --formats json \
  --landing-ai \
  --landing-ai-schema financial_document
```

### Rama Database Integration
```bash
# Create structured data streams for Rama
python universal-scraper-enhanced.py \
  --url https://docs.example.com/ \
  --formats json \
  --include-metadata \
  --output rama_data_source

# Use the JSON files to populate Rama depots
# site_index.json provides the complete data model
```

### Command Line Options

#### AI-Enhanced Scraper (universal-scraper-ai-enhanced.py)

| Option | Description | Default |
|--------|-------------|---------|
| `--url` | Base URL to start scraping (required) | None |
| `--output` | Output directory name | Auto-generated from URL |
| `--formats` | Output formats (comma-separated: md,json,html) | md |
| `--include-metadata` | Extract enhanced metadata | False |
| `--landing-ai` | Enable Landing.ai processing | False |
| `--landing-ai-schema` | Schema: research_paper, technical_manual, financial_document, or path to JSON | None |
| `--landing-ai-filter` | File patterns to process with Landing.ai | *.pdf |
| `--delay` | Delay between requests in seconds | 1.0 |
| `--user-agent` | Custom User-Agent string | Documentation-Scraper/1.0 |
| `--skip-robots` | Skip robots.txt checking | False |

#### Enhanced Scraper (universal-scraper-enhanced.py)

| Option | Description | Default |
|--------|-------------|---------|
| `--url` | Base URL to start scraping (required) | None |
| `--output` | Output directory name | Auto-generated from URL |
| `--formats` | Output formats (comma-separated: md,json,html) | md |
| `--include-metadata` | Extract enhanced metadata | False |
| `--delay` | Delay between requests in seconds | 1.0 |
| `--user-agent` | Custom User-Agent string | Documentation-Scraper/1.0 |
| `--skip-robots` | Skip robots.txt checking | False |

#### Original Scraper (universal-scraper.py)

| Option | Description | Default |
|--------|-------------|---------| 
| `--url` | Base URL to start scraping (required) | None |
| `--output` | Output directory name | Auto-generated from URL |
| `--delay` | Delay between requests in seconds | 1.0 |
| `--user-agent` | Custom User-Agent string | Documentation-Scraper/1.0 |
| `--skip-robots` | Skip robots.txt checking | False |

## Output Structure

### Enhanced Scraper Output

```
output_directory/
├── markdown/           # Markdown files (if --formats includes 'md')
│   ├── index.md
│   └── subfolder/
│       └── page.md
├── json/              # JSON files (if --formats includes 'json')
│   ├── index.json
│   └── subfolder/
│       └── page.json
├── html/              # HTML files (if --formats includes 'html')
│   ├── index.html
│   └── subfolder/
│       └── page.html
├── images/            # All downloaded images
├── site_index.json    # Complete site structure and metadata
├── content_graph.json # Node/edge graph of content relationships
└── scraper.log        # Detailed scraping log
```

### JSON Output Format

Each JSON file contains:

```json
{
  "metadata": {
    "url": "https://example.com/page",
    "title": "Page Title",
    "description": "Page description",
    "keywords": ["keyword1", "keyword2"],
    "author": "Author Name",
    "og_data": {...},
    "extracted_at": "2025-08-26T10:00:00Z"
  },
  "content": {
    "sections": [
      {
        "id": "section-0",
        "type": "heading",
        "level": 1,
        "text": "Main Title"
      },
      {
        "id": "section-1",
        "type": "paragraph",
        "text": "Content text...",
        "links": [{"text": "link", "href": "/path"}]
      }
    ],
    "code_blocks": [
      {
        "id": "code-0",
        "language": "python",
        "content": "def example():..."
      }
    ],
    "tables": [...],
    "images": [...],
    "links": {
      "internal": [...],
      "external": [...]
    }
  }
}
```

## Features in Detail

### Multi-Format Output Benefits

**JSON Format** - Perfect for:
- Building knowledge graphs and semantic networks
- Integration with databases (PostgreSQL, MongoDB, etc.)
- Feeding data to LLMs with structured context
- Integration with Rama for infinitely composable backends
- Creating searchable indexes with Elasticsearch/Solr

**HTML Format** - Essential for:
- Preserving exact formatting and styling
- Capturing JavaScript-rendered content
- Maintaining complex layouts and interactions
- Debugging scraping issues
- Creating offline mirrors

**Markdown Format** - Ideal for:
- Human-readable documentation archives
- Version control and change tracking
- Static site generators (Jekyll, Hugo)
- LLM fine-tuning datasets
- Wiki imports

### Content Extraction
- Extracts main content areas intelligently
- Creates hierarchical JSON structure with IDs
- Preserves heading hierarchy (H1-H6)
- Maintains code blocks with language detection
- Converts HTML tables to structured data
- Preserves lists with proper nesting
- Extracts all internal and external links

### Metadata Extraction (--include-metadata)
- Page title and description
- Keywords and author information
- OpenGraph data (og:title, og:image, etc.)
- Last modified timestamps
- Custom meta tags
- Social media metadata

### Site Analysis Features
- **site_index.json**: Complete inventory of all pages
- **content_graph.json**: Node/edge representation for graph databases
- Link relationship mapping
- Content hierarchy visualization
- Page interconnection analysis

### Image Handling
- Downloads all images to shared `images/` folder
- Updates paths in all output formats
- Handles data URIs (base64 encoded images)
- Generates unique names for unnamed images
- Preserves image metadata (alt text, dimensions)

### Link Discovery
- Follows all internal links automatically
- Maps relationships between pages
- Ignores external links to stay within documentation
- Skips non-documentation files (PDFs, ZIPs, etc.)
- Handles pagination ("Next", "Older Posts" links)

### Math Formula Support
- Attempts to extract LaTeX source from MathJax/KaTeX
- Preserves formulas in JSON structure
- Falls back to image representation for complex formulas
- Maintains inline and display math formatting

## Troubleshooting

### Common Issues

1. **"robots.txt disallows scraping"**
   - The website's robots.txt prevents scraping
   - Use `--skip-robots` flag (ensure you have permission)

2. **"Error fetching URL"**
   - Check your internet connection
   - The website might be down
   - Try increasing the delay with `--delay 2.0`

3. **Missing Content**
   - Some sites use JavaScript to load content dynamically
   - This scraper works best with static HTML content
   - Consider using Selenium-based scrapers for JS-heavy sites

4. **Rate Limiting**
   - If you get 429 errors, increase the delay
   - Some sites have strict rate limits

### Log Files

Check `scraper.log` in the output directory for detailed information about:
- Pages visited
- Errors encountered
- Images downloaded
- Links discovered

## Best Practices

1. **Respect robots.txt**: Always check if scraping is allowed
2. **Use appropriate delays**: Don't overwhelm the server
3. **Check terms of service**: Ensure you're allowed to scrape
4. **Be selective**: Use specific documentation URLs rather than entire domains
5. **Monitor progress**: Watch the console output for any issues

## Limitations

- Works best with static HTML documentation
- May not capture JavaScript-rendered content
- Some dynamic navigation might be missed
- Complex authentication is not supported

## Advanced Features Deep Dive\n\n### Landing.ai Integration Benefits\n\n**What Landing.ai Adds:**\n- **Layout-Agnostic Parsing**: Extracts data from complex PDF layouts without templates\n- **Element Detection**: Identifies text, tables, forms, checkboxes, equations, code blocks\n- **Hierarchical Relationships**: Understands how elements relate (captions to figures)\n- **Visual Grounding**: Provides exact coordinates for each extracted element\n- **Precision Extraction**: High accuracy even with complex document structures\n\n**When Landing.ai is Worth the Cost:**\n- Research papers with mathematical equations and complex figures\n- Technical manuals with diagrams and code examples\n- Financial documents with structured tables and forms\n- Legal documents requiring precise extraction and verification\n- Any PDF where layout and visual relationships matter\n\n**When to Skip Landing.ai:**\n- Simple HTML documentation (use basic/enhanced versions)\n- Plain text content without complex layouts\n- Budget constraints for large-scale scraping\n- Already well-structured data sources\n\n### Schema System Explained\n\n**Built-in Schemas:**\n- `research_paper`: Extracts titles, authors, abstracts, figures, equations, references\n- `technical_manual`: Gets installation steps, API endpoints, code examples, troubleshooting\n- `financial_document`: Pulls invoice data, line items, totals, payment information\n\n**Custom Schemas:**\nCreate JSON schemas to extract exactly the fields you need:\n```json\n{\n  \"type\": \"object\",\n  \"properties\": {\n    \"product_name\": {\n      \"type\": \"string\",\n      \"description\": \"Name of the product\"\n    },\n    \"specifications\": {\n      \"type\": \"array\",\n      \"items\": {\"type\": \"string\"}\n    }\n  }\n}\n```\n\n### Cost Optimization Strategies\n\n**1. Selective Processing**\n```bash\n# Only process PDFs with AI, everything else free\n--landing-ai-filter \"*.pdf\"\n```\n\n**2. Batch Processing**\n```bash\n# Process multiple related documents in one session\n--url https://docs.example.com/research-papers/\n```\n\n**3. Schema Reuse**\n```bash\n# Use the same schema for similar document types\n--landing-ai-schema research_paper\n```\n\n### Integration with Rama and Knowledge Graphs\n\n**Rama Integration Workflow:**\n1. **Data Ingestion**: JSON output streams directly to Rama depots\n2. **Graph Modeling**: Content relationships map to Rama's graph topology\n3. **Query Capabilities**: Hierarchical sections enable complex PState queries\n4. **Temporal Tracking**: Metadata supports time-based data modeling\n\n**Knowledge Graph Construction:**\n- **Nodes**: Pages, sections, entities from extracted content\n- **Edges**: Links, references, semantic relationships\n- **Properties**: All metadata and extracted fields as node properties\n- **Graph Export**: Compatible with Neo4j, NetworkX, and other graph databases\n\n**LLM Training and RAG Systems:**\n- **Clean Training Data**: Structured JSON provides consistent format\n- **Context Preservation**: Hierarchical content improves understanding\n- **Retrieval Enhancement**: Metadata improves search accuracy\n- **Multi-Modal Support**: Links between text, images, and extracted data"}

## Example Outputs\n\n### Basic Scraper Output\n```\nUniversal Documentation Scraper\nTarget URL: https://docs.example.com/\nOutput directory: docs_example_com\nStarting crawl from: https://docs.example.com/\n[1] Visiting: https://docs.example.com/\n  Saved content to: docs_example_com/index.md\n==================================================\nScraping complete!\nTotal pages visited: 25\nOutput saved to: docs_example_com\n==================================================\n```\n\n### Enhanced Scraper Output\n```\nUniversal Documentation Scraper - Enhanced Edition\nTarget URL: https://docs.example.com/\nOutput formats: json, md\nInclude metadata: True\n[1] Visiting: https://docs.example.com/\n  Saved JSON to: docs_example_com/json/index.json\n  Saved Markdown to: docs_example_com/markdown/index.md\nSaved site index to: docs_example_com/site_index.json\nSaved content graph to: docs_example_com/content_graph.json\n==================================================\nScraping complete!\nTotal pages visited: 45\nTotal unique images downloaded: 123\nFormats generated: json, md\n==================================================\n```\n\n### AI-Enhanced Scraper Output\n```\nAI-Enhanced Universal Documentation Scraper\nTarget URL: https://research.example.com/papers/\nLanding.ai enabled: True\nLanding.ai schema: research_paper\n[1] Visiting: https://research.example.com/papers/\n  Saved JSON to: research_papers/json/index.json\n  Downloaded document: paper1.pdf\n  Processing with Landing.ai: paper1.pdf\n  Landing.ai processing complete: 12 pages\n==================================================\nAI-Enhanced Scraping Complete!\nTotal pages visited: 30\nTotal images downloaded: 89\nDocuments processed with Landing.ai: 15\nEstimated Landing.ai cost: $0.15\nOutput saved to: research_papers\n==================================================\n```"}

## Decision Tree: Which Version Should I Use?\n\n```\nStart Here: What do you want to achieve?\n\n┌─ Simple HTML → Markdown conversion?\n│  └─ Use: universal-scraper.py (Basic)\n│     Cost: Free\n│\n├─ Building knowledge graphs or databases?\n│  └─ Use: universal-scraper-enhanced.py (Enhanced)\n│     Cost: Free\n│     Output: JSON + Markdown + HTML\n│\n├─ Processing complex documents (PDFs, research papers)?\n│  ├─ Budget available for API calls?\n│  │  ├─ Yes → Use: universal-scraper-ai-enhanced.py\n│  │  │        Cost: ~$0.01 per page processed\n│  │  │        Output: AI-extracted structured data\n│  │  └─ No  → Use: universal-scraper-enhanced.py\n│  │           Cost: Free (but limited PDF processing)\n│  │\n│  └─ Mixed content (some PDFs, mostly HTML)?\n│      └─ Use: universal-scraper-ai-enhanced.py with --landing-ai-filter \"*.pdf\"\n│         Cost: Pay only for PDF processing\n│\n└─ Not sure? Start with Enhanced version:\n   python universal-scraper-enhanced.py --url YOUR_URL --formats json,md\n   (You can always upgrade to AI-enhanced later)\n```\n\n## FAQ\n\n**Q: Do I need a Landing.ai API key to use the scraper?**\nA: Only for the AI-enhanced version. The basic and enhanced versions work without any API keys.\n\n**Q: How much does Landing.ai cost?**\nA: Approximately $0.01 per page processed. The scraper shows estimated costs in real-time.\n\n**Q: Can I use the AI features for free?**\nA: Landing.ai offers free tier credits. Check their pricing page for current limits.\n\n**Q: What if I have a large site with thousands of PDFs?**\nA: Use the `--landing-ai-filter` option to process only specific file types, or process in batches.\n\n**Q: Can I create my own extraction schemas?**\nA: Yes! Create a JSON schema file and use `--landing-ai-schema path/to/your/schema.json`\n\n**Q: Is this compatible with Rama?**\nA: Yes! The enhanced and AI-enhanced versions generate JSON output specifically designed for Rama integration.\n\n**Q: Can I pause and resume scraping?**\nA: Not currently, but the scraper skips already-processed files if you re-run it.\n\n## License\n\nThis scraper is provided as-is for educational and personal use. Always respect website terms of service and copyright when scraping content.\n\n## Support\n\nFor questions and support:\n- Basic usage issues: Check the troubleshooting section above\n- Landing.ai specific: Visit [Landing.ai Documentation](https://docs.landing.ai/ade/)\n- Rama integration: See [Rama Documentation](https://redplanetlabs.com/)\n\n---\n\n**Ready to start scraping?** Pick your version and run your first command! 🚀