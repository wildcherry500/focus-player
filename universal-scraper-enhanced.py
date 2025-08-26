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
    """
    Creates a valid filename from a URL by removing special characters
    and handling common URL patterns. Ensures it ends with appropriate extension.
    """
    parsed_url = urlparse(url)
    path = parsed_url.path

    # Remove leading/trailing slashes and the '~/' often found in Rama docs URLs
    path = path.strip('/').replace('~/', '')

    # Replace non-alphanumeric characters (except . and -) with underscores
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', path)

    # If the path is empty (e.g., for the root URL or a directory), append 'index'
    if not filename or filename.endswith('/'):
        filename += 'index'

    # Remove any existing file extension
    if '.' in filename and filename.rfind('.') > filename.rfind('/'):
        filename = filename[:filename.rfind('.')]

    return filename

def extract_math_latex(soup_tag):
    """
    Attempts to extract LaTeX source from MathJax/KaTeX elements.
    """
    # Look for script tags with type="math/tex" or similar
    if soup_tag.name == 'script' and 'type' in soup_tag.attrs and 'math/tex' in soup_tag['type']:
        return f"$${soup_tag.string}$$\n" if soup_tag.string else ""
    
    # Look for span elements with specific classes that might hold LaTeX
    if soup_tag.name == 'span' and ('class' in soup_tag.attrs and ('math' in soup_tag['class'] or 'katex' in soup_tag['class'])):
        # Prioritize data-latex attribute for LaTeX source
        if 'data-latex' in soup_tag.attrs:
            return f"$${soup_tag['data-latex']}$$\n"
        # If data-mathml is present, it's likely MathML, which we'll note but not convert to LaTeX
        if 'data-mathml' in soup_tag.attrs:
            logger.warning(f"  Skipping MathML content for LaTeX extraction: {soup_tag['data-mathml']}")
            return ""
        # Fallback to direct text content for simple inline equations
        if soup_tag.string and soup_tag.string.strip():
            return f"${soup_tag.string.strip()}$"
    
    # If it's an image of math, return a markdown image link
    if soup_tag.name == 'img' and ('class' in soup_tag.attrs and 'math' in soup_tag['class']):
        return f"![Mathematical formula]({soup_tag.get('src', '')})\n"

    return None

def check_robots_txt(base_url, user_agent='Documentation-Scraper/1.0'):
    """
    Check robots.txt for the given URL and return whether scraping is allowed.
    """
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        
        # Check if we can fetch the base URL
        can_fetch = rp.can_fetch(user_agent, base_url)
        
        # Get crawl delay if specified
        crawl_delay = rp.crawl_delay(user_agent)
        if crawl_delay is None:
            crawl_delay = rp.crawl_delay("*")
        
        return can_fetch, crawl_delay
    except Exception as e:
        logger.warning(f"Could not check robots.txt: {e}")
        return True, None  # Default to allowing if we can't check

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
    
    # Title
    title_tag = soup.find('title')
    if title_tag and title_tag.string:
        metadata['title'] = title_tag.string.strip()
    
    # Meta tags
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

# --- Main Scraper Logic ---

