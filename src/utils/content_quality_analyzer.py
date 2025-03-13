"""
ContentQualityAnalyzer - Evaluates the quality of web page content

This module provides functionality to analyze web page content quality by
examining text-to-HTML ratio, ad content, and other quality metrics.
"""

import logging
import re
from typing import Dict, List, Tuple, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ContentQualityAnalyzer:
    """
    Analyzes web content for quality metrics.
    
    Features:
    - Calculates text-to-HTML ratio
    - Estimates ad content percentage
    - Performs minimum content length checks
    - Provides an overall quality score
    """
    
    # Common ad-related class and id patterns
    AD_PATTERNS = [
        r'ad[s-_]?(\d+|container|box|wrap|banner|slot|frame|sidebar|top|bottom)',
        r'sponsor(ed)?(-\w+)?',
        r'banner(-\w+)?',
        r'promo(tion)?(-\w+)?',
        r'gpt-ad',
        r'dfp-slot',
        r'advertisement',
        r'commercial'
    ]
    
    # Compile the patterns for efficiency
    AD_REGEX = re.compile('|'.join(AD_PATTERNS).replace('[s-_]', '[s_-]'), re.IGNORECASE)
    
    def __init__(
        self,
        min_text_length: int = 500,
        min_text_html_ratio: float = 0.1,
        max_ad_ratio: float = 0.4,
        important_tags: List[str] = None
    ):
        """
        Initialize the quality analyzer with configurable thresholds.
        
        Args:
            min_text_length: Minimum text length for quality content
            min_text_html_ratio: Minimum text-to-HTML ratio
            max_ad_ratio: Maximum allowed ad content ratio
            important_tags: HTML tags considered important for content
        """
        self.min_text_length = min_text_length
        self.min_text_html_ratio = min_text_html_ratio
        self.max_ad_ratio = max_ad_ratio
        self.important_tags = important_tags or ['p', 'h1', 'h2', 'h3', 'article', 'section']
        logger.info("ContentQualityAnalyzer initialized")
    
    def analyze_html(self, html: str) -> Dict[str, any]:
        """
        Analyze HTML content and extract quality metrics.
        
        Args:
            html: HTML content to analyze
            
        Returns:
            Dictionary containing quality metrics
        """
        if not html:
            return {
                "quality_score": 0,
                "text_length": 0,
                "text_html_ratio": 0,
                "ad_ratio": 1.0,
                "important_tags_count": 0,
                "is_quality_content": False,
                "reason": "Empty HTML"
            }
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script, style tags and comments for analysis
            for element in soup(['script', 'style']):
                element.decompose()
            for comment in soup.find_all(text=lambda text: isinstance(text, str) and text.startswith('<!--')):
                comment.extract()
            
            # Get all text
            all_text = soup.get_text(separator=' ', strip=True)
            text_length = len(all_text)
            
            # Calculate HTML length
            html_length = len(html)
            text_html_ratio = text_length / html_length if html_length > 0 else 0
            
            # Count important content tags
            important_tags_count = sum(len(soup.find_all(tag)) for tag in self.important_tags)
            
            # Estimate ad content
            ad_content = self._estimate_ad_content(soup)
            ad_ratio = ad_content["ad_html_length"] / html_length if html_length > 0 else 0
            
            # Calculate overall quality score (0-100)
            quality_score = self._calculate_quality_score(
                text_length=text_length,
                text_html_ratio=text_html_ratio,
                ad_ratio=ad_ratio,
                important_tags_count=important_tags_count
            )
            
            # Determine if this is quality content
            is_quality = quality_score >= 50
            reason = self._determine_quality_reason(
                text_length=text_length,
                text_html_ratio=text_html_ratio,
                ad_ratio=ad_ratio,
                important_tags_count=important_tags_count,
                is_quality=is_quality
            )
            
            result = {
                "quality_score": quality_score,
                "text_length": text_length,
                "text_html_ratio": text_html_ratio,
                "ad_ratio": ad_ratio,
                "important_tags_count": important_tags_count,
                "is_quality_content": is_quality,
                "reason": reason
            }
            
            logger.debug(f"Content analysis: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing HTML content: {e}")
            return {
                "quality_score": 0,
                "text_length": 0,
                "text_html_ratio": 0,
                "ad_ratio": 1.0,
                "important_tags_count": 0,
                "is_quality_content": False,
                "reason": f"Analysis error: {str(e)}"
            }
    
    def _estimate_ad_content(self, soup: BeautifulSoup) -> Dict[str, int]:
        """
        Estimate the amount of advertisement content in the page.
        
        Args:
            soup: BeautifulSoup object of the HTML
            
        Returns:
            Dictionary with ad content metrics
        """
        # Find elements that match ad patterns
        ad_elements = []
        
        # Check class names
        for element in soup.find_all(class_=self.AD_REGEX):
            ad_elements.append(element)
            
        # Check id attributes
        for element in soup.find_all(id=self.AD_REGEX):
            if element not in ad_elements:
                ad_elements.append(element)
                
        # Common ad iframe sources
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if any(ad_service in src for ad_service in ['doubleclick', 'googlesyndication', 'adnxs', 'adsystem']):
                ad_elements.append(iframe)
        
        # Check for elements with 'advertisement' text
        for element in soup.find_all(text=re.compile(r'(advertisement|sponsored|promotion)', re.IGNORECASE)):
            parent = element.parent
            if parent not in ad_elements:
                ad_elements.append(parent)
        
        # Calculate total ad content length
        ad_html_length = sum(len(str(element)) for element in ad_elements)
        
        return {
            "ad_elements_count": len(ad_elements),
            "ad_html_length": ad_html_length
        }
    
    def _calculate_quality_score(
        self,
        text_length: int,
        text_html_ratio: float,
        ad_ratio: float,
        important_tags_count: int
    ) -> int:
        """
        Calculate an overall quality score from 0-100.
        
        Args:
            text_length: Length of the text content
            text_html_ratio: Ratio of text to HTML
            ad_ratio: Ratio of ad content
            important_tags_count: Count of important HTML tags
            
        Returns:
            Quality score from 0-100
        """
        # Text length score (0-30)
        text_length_score = min(30, text_length / 50)
        
        # Text-HTML ratio score (0-30)
        text_ratio_score = min(30, text_html_ratio * 200)
        
        # Ad ratio score (0-20, inverse)
        ad_score = max(0, 20 - (ad_ratio * 50))
        
        # Important tags score (0-20)
        tags_score = min(20, important_tags_count * 2)
        
        # Total score
        total_score = int(text_length_score + text_ratio_score + ad_score + tags_score)
        
        return max(0, min(100, total_score))
    
    def _determine_quality_reason(
        self,
        text_length: int,
        text_html_ratio: float,
        ad_ratio: float,
        important_tags_count: int,
        is_quality: bool
    ) -> str:
        """
        Determine the primary reason for the quality assessment.
        
        Args:
            text_length: Length of the text content
            text_html_ratio: Ratio of text to HTML
            ad_ratio: Ratio of ad content
            important_tags_count: Count of important HTML tags
            is_quality: Whether the content is deemed quality
            
        Returns:
            String explaining the quality assessment
        """
        if is_quality:
            return "Quality content"
        
        # Find the main reason for rejecting
        reasons = []
        
        if text_length < self.min_text_length:
            reasons.append(f"Text too short ({text_length} < {self.min_text_length})")
            
        if text_html_ratio < self.min_text_html_ratio:
            reasons.append(f"Text-HTML ratio too low ({text_html_ratio:.2f} < {self.min_text_html_ratio})")
            
        if ad_ratio > self.max_ad_ratio:
            reasons.append(f"Too much ad content ({ad_ratio:.2f} > {self.max_ad_ratio})")
            
        if important_tags_count < 3:
            reasons.append(f"Too few content tags ({important_tags_count} < 3)")
            
        if not reasons:
            return "Multiple quality factors below threshold"
            
        return ", ".join(reasons)
    
    def is_quality_content(self, html: str, threshold: int = 50) -> Tuple[bool, str]:
        """
        Determine if the content meets the quality threshold.
        
        Args:
            html: HTML content to analyze
            threshold: Quality score threshold (0-100)
            
        Returns:
            Tuple of (is_quality, reason)
        """
        result = self.analyze_html(html)
        is_quality = result["quality_score"] >= threshold
        return is_quality, result["reason"]
    
    def get_content_text(self, html: str) -> str:
        """
        Extract clean text content from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted text content
        """
        if not html:
            return ""
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script, style tags and comments
            for element in soup(['script', 'style', 'header', 'footer', 'nav']):
                element.decompose()
                
            # Get text with spacing between elements
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text from HTML: {e}")
            return ""
