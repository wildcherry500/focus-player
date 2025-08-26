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
    and handling common URL patterns. Ensures it ends with .md.
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

    # Remove any existing file extension (e.g., .html, .php) before adding .md
    if '.' in filename and filename.rfind('.') > filename.rfind('/'):
        filename = filename[:filename.rfind('.')]

    # Ensure it ends with .md for markdown files
    if not filename.endswith('.md'):
        filename += '.md'

    return filename

def extract_math_latex(soup_tag):
    """
    Attempts to extract LaTeX source from MathJax/KaTeX elements.
    This is a heuristic and might need adjustment based on the actual HTML structure.
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
    from datetime import datetime
    
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

# --- Main Scraper Logic ---

class DocsScraper:
    def __init__(self, base_url, output_dir, delay, user_agent='Documentation-Scraper/1.0'):
        self.base_url = base_url
        self.output_dir = output_dir
        self.delay = delay
        self.user_agent = user_agent
        
        # Parse base URL to get root path
        parsed = urlparse(base_url)
        self.base_netloc = parsed.netloc
        self.docs_root_path = parsed.path
        
        self.images_dir = os.path.join(output_dir, "images")
        self.visited_urls = set()
        self.to_visit_queue = []
        self.downloaded_images = set()
        self.total_pages = 0
        
        # Request headers
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Create output directories if they don't exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        
        # Set up file handler for logging now that output dir exists
        file_handler = logging.FileHandler(os.path.join(self.output_dir, 'scraper.log'))
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    def download_image(self, img_url, local_image_path):
        """
        Downloads an image from a URL and saves it locally.
        Returns the local path if successful, None otherwise.
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

    def _process_page(self, url, html_content):
        """Parses HTML, extracts content, and saves to Markdown."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Calculate relative path for organizing output
        relative_path_segment = urlparse(url).path.replace(self.docs_root_path, '', 1).strip('/')
        output_file_sub_dir = os.path.dirname(relative_path_segment)
        output_full_dir = os.path.join(self.output_dir, output_file_sub_dir)
        os.makedirs(output_full_dir, exist_ok=True)
        
        markdown_filename = sanitize_filename(url)
        output_filepath = os.path.join(output_full_dir, markdown_filename)
        
        markdown_lines = []
        markdown_lines.append(f"\n\n")
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            markdown_lines.append(f"# {title_tag.string.strip()}\n\n")
        else:
            markdown_lines.append(f"# {sanitize_filename(url).replace('.md', '').replace('_', ' ').title()}\n\n")
        
        # Try to find main content area
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
                            relative_img_link = os.path.relpath(downloaded_path, output_full_dir)
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
        
        # Find all links on the page
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            absolute_url = urljoin(url, href)
            parsed_absolute_url = urlparse(absolute_url)
            
            # Universal link filtering: follow any internal link (same netloc) with a non-empty path and no fragment
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
        
        # Save the markdown file
        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.writelines(markdown_lines)
            logger.info(f"  Saved content to: {output_filepath}")
        except IOError as e:
            logger.error(f"  Error writing file {output_filepath}: {e}")

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

# --- Execution ---
def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description='Universal Documentation Scraper - Scrapes documentation websites and converts to Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python %(prog)s --url https://blog.redplanetlabs.com/rama-case-studies/
  python %(prog)s --url https://docs.landing.ai/ade/ --output landing_ai_docs
  python %(prog)s --url https://example.com/docs/ --delay 2.0
        '''
    )
    
    parser.add_argument('--url', required=True, help='Base URL to scrape')
    parser.add_argument('--output', help='Output directory name (auto-generated from URL if not specified)')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--user-agent', default='Documentation-Scraper/1.0', help='User agent string')
    parser.add_argument('--skip-robots', action='store_true', help='Skip robots.txt checking')
    
    args = parser.parse_args()
    
    # Generate output directory if not specified
    if args.output:
        output_dir = args.output
        logger.info(f"Universal Documentation Scraper")
        logger.info(f"Target URL: {args.url}")
        logger.info(f"Output directory: {output_dir} (user-specified)")
    else:
        output_dir = generate_output_dir_from_url(args.url)
        parsed_url = urlparse(args.url)
        project_type = detect_project_type(args.url, parsed_url)
        content_focus = extract_content_focus(parsed_url)
        
        logger.info(f"Universal Documentation Scraper")
        logger.info(f"Target URL: {args.url}")
        logger.info(f"Detected project type: {project_type}")
        logger.info(f"Content focus: {content_focus}")
        logger.info(f"Generated directory: {output_dir}")
    
    logger.info(f"Request delay: {args.delay}s")
    
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
    scraper = DocsScraper(args.url, output_dir, args.delay, args.user_agent)
    scraper.crawl(args.url)
    
    # Print summary with folder structure
    logger.info("\n" + "="*50)
    logger.info("Scraping complete!")
    logger.info(f"Total pages visited: {len(scraper.visited_urls)}")
    logger.info(f"Total unique images downloaded: {len(scraper.downloaded_images)}")
    
    # Show folder structure
    logger.info(f"\nProject folder structure:")
    logger.info(f"{output_dir}/")
    
    # Count markdown files and images
    md_count = 0
    img_count = 0
    
    try:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith('.md'):
                    md_count += 1
                elif file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
                    img_count += 1
        
        logger.info(f"├── {md_count} markdown files (.md)")
        if img_count > 0:
            logger.info(f"├── images/ ({img_count} image files)")
        logger.info(f"└── scraper.log (detailed execution log)")
        
    except Exception as e:
        logger.warning(f"Could not analyze folder structure: {e}")
    
    logger.info(f"\nOutput saved to: {output_dir}")
    logger.info("="*50)

if __name__ == "__main__":
    main()