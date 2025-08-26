import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import time
import re
import base64
import logging
import argparse
from urllib.robotparser import RobotFileParser
import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from typing import Optional, List, Union

# Landing.ai integration (optional import)
try:
    from agentic_doc.parse import parse as landing_parse
    LANDING_AI_AVAILABLE = True
except ImportError:
    LANDING_AI_AVAILABLE = False
    landing_parse = None

# --- Setup Logging ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# --- Helper Functions ---

def sanitize_filename(url):
    """Creates a valid filename from a URL."""
    parsed_url = urlparse(url)
    path = parsed_url.path.strip('/').replace('~/', '')
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', path)
    
    if not filename or filename.endswith('/'):
        filename += 'index'
    
    if '.' in filename and filename.rfind('.') > filename.rfind('/'):
        filename = filename[:filename.rfind('.')]
    
    return filename

def extract_math_latex(soup_tag):
    """Extract LaTeX from MathJax/KaTeX elements."""
    if soup_tag.name == 'script' and 'type' in soup_tag.attrs and 'math/tex' in soup_tag['type']:
        return f"$${soup_tag.string}$$\n" if soup_tag.string else ""
    
    if soup_tag.name == 'span' and ('class' in soup_tag.attrs and ('math' in soup_tag['class'] or 'katex' in soup_tag['class'])):
        if 'data-latex' in soup_tag.attrs:
            return f"$${soup_tag['data-latex']}$$\n"
        if soup_tag.string and soup_tag.string.strip():
            return f"${soup_tag.string.strip()}$"
    
    if soup_tag.name == 'img' and ('class' in soup_tag.attrs and 'math' in soup_tag['class']):
        return f"![Mathematical formula]({soup_tag.get('src', '')})\n"
    
    return None

def check_robots_txt(base_url, user_agent='Documentation-Scraper/1.0'):
    """Check robots.txt for scraping permission."""
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        
        can_fetch = rp.can_fetch(user_agent, base_url)
        crawl_delay = rp.crawl_delay(user_agent) or rp.crawl_delay("*")
        
        return can_fetch, crawl_delay
    except Exception as e:
        logger.warning(f"Could not check robots.txt: {e}")
        return True, None

def detect_project_type(url, parsed_url):
    """Detect the type of project based on URL patterns."""
    domain = parsed_url.netloc.lower()
    path = parsed_url.path.lower()
    
    # Research sites
    if any(site in domain for site in ['arxiv.org', 'papers.', 'research.', 'scholar.']):
        return 'research'
    
    # Documentation sites  
    if any(term in path for term in ['/docs/', '/doc/', '/documentation/', '/api/', '/reference/']):
        return 'docs'
    
    # API documentation
    if any(term in path for term in ['/api/', '/swagger/', '/openapi/', '/graphql/']):
        return 'api'
    
    # Blog/articles
    if any(term in path for term in ['/blog/', '/article/', '/post/', '/news/', '/case-studies/']):
        return 'blog'
    
    # Landing pages / marketing
    if any(term in domain for term in ['landing.', 'www.']) and not any(term in path for term in ['/docs/', '/blog/']):
        return 'landing'
    
    # Default to docs for most other cases
    return 'docs'

def extract_content_focus(parsed_url):
    """Extract meaningful content focus from URL path."""
    path = parsed_url.path.strip('/').lower()
    
    if not path or path in ['', 'index', 'home']:
        return 'overview'
    
    # Remove common prefixes and file extensions
    path = re.sub(r'^(docs?|documentation|api|blog|articles?)/?', '', path)
    path = re.sub(r'\.(html?|php|aspx?)$', '', path)
    
    # Take the most meaningful part of the path
    parts = path.split('/')
    if len(parts) >= 2:
        # Use last two parts for focus
        focus = '-'.join(parts[-2:])
    elif len(parts) == 1:
        focus = parts[0]
    else:
        focus = 'overview'
    
    # Clean up and limit length
    focus = re.sub(r'[^a-z0-9-]', '-', focus)
    focus = re.sub(r'-+', '-', focus).strip('-')
    return focus[:20] if focus else 'overview'

def generate_output_dir_from_url(url):
    """Generate a structured, self-documenting directory name from URL."""
    parsed = urlparse(url)
    
    # Detect project type
    project_type = detect_project_type(url, parsed)
    
    # Clean domain name
    domain = parsed.netloc.replace('.', '-').replace('www-', '')
    
    # Extract content focus
    content_focus = extract_content_focus(parsed)
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d')
    
    # Construct directory name
    dir_name = f"scraper-{project_type}_{domain}_{content_focus}_{timestamp}"
    
    # Ensure reasonable length (max 60 chars)
    if len(dir_name) > 60:
        # Truncate content_focus if needed
        excess = len(dir_name) - 60
        content_focus = content_focus[:max(5, len(content_focus) - excess)]
        dir_name = f"scraper-{project_type}_{domain}_{content_focus}_{timestamp}"
    
    return dir_name

def extract_metadata(soup, url):
    """Extract metadata from HTML page."""
    metadata = {
        'url': url,
        'title': None,
        'description': None,
        'keywords': [],
        'author': None,
        'last_modified': None,
        'og_data': {},
        'extracted_at': datetime.utcnow().isoformat() + 'Z'
    }
    
    title_tag = soup.find('title')
    if title_tag and title_tag.string:
        metadata['title'] = title_tag.string.strip()
    
    for meta in soup.find_all('meta'):
        name = meta.get('name', '').lower()
        property_attr = meta.get('property', '').lower()
        content = meta.get('content', '')
        
        if name == 'description':
            metadata['description'] = content
        elif name == 'keywords':
            metadata['keywords'] = [k.strip() for k in content.split(',')]
        elif name == 'author':
            metadata['author'] = content
        elif name == 'last-modified':
            metadata['last_modified'] = content
        elif property_attr.startswith('og:'):
            metadata['og_data'][property_attr] = content
    
    return metadata

def is_complex_document(url, file_extension):
    """Determine if document should be processed with Landing.ai."""
    complex_extensions = ['.pdf', '.docx', '.pptx', '.xlsx']
    return any(url.lower().endswith(ext) or file_extension.lower() == ext for ext in complex_extensions)

