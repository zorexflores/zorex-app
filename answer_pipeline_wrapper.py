"""
Wrapper around answer_pipeline to provide class-based interface
Filters out non-product documents for cleaner summaries
"""
import json
import hashlib
from pathlib import Path
from answer_pipeline import make_answer

class AnswerPipeline:
    def __init__(self, cache_file="summary_cache.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        
        # Load product pages from corpus
        with open('corpus/index/pages.json', 'r') as f:
            self.pages = json.load(f)
        
        # Create product lookup
        self.products = {}
        for page in self.pages:
            product = page['product']
            if product not in self.products:
                self.products[product] = []
            self.products[product].append(page['text'])
    
    def _load_cache(self):
        """Load existing cache"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_cache(self):
        """Save cache to disk"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def _get_cache_key(self, product_name):
        """Generate cache key for a product"""
        return hashlib.md5(product_name.encode()).hexdigest()
    
    def _is_product_doc(self, product_name: str) -> bool:
        """Determine if this is an actual product vs newsletter/manual/duplicate."""
        name_lower = product_name.lower()
        
        # Exclude newsletters and manuals
        exclude_patterns = [
            'newsletter', 'news', 'better health',
            'manual', 'protocol manual', 'blood chemistry',
            'cliniciansview', 'quick reference',
            # Full month names
            'april', 'may', 'june', 'july', 'august', 'september', 'sept',
            'october', 'november', 'december', 'january', 'february', 'march',
            # Abbreviated months
            'jan ', 'feb ', 'mar ', 'apr ', 'may ', 'jun ', 
            'jul ', 'aug ', 'sep ', 'oct ', 'nov ', 'dec ',
            # Year patterns (dated literature)
            ' 2022', ' 2023', ' 2024', '2022', '2023', '2024'
        ]
        
        if any(pattern in name_lower for pattern in exclude_patterns):
            return False
        
        # Exclude literature files and duplicates
        if any(name_lower.endswith(suffix) for suffix in [' lit', 'lit', ' literature', ' tech lit']):
            if not product_name.isupper():  # Keep uppercase versions
                return False
        
        # Exclude lowercase duplicates (e.g., "sign u spray" when "SIGN U SPRAY" exists)
        if product_name and product_name[0].islower():
            return False
        
        # Exclude demo products
        if 'demo' in name_lower:
            return False
        
        
        # Exclude duplicates if (1) version exists
        version_with_1 = f"{product_name} (1)"
        if version_with_1 in self.products and product_name != version_with_1:
            return False
        
        return True

    def get_product_list(self):
        """Get list of actual products (excludes newsletters/manuals)"""
        all_products = sorted(self.products.keys())
        # Filter to only actual products
        products = [p for p in all_products if self._is_product_doc(p)]
        return products
    
    def get_all_items(self):
        """Get everything including newsletters/manuals"""
        return sorted(self.products.keys())
    
    def get_cached_summary(self, product_name):
        """Get summary for a product (cached or generate new)"""
        cache_key = self._get_cache_key(product_name)
        
        # Check cache first
        if cache_key in self.cache:
            blocks = self.cache[cache_key].get('blocks', [])
            return ' '.join(blocks)
        
        # Generate new summary
        if product_name not in self.products:
            return f"No data found for {product_name}"
        
        # Get all text for this product
        product_texts = self.products[product_name]
        
        # Generate summary
        result = make_answer(
            query=product_name,
            raw_chunks=product_texts,
            product_hint=product_name
        )
        
        # Cache it
        self.cache[cache_key] = result
        self._save_cache()
        
        # Return formatted summary
        blocks = result.get('blocks', [])
        return ' '.join(blocks)
