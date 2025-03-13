"""
ContentFingerprinter - Creates hash-based fingerprints of web content

This module generates and compares content fingerprints to detect duplicate
or similar content even with minor variations.
"""

import re
import hashlib
import logging
from typing import Dict, Set, List, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class ContentFingerprinter:
    """
    Generates hash-based fingerprints from content and detects duplicates.
    
    Features:
    - Creates content fingerprints using multiple methods
    - Detects duplicate content even with minor variations
    - Maintains fingerprint history for comparison
    - Configurable similarity thresholds
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.85,
        max_fingerprints: int = 10000,
        min_shingle_size: int = 3
    ):
        """
        Initialize the fingerprinter with configurable parameters.
        
        Args:
            similarity_threshold: Threshold for considering content similar (0.0-1.0)
            max_fingerprints: Maximum number of fingerprints to store
            min_shingle_size: Minimum shingle size for shingling algorithm
        """
        self.similarity_threshold = similarity_threshold
        self.max_fingerprints = max_fingerprints
        self.min_shingle_size = min_shingle_size
        
        # Store content fingerprints (dictionary of url -> fingerprints)
        self.fingerprints: Dict[str, Dict] = {}
        
        # Create inverted index for rapid similarity lookup
        self.shingle_index: Dict[str, Set[str]] = defaultdict(set)
        
        logger.info(f"ContentFingerprinter initialized with similarity threshold {similarity_threshold}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text for consistent fingerprinting.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation and numbers
        text = re.sub(r'[^\w\s]|[\d]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _create_shingles(self, text: str, size: int) -> List[str]:
        """
        Create shingles (n-grams) from text.
        
        Args:
            text: Text to process
            size: Size of each shingle (n-gram)
            
        Returns:
            List of shingles
        """
        words = self._clean_text(text).split()
        if len(words) < size:
            return [" ".join(words)]
            
        return [" ".join(words[i:i+size]) for i in range(len(words) - size + 1)]
    
    def _calculate_simhash(self, text: str) -> int:
        """
        Calculate a SimHash of the text.
        
        Args:
            text: Text to hash
            
        Returns:
            SimHash value as integer
        """
        # Create word tokens
        tokens = self._clean_text(text).split()
        if not tokens:
            return 0
        
        # Initialize feature vector
        v = [0] * 64
        
        # For each token
        for token in tokens:
            # Get a 64-bit hash
            h = hashlib.md5(token.encode('utf-8')).hexdigest()
            h_int = int(h, 16)
            
            # Add the hash values to the feature vector
            for i in range(64):
                bit = (h_int >> i) & 1
                if bit == 1:
                    v[i] += 1
                else:
                    v[i] -= 1
        
        # Create the final simhash
        simhash = 0
        for i in range(64):
            if v[i] > 0:
                simhash |= (1 << i)
                
        return simhash
    
    def _hamming_distance(self, hash1: int, hash2: int) -> int:
        """
        Calculate Hamming distance between two hashes.
        
        Args:
            hash1: First hash value
            hash2: Second hash value
            
        Returns:
            Hamming distance
        """
        xor = hash1 ^ hash2
        return bin(xor).count('1')
    
    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """
        Calculate Jaccard similarity between two sets.
        
        Args:
            set1: First set
            set2: Second set
            
        Returns:
            Jaccard similarity (0.0-1.0)
        """
        if not set1 or not set2:
            return 0.0
            
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0
    
    def fingerprint(self, url: str, content: str) -> Dict:
        """
        Create fingerprints for content and store them.
        
        Args:
            url: URL associated with the content
            content: Content to fingerprint
            
        Returns:
            Dictionary with fingerprint information
        """
        if not content:
            logger.warning(f"Empty content for URL: {url}")
            return {}
            
        # Create various fingerprints
        clean_content = self._clean_text(content)
        md5_hash = hashlib.md5(clean_content.encode('utf-8')).hexdigest()
        simhash = self._calculate_simhash(clean_content)
        shingles = set(self._create_shingles(clean_content, self.min_shingle_size))
        
        # Create fingerprint record
        fingerprint = {
            "url": url,
            "md5": md5_hash,
            "simhash": simhash,
            "shingles": shingles,
            "content_length": len(content),
            "word_count": len(clean_content.split())
        }
        
        # Store fingerprint
        self.fingerprints[url] = fingerprint
        
        # Update inverted index for rapid similarity checks
        for shingle in shingles:
            self.shingle_index[shingle].add(url)
        
        # Limit storage size if needed
        if len(self.fingerprints) > self.max_fingerprints:
            self._prune_fingerprints()
        
        return fingerprint
    
    def _prune_fingerprints(self):
        """Remove oldest fingerprints to stay within size limits."""
        # Remove 20% of the oldest fingerprints
        fingerprints_to_remove = int(self.max_fingerprints * 0.2)
        urls_to_remove = list(self.fingerprints.keys())[:fingerprints_to_remove]
        
        for url in urls_to_remove:
            # Remove from inverted index
            for shingle in self.fingerprints[url]["shingles"]:
                if url in self.shingle_index[shingle]:
                    self.shingle_index[shingle].remove(url)
            
            # Remove the fingerprint
            del self.fingerprints[url]
            
        logger.info(f"Pruned {len(urls_to_remove)} old fingerprints")
    
    def find_similar(self, content: str, threshold: Optional[float] = None) -> List[Tuple[str, float]]:
        """
        Find similar content based on fingerprints.
        
        Args:
            content: Content to check for similarity
            threshold: Custom similarity threshold (overrides default)
            
        Returns:
            List of (URL, similarity score) tuples for similar content
        """
        if not content or not self.fingerprints:
            return []
        
        # Use provided threshold or default
        similarity_threshold = threshold or self.similarity_threshold
        
        # Generate fingerprint for comparison
        clean_content = self._clean_text(content)
        query_simhash = self._calculate_simhash(clean_content)
        query_shingles = set(self._create_shingles(clean_content, self.min_shingle_size))
        
        # Candidate URLs using inverted index for faster lookup
        candidate_urls = set()
        for shingle in query_shingles:
            candidate_urls.update(self.shingle_index.get(shingle, set()))
        
        # If no candidates via index, check all fingerprints
        if not candidate_urls and self.fingerprints:
            candidate_urls = set(self.fingerprints.keys())
        
        # Calculate similarity for each candidate
        similar_content = []
        for url in candidate_urls:
            fingerprint = self.fingerprints.get(url)
            if not fingerprint:
                continue
            
            # Calculate similarities using multiple methods
            
            # 1. SimHash similarity (using Hamming distance)
            hamming_dist = self._hamming_distance(query_simhash, fingerprint["simhash"])
            simhash_similarity = 1.0 - (hamming_dist / 64.0)  # Normalize to 0-1
            
            # 2. Jaccard similarity for shingles
            jaccard_sim = self._jaccard_similarity(query_shingles, fingerprint["shingles"])
            
            # Combined similarity score (average of both methods)
            similarity = (simhash_similarity + jaccard_sim) / 2.0
            
            # Add to results if above threshold
            if similarity >= similarity_threshold:
                similar_content.append((url, similarity))
        
        # Sort by similarity (highest first)
        similar_content.sort(key=lambda x: x[1], reverse=True)
        return similar_content
    
    def is_duplicate(self, content: str, threshold: Optional[float] = None) -> Tuple[bool, Optional[str], float]:
        """
        Check if content is a duplicate of existing content.
        
        Args:
            content: Content to check
            threshold: Custom similarity threshold (overrides default)
            
        Returns:
            Tuple of (is_duplicate, duplicate_url, similarity_score)
        """
        similar = self.find_similar(content, threshold)
        
        if similar:
            most_similar_url, similarity = similar[0]
            threshold_used = threshold or self.similarity_threshold
            
            if similarity >= threshold_used:
                logger.info(f"Duplicate content detected (similarity: {similarity:.2f}) with URL: {most_similar_url}")
                return True, most_similar_url, similarity
                
        return False, None, 0.0
    
    def clear(self):
        """Clear all stored fingerprints."""
        self.fingerprints.clear()
        self.shingle_index.clear()
        logger.info("Content fingerprints cleared")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about stored fingerprints.
        
        Returns:
            Dictionary with fingerprint statistics
        """
        return {
            "total_fingerprints": len(self.fingerprints),
            "total_shingles": len(self.shingle_index),
            "average_shingles_per_document": sum(len(fp["shingles"]) for fp in self.fingerprints.values()) / max(1, len(self.fingerprints))
        }