class DocsScraper:
    def __init__(self, base_url, output_dir, delay, user_agent='Documentation-Scraper/1.0', 
                 formats=['md'], include_metadata=False):
        self.base_url = base_url
        self.output_dir = output_dir
        self.delay = delay
        self.user_agent = user_agent
        self.formats = formats
        self.include_metadata = include_metadata
        
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
        
        self.images_dir = os.path.join(output_dir, "images")
        os.makedirs(self.images_dir, exist_ok=True)
        
        self.visited_urls = set()
        self.to_visit_queue = []
        self.downloaded_images = set()
        self.total_pages = 0
        
        # For site index and graph generation
        self.site_structure = {
            'metadata': {
                'base_url': base_url,
                'scrape_start': datetime.utcnow().isoformat() + 'Z',
                'total_pages': 0,
                'total_images': 0
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
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set up file handler for logging
        file_handler = logging.FileHandler(os.path.join(self.output_dir, 'scraper.log'))
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    def download_image(self, img_url, local_image_path):
        """
        Downloads an image from a URL and saves it locally.
        """
        if img_url in self.downloaded_images:
            logger.info(f"  Image already downloaded: {img_url}")
            return local_image_path
        try:
            if img_url.startswith('data:'):
                match = re.match(r'data:image/(\w+);base64,(.*)', img_url)
                if match:
                    img_data = base64.b64decode(match.group(2))
                    with open(local_image_path, 'wb') as f:
                        f.write(img_data)
                    self.downloaded_images.add(img_url)
                    logger.info(f"  Downloaded data URI image to: {local_image_path}")
                    return local_image_path
                else:
                    logger.warning(f"  Skipping unsupported data URI format: {img_url[:50]}...")
                    return None
            response = requests.get(img_url, stream=True, timeout=10, headers=self.headers)
            response.raise_for_status()
            with open(local_image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.downloaded_images.add(img_url)
            logger.info(f"  Downloaded image: {img_url} to {local_image_path}")
            return local_image_path
        except requests.exceptions.RequestException as e:
            logger.error(f"  Error downloading image {img_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"  Unexpected error downloading image {img_url}: {e}")
            return None

    def _get_page_content(self, url):
        """Fetches HTML content from a URL."""
        if url in self.visited_urls:
            logger.info(f"  Skipping already visited URL: {url}")
            return None
        
        self.total_pages += 1
        logger.info(f"[{self.total_pages}] Visiting: {url}")
        self.visited_urls.add(url)
        
        try:
            response = requests.get(url, timeout=15, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"  Error fetching {url}: {e}")
            return None
        finally:
            time.sleep(self.delay)

    def _extract_structured_content(self, soup, url):
        """Extract content in a structured format for JSON output."""
        structured_content = {
            'sections': [],
            'images': [],
            'tables': [],
            'code_blocks': [],
            'links': {
                'internal': [],
                'external': []
            }
        }
        
        # Find main content area
        content_div = soup.find('div', class_=lambda x: x and ('main-content' in x or 'page-content' in x))
        if not content_div:
            content_div = soup.find('article')
        if not content_div:
            content_div = soup.find('main')
        if not content_div:
            content_div = soup.find('body')
        
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
                    
                    # Extract links within paragraph
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
                    if code_element:
                        lang_classes = code_element.get('class', [])
                        language = 'text'
                        for cls in lang_classes:
                            if cls.startswith('language-'):
                                language = cls.replace('language-', '')
                                break
                    else:
                        language = 'text'
                    
                    structured_content['code_blocks'].append({
                        'id': f'code-{len(structured_content["code_blocks"])}',
                        'language': language,
                        'content': element.get_text(strip=False)
                    })
                
                # Tables
                elif element.name == 'table':
                    table_data = {
                        'id': f'table-{len(structured_content["tables"])}',
                        'headers': [],
                        'rows': []
                    }
                    
                    # Extract headers
                    for th in element.find_all('th'):
                        table_data['headers'].append(th.get_text(strip=True))
                    
                    # Extract rows
                    for tr in element.find_all('tr'):
                        row_data = []
                        for td in tr.find_all('td'):
                            row_data.append(td.get_text(strip=True))
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
        
        # Extract all links for graph building
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            absolute_url = urljoin(url, href)
            parsed = urlparse(absolute_url)
            
            if parsed.netloc == self.base_netloc:
                structured_content['links']['internal'].append(absolute_url)
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
                'scraper_version': '1.0'
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
        """Save content in Markdown format (existing logic)."""
        markdown_lines = []
        markdown_lines.append(f"\n\n")
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            markdown_lines.append(f"# {title_tag.string.strip()}\n\n")
        else:
            markdown_lines.append(f"# {sanitize_filename(url).replace('_', ' ').title()}\n\n")
        
        # Find main content area
        content_div = soup.find('div', class_=lambda x: x and ('main-content' in x or 'page-content' in x))
        if not content_div:
            content_div = soup.find('article')
        if not content_div:
            content_div = soup.find('main')
        if not content_div:
            content_div = soup.find('body')
            logger.warning(f"  Specific content div not found for {url}. Scraping from body.")
        
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
                elif element.name == 'code':
                    if element.find_parent('pre'):
                        continue
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
                            # Calculate relative path from markdown file location
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
                    continue
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(markdown_lines)
            logger.info(f"  Saved Markdown to: {output_path}")
        except IOError as e:
            logger.error(f"  Error writing Markdown file {output_path}: {e}")

    def _process_page(self, url, html_content):
        """Process page and save in requested formats."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Calculate relative path for organizing output
        relative_path_segment = urlparse(url).path.replace(self.docs_root_path, '', 1).strip('/')
        output_file_sub_dir = os.path.dirname(relative_path_segment)
        
        # Base filename without extension
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
        
        # Update site structure for index
        page_info = {
            'url': url,
            'title': soup.find('title').string.strip() if soup.find('title') else base_filename,
            'path': relative_path_segment,
            'scraped_at': datetime.utcnow().isoformat() + 'Z'
        }
        if self.include_metadata:
            page_info['metadata'] = extract_metadata(soup, url)
        
        self.site_structure['pages'].append(page_info)
        
        # Find all links on the page for crawling
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            absolute_url = urljoin(url, href)
            parsed_absolute_url = urlparse(absolute_url)
            
            # Track link relationships
            self.site_structure['link_graph'][url].append(absolute_url)
            
            # Universal link filtering: follow any internal link
            if (parsed_absolute_url.netloc == self.base_netloc and
                parsed_absolute_url.path and
                not parsed_absolute_url.fragment):
                if not any(absolute_url.lower().endswith(ext) for ext in ['.pdf', '.zip', '.tar', '.gz', '.exe', '.docx', '.xlsx', '.pptx']):
                    if absolute_url not in self.visited_urls and absolute_url not in self.to_visit_queue:
                        self.to_visit_queue.append(absolute_url)
                        logger.info(f"  Added to queue: {absolute_url}")
        
        # Look for pagination links
        next_link = soup.find('a', string=re.compile(r'(Older Posts|Next|Next Page)', re.I))
        if next_link and next_link.get('href'):
            absolute_url = urljoin(url, next_link['href'])
            if absolute_url not in self.visited_urls and absolute_url not in self.to_visit_queue:
                self.to_visit_queue.append(absolute_url)
                logger.info(f"  Added next page to queue: {absolute_url}")

    def crawl(self, start_url):
        """Starts the recursive crawling process."""
        self.to_visit_queue.append(start_url)
        logger.info(f"Starting crawl from: {start_url}")
        
        while self.to_visit_queue:
            current_url = self.to_visit_queue.pop(0)
            html_content = self._get_page_content(current_url)
            if html_content:
                self._process_page(current_url, html_content)
            
            # Show queue status periodically
            if len(self.visited_urls) % 10 == 0:
                logger.info(f"Progress: {len(self.visited_urls)} pages visited, {len(self.to_visit_queue)} in queue")
        
        # Finalize site structure
        self.site_structure['metadata']['scrape_end'] = datetime.utcnow().isoformat() + 'Z'
        self.site_structure['metadata']['total_pages'] = len(self.visited_urls)
        self.site_structure['metadata']['total_images'] = len(self.downloaded_images)
        
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
        """Generate a graph representation of content relationships."""
        content_graph = {
            'nodes': [],
            'edges': [],
            'statistics': {
                'total_nodes': len(self.visited_urls),
                'total_edges': 0
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
                'type': 'page'
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

# --- Execution ---
def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description='Universal Documentation Scraper - Enhanced with multi-format output',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Format Options:
  md    - Markdown files (human-readable)
  json  - Structured JSON (for databases/APIs)
  html  - Original HTML (preserves exact formatting)

Examples:
  # Basic scraping with Markdown output
  python %(prog)s --url https://docs.example.com/
  
  # All formats with metadata
  python %(prog)s --url https://docs.landing.ai/ade/ --formats md,json,html --include-metadata
  
  # JSON only for API integration
  python %(prog)s --url https://docs.example.com/ --formats json --output api_docs
        '''
    )
    
    parser.add_argument('--url', required=True, help='Base URL to scrape')
    parser.add_argument('--output', help='Output directory name (auto-generated from URL if not specified)')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--user-agent', default='Documentation-Scraper/1.0', help='User agent string')
    parser.add_argument('--skip-robots', action='store_true', help='Skip robots.txt checking')
    parser.add_argument('--formats', default='md', help='Output formats: md,json,html (comma-separated, default: md)')
    parser.add_argument('--include-metadata', action='store_true', help='Include enhanced metadata extraction')
    
    args = parser.parse_args()
    
    # Parse format options
    formats = [f.strip().lower() for f in args.formats.split(',')]
    valid_formats = ['md', 'json', 'html']
    for fmt in formats:
        if fmt not in valid_formats:
            parser.error(f"Invalid format '{fmt}'. Valid formats are: {', '.join(valid_formats)}")
    
    # Generate output directory if not specified
    if args.output:
        output_dir = args.output
        logger.info(f"Universal Documentation Scraper - Enhanced Edition")
        logger.info(f"Target URL: {args.url}")
        logger.info(f"Output directory: {output_dir} (user-specified)")
    else:
        output_dir = generate_output_dir_from_url(args.url)
        parsed_url = urlparse(args.url)
        project_type = detect_project_type(args.url, parsed_url)
        content_focus = extract_content_focus(parsed_url)
        
        logger.info(f"Universal Documentation Scraper - Enhanced Edition")
        logger.info(f"Target URL: {args.url}")
        logger.info(f"Detected project type: {project_type}")
        logger.info(f"Content focus: {content_focus}")
        logger.info(f"Generated directory: {output_dir}")
    
    logger.info(f"Output formats: {', '.join(formats)}")
    logger.info(f"Request delay: {args.delay}s")
    logger.info(f"Include metadata: {args.include_metadata}")
    
    # Check robots.txt unless skipped
    if not args.skip_robots:
        logger.info("Checking robots.txt...")
        can_fetch, crawl_delay = check_robots_txt(args.url, args.user_agent)
        
        if not can_fetch:
            logger.error("robots.txt disallows scraping this URL. Use --skip-robots to override.")
            return
        
        if crawl_delay is not None and crawl_delay > args.delay:
            logger.info(f"robots.txt specifies crawl-delay of {crawl_delay}s, updating delay")
            args.delay = crawl_delay
    
    # Create scraper instance and start crawling
    scraper = DocsScraper(
        args.url, 
        output_dir, 
        args.delay, 
        args.user_agent,
        formats=formats,
        include_metadata=args.include_metadata
    )
    scraper.crawl(args.url)
    
    # Print summary with folder structure
    logger.info("\n" + "="*50)
    logger.info("Scraping complete!")
    logger.info(f"Total pages visited: {len(scraper.visited_urls)}")
    logger.info(f"Total unique images downloaded: {len(scraper.downloaded_images)}")
    
    # Show folder structure
    logger.info(f"\nProject folder structure:")
    logger.info(f"{output_dir}/")
    
    # Count files by format
    format_counts = {fmt: 0 for fmt in formats}
    img_count = 0
    
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
        
        # Show format-specific directories
        for fmt in formats:
            if format_counts[fmt] > 0:
                logger.info(f"├── {fmt}/ ({format_counts[fmt]} {fmt.upper()} files)")
        
        if img_count > 0:
            logger.info(f"├── images/ ({img_count} image files)")
            
        if 'json' in formats:
            logger.info(f"├── site_index.json (complete site structure)")
            logger.info(f"├── content_graph.json (node/edge relationships)")
            
        logger.info(f"└── scraper.log (detailed execution log)")
        
    except Exception as e:
        logger.warning(f"Could not analyze folder structure: {e}")
    
    logger.info(f"\nOutput saved to: {output_dir}")
    logger.info(f"Formats generated: {', '.join(formats)}")
    logger.info("="*50)

if __name__ == "__main__":
    main()