def load_schema(schema_path):
    """Load JSON schema for Landing.ai extraction."""
    if not schema_path or not os.path.exists(schema_path):
        return None
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading schema {schema_path}: {e}")
        return None

# --- Default Schemas ---
DEFAULT_SCHEMAS = {
    "research_paper": {
        "type": "object",
        "title": "Research Paper Field Extraction Schema",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "properties": {
            "title": {
                "type": "string",
                "title": "Paper Title",
                "description": "The main title of the research paper."
            },
            "authors": {
                "type": "array",
                "title": "Authors",
                "items": {"type": "string"},
                "description": "List of paper authors."
            },
            "abstract": {
                "type": "string",
                "title": "Abstract",
                "description": "Paper abstract or summary."
            },
            "keywords": {
                "type": "array",
                "title": "Keywords",
                "items": {"type": "string"},
                "description": "Research keywords."
            },
            "figures": {
                "type": "array",
                "title": "Figures",
                "items": {
                    "type": "object",
                    "properties": {
                        "caption": {"type": "string"},
                        "description": {"type": "string"}
                    }
                },
                "description": "Figure captions and descriptions."
            }
        }
    },
    "technical_manual": {
        "type": "object",
        "title": "Technical Manual Field Extraction Schema",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "properties": {
            "title": {
                "type": "string",
                "title": "Manual Title"
            },
            "version": {
                "type": "string",
                "title": "Version"
            },
            "sections": {
                "type": "array",
                "title": "Sections",
                "items": {
                    "type": "object",
                    "properties": {
                        "heading": {"type": "string"},
                        "content": {"type": "string"}
                    }
                }
            },
            "code_blocks": {
                "type": "array",
                "title": "Code Examples",
                "items": {
                    "type": "object",
                    "properties": {
                        "language": {"type": "string"},
                        "code": {"type": "string"}
                    }
                }
            }
        }
    }
}

# --- Main Scraper Logic ---

