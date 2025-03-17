"""
Extractor adapter module for routing URLs to appropriate scrapers.

This module handles selecting and calling the appropriate scraper
based on the domain of the URL.
"""

import importlib
import sys
from typing import Dict, Any, Optional, Callable
from urllib.parse import urlparse

from src.extractors.config import SCRAPER_MAP
from src.extractors.logger import log_debug, log_error
from src.extractors.scrapers import generic_scraper

def register_scrapers() -> Dict[str, Callable]:
    """
    Register available scrapers from config map.
    
    Returns:
        Dictionary mapping domains to scraper functions
    """
    scrapers = {}
    
    # Register each scraper from the SCRAPER_MAP
    for domain, scraper_module_name in SCRAPER_MAP.items():
        try:
            # Import the module
            module_path = f"src.extractors.scrapers.{scraper_module_name}"
            scraper_module = importlib.import_module(module_path)
            
            # Extract the main scraper function (scrape_X or extract_article)
            if hasattr(scraper_module, f"scrape_{scraper_module_name.replace('_scraper', '')}"):
                scraper_func = getattr(scraper_module, f"scrape_{scraper_module_name.replace('_scraper', '')}")
            elif hasattr(scraper_module, "extract_article"):
                scraper_func = getattr(scraper_module, "extract_article")
            else:
                log_error(f"No scraper function found in {scraper_module_name}")
                continue
            
            # Add to the scrapers map
            normalized_domain = f"https://{domain}"
            scrapers[normalized_domain] = scraper_func
            scrapers[domain] = scraper_func  # Also register without https://
            log_debug(f"Registered scraper for {domain}: {scraper_func.__name__}")
            
        except Exception as e:
            log_error(f"Failed to register scraper for {domain}: {e}")
    
    # Register RFA scraper specifically (ensure it works with specific URL format)
    try:
        from src.extractors.scrapers import rfa_scraper
        scrapers["https://www.rfa.org"] = rfa_scraper.scrape_rfa
        log_debug("Registered RFA scraper explicitly")
    except Exception as e:
        log_error(f"Failed to register RFA scraper: {e}")
            
    return scrapers

# Global registry of scrapers
SCRAPERS = register_scrapers()

def create_extractor_for_domain(domain: str) -> Optional[object]:
    """
    Create an extractor module for the given domain.
    
    Args:
        domain: The domain to create an extractor for
        
    Returns:
        An extractor module that can extract content from this domain
    """
    global SCRAPERS
    
    try:
        # Normalize the domain
        domain = domain.strip().lower()
        if domain.startswith("www."):
            non_www_domain = domain[4:]
            domains_to_check = [domain, non_www_domain]
        else:
            www_domain = "www." + domain
            domains_to_check = [domain, www_domain]
            
        # Also check with https:// prefix
        domains_to_check.extend([f"https://{d}" for d in domains_to_check])
        
        # Check if we have a registered scraper for this domain
        for d in domains_to_check:
            if d in SCRAPERS:
                # Create a module-like object with extract_article function
                extractor = type('Extractor', (), {})()
                extractor.extract_article = SCRAPERS[d]
                return extractor
                
        # If no matching scraper, use the generic extractor
        extractor = type('GenericExtractor', (), {})()
        extractor.extract_article = generic_scraper.generic_scrape
        return extractor
        
    except Exception as e:
        log_error(f"Error creating extractor for domain {domain}: {e}")
        return None
