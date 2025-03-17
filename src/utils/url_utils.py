"""
Utility functions for handling URLs in crawlers.
"""

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import Set, List, Dict

def extract_urls_with_pattern(html: str, base_url: str, pattern: str = None, tag: str = "a", 
                              class_name: str = None, contains_path: str = None) -> Set[str]:
    """
    Extract URLs from HTML with specified pattern.
    
    Args:
        html: Page HTML content
        base_url: Base URL for resolving relative URLs
        pattern: Regex pattern to match URLs (optional)
        tag: HTML tag to search for links (default: "a")
        class_name: CSS class name to filter elements (optional)
        contains_path: String that URL path must contain (optional)
        
    Returns:
        Set of URLs matching criteria
    """
    urls = set()
    soup = BeautifulSoup(html, "html.parser")
    
    # Find elements based on tag and class if specified
    if class_name:
        elements = soup.find_all(tag, class_=class_name)
    else:
        elements = soup.find_all(tag)
    
    # Extract href attributes
    for element in elements:
        href = element.get("href") if tag == "a" else None
        if href:
            url = urljoin(base_url, href)
            
            # Apply filtering criteria
            if pattern and not re.search(pattern, url):
                continue
                
            if contains_path and contains_path not in url:
                continue
                
            urls.add(url)
                
    return urls

def filter_urls(urls: List[str], domain: str = None, contains: List[str] = None, 
               excludes: List[str] = None, path_pattern: str = None) -> List[str]:
    """
    Filter URLs based on various criteria.
    
    Args:
        urls: List of URLs to filter
        domain: Domain that URLs must match (optional)
        contains: List of strings that URLs must contain (optional)
        excludes: List of strings that URLs must not contain (optional)
        path_pattern: Regex pattern for URL path (optional)
        
    Returns:
        List of filtered URLs
    """
    filtered = []
    
    for url in urls:
        if not url or not isinstance(url, str):
            continue
            
        parsed = urlparse(url)
        
        # Check domain
        if domain and domain not in parsed.netloc:
            continue
            
        # Check required substrings
        if contains and not all(item in url for item in contains):
            continue
            
        # Check excluded substrings
        if excludes and any(item in url for item in excludes):
            continue
            
        # Check path pattern
        if path_pattern and not re.search(path_pattern, parsed.path):
            continue
            
        filtered.append(url)
            
    return filtered

def get_base_domain(url: str) -> str:
    """Extract the base domain from a URL."""
    parsed = urlparse(url)
    return parsed.netloc

def construct_pagination_url(base_url: str, page_num: int, pagination_type: str = 'query') -> str:
    """
    Construct a URL for pagination based on the site's pagination format.
    
    Args:
        base_url: Base URL to paginate from
        page_num: Page number
        pagination_type: Type of pagination ('query', 'path', 'wordpress', 'sabay')
        
    Returns:
        Paginated URL
    """
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    if pagination_type == 'query':
        # For sites that use ?page=X (like BTV)
        parsed = urlparse(base_url)
        query = parse_qs(parsed.query)
        query['page'] = [str(page_num)]
        new_query = urlencode(query, doseq=True)
        return urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ))
    elif pagination_type == 'path':
        # For sites that use /page/X/ (like WordPress)
        if base_url.endswith('/'):
            return f"{base_url}page/{page_num}/"
        else:
            return f"{base_url}/page/{page_num}/"
    elif pagination_type == 'sabay':
        # For Sabay News which uses a number at the end of the URL
        if base_url.endswith('/'):
            return f"{base_url}{page_num}"
        else:
            return f"{base_url}/{page_num}"
    else:
        # Default to appending page number
        return f"{base_url}/{page_num}"