class AIEnhancedDocsScraper:
    def __init__(self, base_url, output_dir, delay, user_agent='Documentation-Scraper/1.0', 
                 formats=['md'], include_metadata=False, landing_ai_enabled=False,
                 landing_ai_schema=None, landing_ai_filter=None):
        self.base_url = base_url
        self.output_dir = output_dir
        self.delay = delay
        self.user_agent = user_agent
        self.formats = formats
        self.include_metadata = include_metadata
        self.landing_ai_enabled = landing_ai_enabled and LANDING_AI_AVAILABLE
        self.landing_ai_schema = landing_ai_schema
        self.landing_ai_filter = landing_ai_filter or "*.pdf"
        
        if landing_ai_enabled and not LANDING_AI_AVAILABLE:
            logger.warning("Landing.ai requested but agentic-doc not installed. Install with: pip install agentic-doc")
            self.landing_ai_enabled = False
        
        # Parse base URL to get root path
        parsed = urlparse(base_url)
        self.base_netloc = parsed.netloc
        self.docs_root_path = parsed.path
        
        # Setup directories based on formats
        self.dirs = {}
        if 'md' in formats:
            self.dirs['md'] = os.path.join(output_dir, 'markdown')
            os.makedirs(self.dirs['md'], exist_ok=True)
        if 'json' in formats:
            self.dirs['json'] = os.path.join(output_dir, 'json')
            os.makedirs(self.dirs['json'], exist_ok=True)
        if 'html' in formats:
            self.dirs['html'] = os.path.join(output_dir, 'html')
            os.makedirs(self.dirs['html'], exist_ok=True)
        
        # Landing.ai specific directories
        if self.landing_ai_enabled:
            self.dirs['landing_ai'] = os.path.join(output_dir, 'landing_ai_processed')
            os.makedirs(self.dirs['landing_ai'], exist_ok=True)
        
        self.images_dir = os.path.join(output_dir, "images")
        self.documents_dir = os.path.join(output_dir, "documents")
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.documents_dir, exist_ok=True)
        
        self.visited_urls = set()
        self.to_visit_queue = []
        self.downloaded_images = set()
        self.downloaded_documents = set()
        self.landing_ai_processed = set()
        self.total_pages = 0
        self.landing_ai_costs = 0.0  # Track estimated costs
        
        # For site index and graph generation
        self.site_structure = {
            'metadata': {
                'base_url': base_url,
                'scrape_start': datetime.utcnow().isoformat() + 'Z',
                'total_pages': 0,
                'total_images': 0,
                'landing_ai_enabled': self.landing_ai_enabled,
                'landing_ai_processed_count': 0
            },
            'pages': [],
            'link_graph': defaultdict(list)
        }
        
        # Request headers
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set up file handler for logging
        file_handler = logging.FileHandler(os.path.join(self.output_dir, 'scraper.log'))
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    def download_document(self, doc_url, local_doc_path):
        """Download document (PDF, etc.) for Landing.ai processing."""
        if doc_url in self.downloaded_documents:
            logger.info(f"  Document already downloaded: {doc_url}")
            return local_doc_path
        
        try:
            response = requests.get(doc_url, stream=True, timeout=15, headers=self.headers)
            response.raise_for_status()
            with open(local_doc_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.downloaded_documents.add(doc_url)
            logger.info(f"  Downloaded document: {doc_url} to {local_doc_path}")
            return local_doc_path
        except Exception as e:
            logger.error(f"  Error downloading document {doc_url}: {e}")
            return None

    def process_with_landing_ai(self, file_path):
        """Process document with Landing.ai API."""
        if not self.landing_ai_enabled:
            return None
        
        try:
            logger.info(f"  Processing with Landing.ai: {file_path}")
            
            # Load schema if provided
            schema = None
            if self.landing_ai_schema:
                if os.path.exists(self.landing_ai_schema):
                    schema = load_schema(self.landing_ai_schema)
                elif self.landing_ai_schema in DEFAULT_SCHEMAS:
                    schema = DEFAULT_SCHEMAS[self.landing_ai_schema]
            
            # Process with Landing.ai
            if schema:
                results = landing_parse(file_path, extraction_schema=schema)
            else:
                results = landing_parse(file_path)
            
            if results:
                # Estimate cost (rough approximation: $0.01 per page)
                self.landing_ai_costs += 0.01 * len(results)
                self.landing_ai_processed.add(file_path)
                logger.info(f"  Landing.ai processing complete: {len(results)} pages")
                return results
        
        except Exception as e:
            logger.error(f"  Landing.ai processing failed for {file_path}: {e}")
        
        return None

    def download_image(self, img_url, local_image_path):
        """Download image locally."""
        if img_url in self.downloaded_images:
            return local_image_path
        
        try:
            if img_url.startswith('data:'):
                match = re.match(r'data:image/(\w+);base64,(.*)', img_url)
                if match:
                    img_data = base64.b64decode(match.group(2))
                    with open(local_image_path, 'wb') as f:
                        f.write(img_data)
                    self.downloaded_images.add(img_url)
                    return local_image_path
                return None
            
            response = requests.get(img_url, stream=True, timeout=10, headers=self.headers)
            response.raise_for_status()
            with open(local_image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.downloaded_images.add(img_url)
            logger.info(f"  Downloaded image: {img_url} to {local_image_path}")
            return local_image_path
        except Exception as e:
            logger.error(f"  Error downloading image {img_url}: {e}")
            return None

    def _get_page_content(self, url):
        """Fetch HTML content from URL."""
        if url in self.visited_urls:
            return None
        
        self.total_pages += 1
        logger.info(f"[{self.total_pages}] Visiting: {url}")
        self.visited_urls.add(url)
        
        try:
            response = requests.get(url, timeout=15, headers=self.headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"  Error fetching {url}: {e}")
            return None
        finally:
            time.sleep(self.delay)

    def _extract_structured_content(self, soup, url):
        """Extract content in structured format for JSON output."""
        structured_content = {
            'sections': [],
            'images': [],
            'tables': [],
            'code_blocks': [],
            'documents': [],
            'links': {'internal': [], 'external': []},
            'landing_ai_processed': []
        }
        
        # Find main content area
        content_div = (soup.find('div', class_=lambda x: x and ('main-content' in x or 'page-content' in x)) or
                      soup.find('article') or soup.find('main') or soup.find('body'))
        
        if content_div:
            section_id = 0
            
            for element in content_div.find_all(True):
                # Headings
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    structured_content['sections'].append({
                        'id': f'section-{section_id}',
                        'type': 'heading',
                        'level': int(element.name[1]),
                        'text': element.get_text(strip=True),
                        'html_id': element.get('id', '')
                    })
                    section_id += 1
                
                # Paragraphs
                elif element.name == 'p':
                    para_content = {
                        'id': f'section-{section_id}',
                        'type': 'paragraph',
                        'text': element.get_text(strip=True),
                        'links': []
                    }
                    
                    for link in element.find_all('a', href=True):
                        para_content['links'].append({
                            'text': link.get_text(strip=True),
                            'href': link.get('href')
                        })
                    
                    if para_content['text']:
                        structured_content['sections'].append(para_content)
                        section_id += 1
                
                # Code blocks
                elif element.name == 'pre':
                    code_element = element.find('code')
                    language = 'text'
                    if code_element:
                        lang_classes = code_element.get('class', [])
                        for cls in lang_classes:
                            if cls.startswith('language-'):
                                language = cls.replace('language-', '')
                                break
                    
                    structured_content['code_blocks'].append({
                        'id': f'code-{len(structured_content["code_blocks"])}',
                        'language': language,
                        'content': element.get_text(strip=False)
                    })
                
                # Tables
                elif element.name == 'table':
                    table_data = {
                        'id': f'table-{len(structured_content["tables"])}',
                        'headers': [th.get_text(strip=True) for th in element.find_all('th')],
                        'rows': []
                    }
                    
                    for tr in element.find_all('tr'):
                        row_data = [td.get_text(strip=True) for td in tr.find_all('td')]
                        if row_data:
                            table_data['rows'].append(row_data)
                    
                    if table_data['headers'] or table_data['rows']:
                        structured_content['tables'].append(table_data)
                
                # Images
                elif element.name == 'img':
                    img_data = {
                        'src': element.get('src', ''),
                        'alt': element.get('alt', ''),
                        'title': element.get('title', ''),
                        'width': element.get('width', ''),
                        'height': element.get('height', '')
                    }
                    if img_data['src']:
                        structured_content['images'].append(img_data)
        
        # Extract all links and check for documents
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            absolute_url = urljoin(url, href)
            parsed = urlparse(absolute_url)
            
            if parsed.netloc == self.base_netloc:
                structured_content['links']['internal'].append(absolute_url)
                
                # Check if this is a document that should be processed with Landing.ai
                if self.landing_ai_enabled and is_complex_document(absolute_url, ''):
                    doc_name = os.path.basename(parsed.path) or f"document_{len(structured_content['documents'])}.pdf"
                    local_doc_path = os.path.join(self.documents_dir, doc_name)
                    
                    # Download and process document
                    downloaded_path = self.download_document(absolute_url, local_doc_path)
                    if downloaded_path:
                        landing_ai_result = self.process_with_landing_ai(downloaded_path)
                        structured_content['documents'].append({
                            'url': absolute_url,
                            'local_path': downloaded_path,
                            'processed_with_landing_ai': landing_ai_result is not None,
                            'landing_ai_result': landing_ai_result[0].__dict__ if landing_ai_result else None
                        })
                        
                        if landing_ai_result:
                            structured_content['landing_ai_processed'].append({
                                'document': absolute_url,
                                'chunks': len(landing_ai_result[0].chunks) if landing_ai_result else 0,
                                'markdown_length': len(landing_ai_result[0].markdown) if landing_ai_result else 0
                            })
            else:
                structured_content['links']['external'].append(absolute_url)
        
        return structured_content

    def _save_json(self, url, soup, structured_content, output_path):
        """Save content in JSON format."""
        json_data = {
            'metadata': extract_metadata(soup, url) if self.include_metadata else {'url': url},
            'content': structured_content,
            'scrape_info': {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'scraper_version': '2.0',
                'landing_ai_enabled': self.landing_ai_enabled,
                'landing_ai_processed_docs': len(structured_content.get('landing_ai_processed', []))
            }
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            logger.info(f"  Saved JSON to: {output_path}")
        except Exception as e:
            logger.error(f"  Error saving JSON {output_path}: {e}")

    def _save_html(self, html_content, output_path):
        """Save original HTML content."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"  Saved HTML to: {output_path}")
        except Exception as e:
            logger.error(f"  Error saving HTML {output_path}: {e}")

    def _save_markdown(self, url, soup, output_path):
        """Save content in Markdown format."""
        markdown_lines = ["\n\n"]
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            markdown_lines.append(f"# {title_tag.string.strip()}\n\n")
        else:
            markdown_lines.append(f"# {sanitize_filename(url).replace('_', ' ').title()}\n\n")
        
        # Standard markdown processing (existing logic)
        content_div = (soup.find('div', class_=lambda x: x and ('main-content' in x or 'page-content' in x)) or
                      soup.find('article') or soup.find('main') or soup.find('body'))
        
        if content_div:
            for element in content_div.find_all(True):
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    markdown_lines.append(f"{'#' * int(element.name[1])} {element.get_text(strip=True)}\n\n")
                elif element.name == 'p':
                    paragraph_content = []
                    for child in element.children:
                        if child.name in ['script', 'span', 'img']:
                            latex = extract_math_latex(child)
                            if latex:
                                paragraph_content.append(latex)
                                continue
                        if child.string:
                            paragraph_content.append(child.string.strip())
                        elif child.name:
                            paragraph_content.append(child.get_text(strip=True))
                    
                    full_paragraph_text = " ".join(filter(None, paragraph_content)).strip()
                    if full_paragraph_text:
                        markdown_lines.append(f"{full_paragraph_text}\n\n")
                
                elif element.name == 'code' and not element.find_parent('pre'):
                    markdown_lines.append(f"`{element.get_text(strip=True)}` ")
                
                elif element.name == 'pre':
                    code_content = element.get_text(strip=False)
                    lang_match = re.search(r'language-(\w+)', element.get('class', [''])[0])
                    lang = lang_match.group(1) if lang_match else 'text'
                    markdown_lines.append(f"```{lang}\n{code_content.strip()}\n```\n\n")
                
                elif element.name == 'img':
                    img_src = element.get('src')
                    if img_src:
                        absolute_img_url = urljoin(url, img_src)
                        img_name = os.path.basename(urlparse(absolute_img_url).path)
                        if not img_name or '.' not in img_name:
                            img_extension = absolute_img_url.split('.')[-1].split('?')[0]
                            if len(img_extension) > 4 or not img_extension.isalnum():
                                img_extension = 'png'
                            img_name = f"image_{len(self.downloaded_images)}_{time.time_ns()}.{img_extension}"
                        
                        local_img_path = os.path.join(self.images_dir, img_name)
                        downloaded_path = self.download_image(absolute_img_url, local_img_path)
                        if downloaded_path:
                            relative_img_link = os.path.relpath(downloaded_path, os.path.dirname(output_path))
                            markdown_lines.append(f"![{element.get('alt', 'Image')}]({relative_img_link})\n\n")
                
                elif element.name == 'table':
                    headers = [th.get_text(strip=True) for th in element.find_all('th')]
                    rows = []
                    for tr in element.find_all('tr'):
                        row_data = [td.get_text(strip=True) for td in tr.find_all('td')]
                        if row_data:
                            rows.append(row_data)
                    
                    if headers:
                        markdown_lines.append("| " + " | ".join(headers) + " |\n")
                        markdown_lines.append("|" + "---|".join(['-' * len(h) for h in headers]) + "|\n")
                    for row in rows:
                        markdown_lines.append("| " + " | ".join(row) + " |\n")
                    markdown_lines.append("\n")
                
                elif element.name == 'li':
                    indent_level = 0
                    current_parent = element.find_parent(['ul', 'ol'])
                    while current_parent and current_parent.name in ['ul', 'ol']:
                        indent_level += 1
                        current_parent = current_parent.find_parent(['ul', 'ol'])
                    prefix = "- " if element.find_parent('ul') else "1. "
                    markdown_lines.append(f"{'  ' * (indent_level - 1)}{prefix}{element.get_text(strip=True)}\n")
                
                elif element.name in ['ul', 'ol']:
                    continue
                
                elif element.name == 'script':
                    latex = extract_math_latex(element)
                    if latex:
                        markdown_lines.append(latex)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(markdown_lines)
            logger.info(f"  Saved Markdown to: {output_path}")
        except Exception as e:
            logger.error(f"  Error writing Markdown file {output_path}: {e}")

    def _process_page(self, url, html_content):
        """Process page and save in requested formats."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Calculate relative path for organizing output
        relative_path_segment = urlparse(url).path.replace(self.docs_root_path, '', 1).strip('/')
        output_file_sub_dir = os.path.dirname(relative_path_segment)
        base_filename = sanitize_filename(url)
        
        # Extract structured content if needed for JSON
        structured_content = None
        if 'json' in self.formats:
            structured_content = self._extract_structured_content(soup, url)
        
        # Save in each requested format
        for format_type in self.formats:
            if format_type == 'md':
                output_full_dir = os.path.join(self.dirs['md'], output_file_sub_dir)
                os.makedirs(output_full_dir, exist_ok=True)
                output_filepath = os.path.join(output_full_dir, base_filename + '.md')
                self._save_markdown(url, soup, output_filepath)
            
            elif format_type == 'json':
                output_full_dir = os.path.join(self.dirs['json'], output_file_sub_dir)
                os.makedirs(output_full_dir, exist_ok=True)
                output_filepath = os.path.join(output_full_dir, base_filename + '.json')
                self._save_json(url, soup, structured_content, output_filepath)
            
            elif format_type == 'html':
                output_full_dir = os.path.join(self.dirs['html'], output_file_sub_dir)
                os.makedirs(output_full_dir, exist_ok=True)
                output_filepath = os.path.join(output_full_dir, base_filename + '.html')
                self._save_html(html_content, output_filepath)
        
        # Update site structure
        page_info = {
            'url': url,
            'title': soup.find('title').string.strip() if soup.find('title') else base_filename,
            'path': relative_path_segment,
            'scraped_at': datetime.utcnow().isoformat() + 'Z',
            'landing_ai_processed_docs': len(structured_content.get('landing_ai_processed', [])) if structured_content else 0
        }
        
        if self.include_metadata:
            page_info['metadata'] = extract_metadata(soup, url)
        
        self.site_structure['pages'].append(page_info)
        
        # Find all links for crawling
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            absolute_url = urljoin(url, href)
            parsed_absolute_url = urlparse(absolute_url)
            
            # Track link relationships
            self.site_structure['link_graph'][url].append(absolute_url)
            
            # Follow internal links
            if (parsed_absolute_url.netloc == self.base_netloc and
                parsed_absolute_url.path and
                not parsed_absolute_url.fragment):
                
                # Skip non-web files but allow PDFs for Landing.ai processing
                skip_extensions = ['.zip', '.tar', '.gz', '.exe', '.docx', '.xlsx', '.pptx']
                if not any(absolute_url.lower().endswith(ext) for ext in skip_extensions):
                    if absolute_url not in self.visited_urls and absolute_url not in self.to_visit_queue:
                        self.to_visit_queue.append(absolute_url)
                        logger.info(f"  Added to queue: {absolute_url}")
        
        # Look for pagination
        next_link = soup.find('a', string=re.compile(r'(Older Posts|Next|Next Page)', re.I))
        if next_link and next_link.get('href'):
            absolute_url = urljoin(url, next_link['href'])
            if absolute_url not in self.visited_urls and absolute_url not in self.to_visit_queue:
                self.to_visit_queue.append(absolute_url)
                logger.info(f"  Added next page to queue: {absolute_url}")

    def crawl(self, start_url):
        """Start the crawling process."""
        self.to_visit_queue.append(start_url)
        logger.info(f"Starting AI-enhanced crawl from: {start_url}")
        if self.landing_ai_enabled:
            logger.info(f"Landing.ai processing enabled for: {self.landing_ai_filter}")
        
        while self.to_visit_queue:
            current_url = self.to_visit_queue.pop(0)
            html_content = self._get_page_content(current_url)
            if html_content:
                self._process_page(current_url, html_content)
            
            if len(self.visited_urls) % 10 == 0:
                logger.info(f"Progress: {len(self.visited_urls)} pages, {len(self.landing_ai_processed)} docs processed with Landing.ai")
        
        # Finalize site structure
        self.site_structure['metadata']['scrape_end'] = datetime.utcnow().isoformat() + 'Z'
        self.site_structure['metadata']['total_pages'] = len(self.visited_urls)
        self.site_structure['metadata']['total_images'] = len(self.downloaded_images)
        self.site_structure['metadata']['landing_ai_processed_count'] = len(self.landing_ai_processed)
        self.site_structure['metadata']['estimated_landing_ai_cost'] = self.landing_ai_costs
        
        # Save site index
        site_index_path = os.path.join(self.output_dir, 'site_index.json')
        try:
            with open(site_index_path, 'w', encoding='utf-8') as f:
                json.dump(self.site_structure, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved site index to: {site_index_path}")
        except Exception as e:
            logger.error(f"Error saving site index: {e}")
        
        # Generate content graph
        self._generate_content_graph()

    def _generate_content_graph(self):
        """Generate graph representation of content relationships."""
        content_graph = {
            'nodes': [],
            'edges': [],
            'statistics': {
                'total_nodes': len(self.visited_urls),
                'total_edges': 0,
                'landing_ai_nodes': len(self.landing_ai_processed)
            }
        }
        
        # Create nodes
        url_to_id = {}
        for i, page in enumerate(self.site_structure['pages']):
            url_to_id[page['url']] = i
            content_graph['nodes'].append({
                'id': i,
                'url': page['url'],
                'title': page['title'],
                'type': 'page',
                'landing_ai_processed_docs': page.get('landing_ai_processed_docs', 0)
            })
        
        # Create edges
        edge_id = 0
        for source_url, target_urls in self.site_structure['link_graph'].items():
            if source_url in url_to_id:
                source_id = url_to_id[source_url]
                for target_url in target_urls:
                    if target_url in url_to_id:
                        target_id = url_to_id[target_url]
                        content_graph['edges'].append({
                            'id': edge_id,
                            'source': source_id,
                            'target': target_id,
                            'type': 'link'
                        })
                        edge_id += 1
        
        content_graph['statistics']['total_edges'] = len(content_graph['edges'])
        
        # Save content graph
        graph_path = os.path.join(self.output_dir, 'content_graph.json')
        try:
            with open(graph_path, 'w', encoding='utf-8') as f:
                json.dump(content_graph, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved content graph to: {graph_path}")
        except Exception as e:
            logger.error(f"Error saving content graph: {e}")

# --- Local Document Processing Functions ---

def is_supported_local_file(file_path):
    """Check if file is supported by Landing.ai (PDF, JPEG, PNG)."""
    supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
    return any(file_path.lower().endswith(ext) for ext in supported_extensions)

def discover_local_files(input_path, input_pattern=None):
    """Discover files for local processing."""
    import glob
    
    files_to_process = []
    
    if os.path.isfile(input_path):
        # Single file
        if is_supported_local_file(input_path):
            files_to_process.append(input_path)
        else:
            logger.warning(f"Unsupported file type: {input_path}. Supported: PDF, JPEG, PNG")
    elif os.path.isdir(input_path):
        # Directory
        if input_pattern:
            # Use pattern
            pattern_path = os.path.join(input_path, input_pattern)
            matched_files = glob.glob(pattern_path, recursive=True)
        else:
            # Default: find all supported files
            matched_files = []
            for ext in ['*.pdf', '*.jpg', '*.jpeg', '*.png']:
                pattern_path = os.path.join(input_path, '**', ext)
                matched_files.extend(glob.glob(pattern_path, recursive=True))
        
        # Filter for supported files
        for file_path in matched_files:
            if is_supported_local_file(file_path):
                files_to_process.append(os.path.abspath(file_path))
    
    return sorted(files_to_process)

def detect_document_type_from_filename(filename):
    """Detect document type from filename for schema selection."""
    filename_lower = filename.lower()
    
    # Research/academic keywords
    if any(term in filename_lower for term in ['paper', 'research', 'study', 'journal', 'arxiv', 'academic']):
        return 'research_paper'
    
    # Financial keywords
    if any(term in filename_lower for term in ['invoice', 'receipt', 'bill', 'statement', 'financial']):
        return 'financial_document'
    
    # Technical manual keywords
    if any(term in filename_lower for term in ['manual', 'guide', 'tutorial', 'docs', 'documentation', 'api']):
        return 'technical_manual'
    
    # Default based on file extension
    if filename_lower.endswith('.pdf'):
        return 'research_paper'  # Default for PDFs
    else:
        return 'financial_document'  # Default for images (often invoices/receipts)

def generate_local_output_dir(input_path, files_to_process):
    """Generate output directory name for local document processing."""
    if len(files_to_process) == 1:
        # Single file
        filename = os.path.splitext(os.path.basename(files_to_process[0]))[0]
        # Clean filename for directory name
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '-', filename)[:20]
        document_type = detect_document_type_from_filename(files_to_process[0])
    else:
        # Multiple files
        if os.path.isdir(input_path):
            clean_name = os.path.basename(os.path.abspath(input_path))[:20]
            document_type = 'batch'
        else:
            clean_name = 'multiple-files'
            document_type = 'batch'
    
    timestamp = datetime.now().strftime('%Y%m%d')
    return f"scraper-local_{document_type}_{clean_name}_{timestamp}"

def process_local_documents(files_to_process, output_dir, formats, landing_ai_enabled=False, landing_ai_schema=None, include_metadata=False):
    """Process local documents and generate outputs."""
    import shutil
    
    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    
    # Create format-specific directories
    format_dirs = {}
    for fmt in formats:
        format_dirs[fmt] = os.path.join(output_dir, fmt)
        os.makedirs(format_dirs[fmt], exist_ok=True)
    
    # Create documents directory for copies of processed files
    documents_dir = os.path.join(output_dir, 'documents')
    os.makedirs(documents_dir, exist_ok=True)
    
    # Create Landing.ai results directory if needed
    if landing_ai_enabled:
        landing_ai_dir = os.path.join(output_dir, 'landing_ai_processed')
        os.makedirs(landing_ai_dir, exist_ok=True)
    
    # Set up logging
    log_file = os.path.join(output_dir, 'scraper.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    processed_docs = []
    total_cost = 0.0
    
    # Process each file
    for i, file_path in enumerate(files_to_process, 1):
        logger.info(f"[{i}/{len(files_to_process)}] Processing: {os.path.basename(file_path)}")
        
        try:
            # Copy file to documents directory
            dest_filename = os.path.basename(file_path)
            dest_path = os.path.join(documents_dir, dest_filename)
            shutil.copy2(file_path, dest_path)
            
            doc_info = {
                'original_path': file_path,
                'filename': dest_filename,
                'file_size': os.path.getsize(file_path),
                'landing_ai_processed': False,
                'landing_ai_cost': 0.0,
                'formats_generated': []
            }
            
            # Process with Landing.ai if enabled
            landing_ai_result = None
            if landing_ai_enabled and LANDING_AI_AVAILABLE:
                try:
                    # Auto-detect schema if not provided
                    schema_to_use = landing_ai_schema
                    if not schema_to_use:
                        schema_to_use = detect_document_type_from_filename(file_path)
                        logger.info(f"  Auto-detected schema: {schema_to_use}")
                    
                    # Load schema
                    schema = None
                    if schema_to_use:
                        if os.path.exists(schema_to_use):
                            schema = load_schema(schema_to_use)
                        elif schema_to_use in DEFAULT_SCHEMAS:
                            schema = DEFAULT_SCHEMAS[schema_to_use]
                    
                    # Process with Landing.ai
                    logger.info(f"  Processing with Landing.ai...")
                    if schema:
                        landing_ai_result = landing_parse(dest_path, extraction_schema=schema)
                    else:
                        landing_ai_result = landing_parse(dest_path)
                    
                    # Estimate cost (rough approximation)
                    doc_cost = 0.01  # Base cost per document
                    doc_info['landing_ai_cost'] = doc_cost
                    doc_info['landing_ai_processed'] = True
                    total_cost += doc_cost
                    
                    # Save Landing.ai results
                    base_name = os.path.splitext(dest_filename)[0]
                    landing_ai_file = os.path.join(landing_ai_dir, f"{base_name}_landing_ai.json")
                    with open(landing_ai_file, 'w', encoding='utf-8') as f:
                        json.dump(landing_ai_result, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"  Landing.ai processing complete")
                    
                except Exception as e:
                    logger.error(f"  Landing.ai processing failed: {e}")
            
            # Generate output formats
            base_name = os.path.splitext(dest_filename)[0]
            
            # Generate basic metadata
            metadata = {
                'filename': dest_filename,
                'original_path': file_path,
                'file_size': doc_info['file_size'],
                'processed_at': datetime.now().isoformat(),
                'landing_ai_processed': doc_info['landing_ai_processed']
            }
            
            # Generate different output formats
            for fmt in formats:
                if fmt == 'json':
                    # JSON format with metadata and Landing.ai results
                    json_data = {
                        'metadata': metadata,
                        'content': {
                            'type': 'local_document',
                            'file_type': os.path.splitext(file_path)[1].lower(),
                            'landing_ai_result': landing_ai_result if landing_ai_result else None
                        }
                    }
                    
                    json_file = os.path.join(format_dirs['json'], f"{base_name}.json")
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                    doc_info['formats_generated'].append('json')
                    
                elif fmt == 'md':
                    # Markdown summary
                    md_content = f"# {dest_filename}\n\n"
                    md_content += f"**File Type:** {os.path.splitext(file_path)[1].upper()}\n"
                    md_content += f"**File Size:** {doc_info['file_size']:,} bytes\n"
                    md_content += f"**Processed:** {metadata['processed_at']}\n\n"
                    
                    if doc_info['landing_ai_processed'] and landing_ai_result:
                        md_content += "## Landing.ai Extraction Results\n\n"
                        md_content += "```json\n"
                        md_content += json.dumps(landing_ai_result, indent=2)
                        md_content += "\n```\n"
                    
                    md_file = os.path.join(format_dirs['md'], f"{base_name}.md")
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(md_content)
                    doc_info['formats_generated'].append('md')
                    
                elif fmt == 'html':
                    # HTML summary
                    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{dest_filename}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .metadata {{ background: #f5f5f5; padding: 20px; margin: 20px 0; }}
        .landing-ai {{ background: #e8f4f8; padding: 20px; margin: 20px 0; }}
        pre {{ background: #f0f0f0; padding: 10px; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>{dest_filename}</h1>
    <div class="metadata">
        <h2>File Information</h2>
        <p><strong>File Type:</strong> {os.path.splitext(file_path)[1].upper()}</p>
        <p><strong>File Size:</strong> {doc_info['file_size']:,} bytes</p>
        <p><strong>Processed:</strong> {metadata['processed_at']}</p>
    </div>
"""
                    
                    if doc_info['landing_ai_processed'] and landing_ai_result:
                        html_content += """
    <div class="landing-ai">
        <h2>Landing.ai Extraction Results</h2>
        <pre>{}</pre>
    </div>
""".format(json.dumps(landing_ai_result, indent=2))
                    
                    html_content += """
</body>
</html>"""
                    
                    html_file = os.path.join(format_dirs['html'], f"{base_name}.html")
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    doc_info['formats_generated'].append('html')
            
            processed_docs.append(doc_info)
            logger.info(f"  Generated formats: {', '.join(doc_info['formats_generated'])}")
            
        except Exception as e:
            logger.error(f"  Error processing {file_path}: {e}")
            processed_docs.append({
                'original_path': file_path,
                'filename': os.path.basename(file_path),
                'error': str(e),
                'landing_ai_processed': False,
                'landing_ai_cost': 0.0
            })
    
    # Generate summary files
    if 'json' in formats:
        summary = {
            'processing_summary': {
                'total_files': len(files_to_process),
                'successfully_processed': len([d for d in processed_docs if 'error' not in d]),
                'landing_ai_processed': len([d for d in processed_docs if d.get('landing_ai_processed')]),
                'total_landing_ai_cost': total_cost,
                'formats_generated': formats,
                'processed_at': datetime.now().isoformat()
            },
            'processed_documents': processed_docs
        }
        
        summary_file = os.path.join(output_dir, 'processing_summary.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    
    return processed_docs

# --- Execution ---
def main():
    parser = argparse.ArgumentParser(
        description='AI-Enhanced Universal Documentation Scraper with Landing.ai Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Web Scraping Examples:
  # Enable Landing.ai for PDFs with research paper schema
  python %(prog)s --url https://arxiv.org/papers/ --formats json,md --landing-ai --landing-ai-schema research_paper
  
  # Landing.ai with specific document filter
  python %(prog)s --url https://docs.example.com/ --landing-ai --landing-ai-filter "*.pdf"

Local Document Processing Examples:
  # Process single PDF with Landing.ai
  python %(prog)s --local --input research_paper.pdf --landing-ai --landing-ai-schema research_paper --formats json,md
  
  # Process all PDFs in directory
  python %(prog)s --local --input ./documents/ --input-pattern "*.pdf" --landing-ai --formats json
  
  # Process image documents (invoices, diagrams)
  python %(prog)s --local --input invoice.jpg --landing-ai --landing-ai-schema financial_document
        '''
    )
    
    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--url', help='Base URL to scrape (web scraping mode)')
    mode_group.add_argument('--local', action='store_true', help='Enable local document processing mode')
    
    # Common arguments
    parser.add_argument('--output', help='Output directory name')
    parser.add_argument('--formats', default='md', help='Output formats: md,json,html')
    parser.add_argument('--include-metadata', action='store_true', help='Include enhanced metadata')
    
    # Web scraping specific arguments
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests (web mode only)')
    parser.add_argument('--user-agent', default='Documentation-Scraper/1.0', help='User agent (web mode only)')
    parser.add_argument('--skip-robots', action='store_true', help='Skip robots.txt checking (web mode only)')
    
    # Local document processing arguments
    parser.add_argument('--input', help='Path to local file or directory (local mode only)')
    parser.add_argument('--input-pattern', help='Glob pattern for batch processing (e.g., "*.pdf", "*.{jpg,png}") (local mode only)')
    
    # Landing.ai specific arguments
    parser.add_argument('--landing-ai', action='store_true', help='Enable Landing.ai processing for documents')
    parser.add_argument('--landing-ai-schema', help='Schema for extraction: research_paper, technical_manual, or path to JSON schema')
    parser.add_argument('--landing-ai-filter', default='*.pdf', help='File patterns to process with Landing.ai (web mode only)')
    
    args = parser.parse_args()
    
    # Validate arguments based on mode
    if args.local:
        if not args.input:
            parser.error("--input is required when using --local mode")
        if not os.path.exists(args.input):
            parser.error(f"Input path does not exist: {args.input}")
    
    # Parse formats
    formats = [f.strip().lower() for f in args.formats.split(',')]
    valid_formats = ['md', 'json', 'html']
    for fmt in formats:
        if fmt not in valid_formats:
            parser.error(f"Invalid format '{fmt}'. Valid: {', '.join(valid_formats)}")
    
    # Handle local vs web mode
    if args.local:
        # LOCAL DOCUMENT PROCESSING MODE
        files_to_process = discover_local_files(args.input, args.input_pattern)
        
        if not files_to_process:
            logger.error(f"No supported files found in: {args.input}")
            logger.error("Supported file types: PDF, JPEG, PNG")
            return
        
        # Generate output directory
        if args.output:
            output_dir = args.output
        else:
            output_dir = generate_local_output_dir(args.input, files_to_process)
        
        logger.info("AI-Enhanced Universal Documentation Scraper - Local Mode")
        logger.info(f"Input path: {args.input}")
        logger.info(f"Files discovered: {len(files_to_process)}")
        logger.info(f"Output directory: {output_dir}")
        if args.input_pattern:
            logger.info(f"Pattern filter: {args.input_pattern}")
        
        # Show file list if reasonable number
        if len(files_to_process) <= 10:
            logger.info("Files to process:")
            for file_path in files_to_process:
                logger.info(f"  - {os.path.basename(file_path)}")
        elif len(files_to_process) > 10:
            logger.info(f"Processing {len(files_to_process)} files (showing first 5):")
            for file_path in files_to_process[:5]:
                logger.info(f"  - {os.path.basename(file_path)}")
            logger.info(f"  ... and {len(files_to_process) - 5} more")
        
    else:
        # WEB SCRAPING MODE  
        if args.output:
            output_dir = args.output
            logger.info("AI-Enhanced Universal Documentation Scraper - Web Mode")
            logger.info(f"Target URL: {args.url}")
            logger.info(f"Output directory: {output_dir} (user-specified)")
        else:
            output_dir = generate_output_dir_from_url(args.url)
            parsed_url = urlparse(args.url)
            project_type = detect_project_type(args.url, parsed_url)
            content_focus = extract_content_focus(parsed_url)
            
            logger.info("AI-Enhanced Universal Documentation Scraper - Web Mode")
            logger.info(f"Target URL: {args.url}")
            logger.info(f"Detected project type: {project_type}")
            logger.info(f"Content focus: {content_focus}")
            logger.info(f"Generated directory: {output_dir}")
        
        # Check robots.txt
        if not args.skip_robots:
            logger.info("Checking robots.txt...")
            can_fetch, crawl_delay = check_robots_txt(args.url, args.user_agent)
            if not can_fetch:
                logger.error("robots.txt disallows scraping. Use --skip-robots to override.")
                return
            if crawl_delay and crawl_delay > args.delay:
                logger.info(f"robots.txt crawl-delay: {crawl_delay}s")
                args.delay = crawl_delay
    
    # Common logging
    logger.info(f"Output formats: {', '.join(formats)}")
    logger.info(f"Landing.ai enabled: {args.landing_ai}")
    if args.landing_ai:
        logger.info(f"Landing.ai schema: {args.landing_ai_schema or 'auto-detect' if args.local else 'default'}")
        if not args.local:
            logger.info(f"Landing.ai filter: {args.landing_ai_filter}")
    
    # Execute based on mode
    if args.local:
        # LOCAL DOCUMENT PROCESSING
        # Process local documents directly
        processed_docs = process_local_documents(
            files_to_process, output_dir, formats,
            landing_ai_enabled=args.landing_ai,
            landing_ai_schema=args.landing_ai_schema,
            include_metadata=args.include_metadata
        )
        total_docs = len(processed_docs)
        total_landing_ai_processed = sum(1 for doc in processed_docs if doc.get('landing_ai_processed'))
        landing_ai_costs = sum(doc.get('landing_ai_cost', 0) for doc in processed_docs)
        
    else:
        # WEB SCRAPING MODE
        scraper = AIEnhancedDocsScraper(
            args.url, output_dir, args.delay, args.user_agent,
            formats=formats, include_metadata=args.include_metadata,
            landing_ai_enabled=args.landing_ai, landing_ai_schema=args.landing_ai_schema,
            landing_ai_filter=args.landing_ai_filter
        )
        scraper.crawl(args.url)
        total_docs = len(scraper.visited_urls)
        total_landing_ai_processed = len(scraper.landing_ai_processed)
        landing_ai_costs = scraper.landing_ai_costs
    
    # Print summary with folder structure
    logger.info("\n" + "="*50)
    if args.local:
        logger.info("Local Document Processing Complete!")
        logger.info(f"Total documents processed: {total_docs}")
        logger.info(f"Documents processed with Landing.ai: {total_landing_ai_processed}")
    else:
        logger.info("AI-Enhanced Web Scraping Complete!")
        logger.info(f"Total pages visited: {total_docs}")
        logger.info(f"Total images downloaded: {len(scraper.downloaded_images) if hasattr(scraper, 'downloaded_images') else 0}")
        logger.info(f"Documents processed with Landing.ai: {total_landing_ai_processed}")
    
    if args.landing_ai and landing_ai_costs > 0:
        logger.info(f"Estimated Landing.ai cost: ${landing_ai_costs:.2f}")
    
    # Show folder structure
    logger.info(f"\nProject folder structure:")
    logger.info(f"{output_dir}/")
    
    # Count files by format
    format_counts = {fmt: 0 for fmt in formats}
    img_count = 0
    ai_doc_count = 0
    
    try:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith('.md') and 'md' in formats:
                    format_counts['md'] += 1
                elif file.endswith('.json') and 'json' in formats and not file.startswith(('site_index', 'content_graph')):
                    format_counts['json'] += 1
                elif file.endswith('.html') and 'html' in formats:
                    format_counts['html'] += 1
                elif file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
                    img_count += 1
                elif file.lower().endswith(('.pdf', '.docx', '.doc')):
                    ai_doc_count += 1
        
        # Show format-specific directories
        for fmt in formats:
            if format_counts[fmt] > 0:
                logger.info(f"├── {fmt}/ ({format_counts[fmt]} {fmt.upper()} files)")
        
        if img_count > 0:
            logger.info(f"├── images/ ({img_count} image files)")
            
        if ai_doc_count > 0:
            logger.info(f"├── documents/ ({ai_doc_count} AI-processed documents)")
            
        if 'json' in formats:
            logger.info(f"├── site_index.json (complete site structure)")
            logger.info(f"├── content_graph.json (node/edge relationships)")
            
        if scraper.landing_ai_enabled and len(scraper.landing_ai_processed) > 0:
            logger.info(f"├── landing_ai_processed/ (AI extraction results)")
            
        logger.info(f"└── scraper.log (detailed execution log)")
        
    except Exception as e:
        logger.warning(f"Could not analyze folder structure: {e}")
    
    logger.info(f"\nOutput saved to: {output_dir}")
    logger.info(f"Formats generated: {', '.join(formats)}")
    logger.info("="*50)

if __name__ == "__main__":
    main()