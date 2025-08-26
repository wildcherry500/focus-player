# Visual Processing Workflow Guide

## How Complex Documents Are Processed (ArXiv Example)

When you run the AI-enhanced scraper on a research paper like `https://arxiv.org/html/2508.15760v1`, here's what happens:

### Step 1: Document Discovery
```bash
# Scraper visits the HTML page
[1] Visiting: https://arxiv.org/html/2508.15760v1
  ✓ Standard HTML parsing (FREE)
  ✓ Extracted: Title, Abstract, Authors, References
  ✓ Searching for PDFs to process with AI...
```

### Step 2: AI Processing Triggers
```python
# When PDFs are found:
if url.endswith('.pdf') and landing_ai_enabled:
    # Download PDF to documents/ folder
    local_pdf = download_document(pdf_url)
    
    # Process with Landing.ai
    result = landing_ai.parse(local_pdf, schema=research_paper)
    
    # Extract complex visuals:
    # - Flowcharts with text extraction
    # - Data charts with axis labels
    # - Mathematical equations 
    # - Figure-caption relationships
```

### Step 3: Flowchart Processing Example

When Landing.ai processes a flowchart, it identifies:

```json
{
  "figures": [
    {
      "figure_number": "1", 
      "caption": "System Architecture Flowchart",
      "figure_type": "flowchart",
      "visual_elements": [
        {
          "element_type": "process_box",
          "text": "Data Input Module",
          "coordinates": {"x": 100, "y": 150, "width": 120, "height": 40}
        },
        {
          "element_type": "decision_diamond",
          "text": "Validation Check", 
          "coordinates": {"x": 180, "y": 250, "width": 80, "height": 60}
        },
        {
          "element_type": "arrow",
          "connects": ["Data Input Module", "Validation Check"]
        }
      ],
      "extracted_workflow": "Data Input → Validation → Processing → Output",
      "grounding": {
        "page": 1,
        "bounding_box": {"left": 0.1, "top": 0.2, "right": 0.8, "bottom": 0.6}
      }
    }
  ]
}
```

### Step 4: Landing.ai Visual Analysis Pipeline

```
PDF Document → Landing.ai Processing:

┌─ Layout Analysis ────────────────────┐
│ • Identifies visual blocks           │
│ • Separates text from graphics       │
│ • Detects figure boundaries          │
└─────────────────────────────────────┘
         ↓
┌─ Element Classification ─────────────┐
│ • Flowchart: Detects boxes, arrows  │
│ • Bar Chart: Identifies axes, bars  │
│ • Table: Recognizes rows/columns    │
│ • Equation: LaTeX/mathematical text │
└─────────────────────────────────────┘
         ↓
┌─ Relationship Mapping ──────────────┐
│ • Links captions to figures         │
│ • Associates text with visuals      │
│ • Maintains reading order           │
└─────────────────────────────────────┘
         ↓
┌─ Content Extraction ────────────────┐
│ • Extracts text within flowchart    │
│ • Reads chart data points           │
│ • Preserves visual structure        │
└─────────────────────────────────────┘
```

### Step 5: Cost-Optimized Hybrid Result

```
Final Output Structure:
├── HTML Content (FREE processing)
│   ├── json/html_2508.json - Structured page content
│   ├── markdown/html_2508.md - Clean readable format
│   └── site_index.json - Site structure
│
└── PDF Content (AI processing - ~$0.01/page)
    ├── documents/paper.pdf - Downloaded original
    ├── landing_ai_processed/ - AI extraction results
    └── Enhanced JSON with visual elements
```

### Step 6: Integration Ready Output

The combined result gives you:
- **Text Content**: Abstracts, references, methodology (from HTML)
- **Visual Content**: Flowcharts, charts, equations (from PDF AI processing)
- **Relationships**: Figure captions linked to visuals
- **Coordinates**: Exact positions for compliance tracking
- **Structured Data**: Ready for Rama, knowledge graphs, or databases

## API Key Setup and Testing

### Set Your API Key
```bash
# Get free API key: https://docs.landing.ai/ade/agentic-api-key
export VISION_AGENT_API_KEY=your-api-key-here

# Verify it's set
python -c "import os; print('API Key:', os.getenv('VISION_AGENT_API_KEY', 'NOT SET'))"
```

### Test with ArXiv Paper
```bash
# Run the test (will process HTML for free, PDFs with AI)
python universal-scraper-ai-enhanced.py \
  --url https://arxiv.org/html/2508.15760v1 \
  --landing-ai \
  --landing-ai-schema research_paper \
  --landing-ai-filter "*.pdf" \
  --formats json,md \
  --output arxiv_test
```

### Expected Output
```
AI-Enhanced Universal Documentation Scraper
Target URL: https://arxiv.org/html/2508.15760v1
Landing.ai enabled: True
Landing.ai schema: research_paper

[1] Visiting: https://arxiv.org/html/2508.15760v1
  ✓ Saved JSON to: arxiv_test/json/html_2508.json
  ✓ Saved Markdown to: arxiv_test/markdown/html_2508.md
  
  ✓ Downloaded document: paper.pdf
  ✓ Processing with Landing.ai: paper.pdf
  ✓ Landing.ai processing complete: 8 pages
  ✓ Extracted: 3 figures, 2 tables, 12 equations

==================================================
AI-Enhanced Scraping Complete!
Total pages visited: 1
Documents processed with Landing.ai: 1
Estimated Landing.ai cost: $0.08
Output saved to: arxiv_test
==================================================
```

## What Makes This Powerful for Research Papers

### Traditional Scraping vs AI-Enhanced

**Traditional HTML Scraping:**
- ✓ Gets title, abstract, authors, references
- ✗ Misses complex visual content
- ✗ Can't extract from PDFs
- ✗ No understanding of figure relationships

**AI-Enhanced Processing:**
- ✓ Everything from traditional scraping
- ✓ Extracts text from within flowcharts
- ✓ Identifies chart data and trends
- ✓ Links captions to figures
- ✓ Provides exact coordinates for compliance
- ✓ Understands mathematical equations
- ✓ Preserves document structure and relationships

### Perfect for Rama Integration

The structured JSON output maps directly to Rama's data modeling capabilities:

```clojure
; Example Rama depot structure from scraped paper
(def paper-depot
  {:title "LiveMCP-101: Stress Testing..."
   :authors ["Author 1" "Author 2"]
   :figures [{:type :flowchart
              :elements [{:type :process-box
                         :text "Data Input"
                         :coords [100 150 120 40]}]}]
   :relationships [{:source "Figure 1"
                   :target "Section 2.1"
                   :type :illustrates}]})
```

This enables complex queries like "Find all papers with system architecture flowcharts" or "Show relationships between figures and methodology sections."