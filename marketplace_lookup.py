#!/usr/bin/env python3
"""
Marketplace Lookup Module

Fetches category information from Second Life Marketplace product pages.
Uses SL credentials to access Adult-rated content.

Usage:
    python marketplace_lookup.py --url "https://marketplace.secondlife.com/p/PRODUCT/12345"
    python marketplace_lookup.py --url "https://marketplace.secondlife.com/p/PRODUCT/12345" --save
"""

import argparse
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProductInfo:
    """Information scraped from a Marketplace product page."""
    url: str
    name: str
    category_path: list[str]  # e.g., ["Avatar Accessories", "Collars"]
    category_full: str  # e.g., "Avatar Accessories > Collars"
    maturity: str  # General, Moderate, Adult
    creator: Optional[str] = None
    scraped_at: Optional[str] = None


class MarketplaceLookup:
    """Handles authentication and scraping of SL Marketplace."""
    
    LOGIN_URL = "https://id.secondlife.com/openid/login"
    MARKETPLACE_BASE = "https://marketplace.secondlife.com"
    
    def __init__(self, username: str, password: str, cache_file: str = "marketplace_cache.json"):
        self.username = username
        self.password = password
        self.cache_file = Path(cache_file)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.authenticated = False
        self.cache = self._load_cache()
    
    def _load_cache(self) -> dict:
        """Load cached product info from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache: {e}")
        return {"products": {}, "categories": {}}
    
    def _save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
            logger.info(f"Cache saved to {self.cache_file}")
        except IOError as e:
            logger.error(f"Failed to save cache: {e}")
    
    def login(self) -> bool:
        """
        Authenticate with Second Life to access Adult content.
        Returns True if login successful.
        """
        logger.info("Attempting to login to Second Life...")
        
        try:
            # First, get the login page to establish session and get CSRF token
            login_page_url = f"{self.LOGIN_URL}?return_to={self.MARKETPLACE_BASE}"
            resp = self.session.get(login_page_url, timeout=30)
            resp.raise_for_status()
            
            # Get CSRF token from cookie (Django-style CSRF protection)
            csrf_token = self.session.cookies.get('csrftoken', '')
            
            # Build login payload
            payload = {
                'username': self.username,
                'password': self.password,
                'return_to': self.MARKETPLACE_BASE,
                'show_join': 'true',
            }
            
            # Include CSRF token in payload (Django middleware token)
            if csrf_token:
                payload['csrfmiddlewaretoken'] = csrf_token
            
            # Set headers with CSRF token and Referer
            headers = {
                'X-CSRFToken': csrf_token,
                'Referer': login_page_url,
            }
            
            logger.debug(f"Posting login with CSRF token")
            
            # Submit login to loginsubmit endpoint
            login_resp = self.session.post(
                "https://id.secondlife.com/openid/loginsubmit",
                data=payload,
                headers=headers,
                timeout=30,
                allow_redirects=True
            )
            
            # Check if we were redirected to marketplace (success)
            if 'marketplace.secondlife.com' in login_resp.url:
                logger.info("✓ Successfully logged in to Marketplace")
                self.authenticated = True
                return True
            
            # Check for login failure
            if 'incorrect' in login_resp.text.lower():
                logger.error("Login failed - incorrect username or password")
                return False
            
            # Verify by checking marketplace
            check_resp = self.session.get(
                f"{self.MARKETPLACE_BASE}/en-US",
                timeout=30
            )
            
            # Look for signs of being logged in
            if 'Sign out' in check_resp.text or 'sign-out' in check_resp.text.lower():
                logger.info("✓ Successfully logged in to Marketplace")
                self.authenticated = True
                return True
            
            logger.warning("Login may have failed - continuing anyway")
            return False
            
        except requests.RequestException as e:
            logger.error(f"Login request failed: {e}")
            return False
    
    def get_product_info(self, url: str, use_cache: bool = True) -> Optional[ProductInfo]:
        """
        Fetch and parse product information from a Marketplace URL.
        
        Args:
            url: Full marketplace product URL
            use_cache: Check cache first before fetching
            
        Returns:
            ProductInfo if successful, None otherwise
        """
        # Normalize URL
        url = url.split('?')[0]  # Remove query params
        
        # Check cache first
        if use_cache and url in self.cache.get("products", {}):
            logger.info(f"Cache hit for {url}")
            cached = self.cache["products"][url]
            return ProductInfo(**cached)
        
        logger.info(f"Fetching: {url}")
        
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            
            # Check if we need to login
            if "Please log in" in resp.text and "adult content" in resp.text.lower():
                if not self.authenticated:
                    logger.info("Adult content - attempting login...")
                    if not self.login():
                        logger.warning("Could not authenticate for adult content")
                    # Retry the request
                    resp = self.session.get(url, timeout=30)
            
            return self._parse_product_page(url, resp.text)
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def _parse_product_page(self, url: str, html: str) -> Optional[ProductInfo]:
        """Parse product information from HTML using regex."""
        
        # Extract product name from title
        name = ""
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            title_text = title_match.group(1)
            # Format: "Second Life Marketplace - Product Name"
            if ' - ' in title_text:
                name = title_text.split(' - ', 1)[1].strip()
            else:
                name = title_text.strip()
        
        # Extract category from JavaScript - primary method
        category_full = ""
        category_path = []
        
        # Look for category in JS: 'category': 'Category Name'
        category_match = re.search(r"'category':\s*'([^']+)'", html)
        if category_match:
            category_full = category_match.group(1)
        
        # Alternative: look for product_category in dataLayer
        if not category_full:
            datalayer_cat = re.search(r'"product_category":\s*"([^"]+)"', html)
            if datalayer_cat:
                category_full = datalayer_cat.group(1)
        
        # Extract breadcrumb path from links
        breadcrumb_matches = re.findall(
            r'<a[^>]*href="[^"]*category_id=[^"]*"[^>]*>([^<]+)</a>',
            html,
            re.IGNORECASE
        )
        for cat_name in breadcrumb_matches:
            cat_name = cat_name.strip()
            if cat_name and cat_name != '…' and cat_name not in category_path:
                category_path.append(cat_name)
        
        if category_path and not category_full:
            category_full = " > ".join(category_path)
        elif category_full and not category_path:
            # Split category string if it contains separators
            if ' > ' in category_full:
                category_path = [c.strip() for c in category_full.split(' > ')]
            elif '/' in category_full:
                category_path = [c.strip() for c in category_full.split('/')]
            else:
                category_path = [category_full]
        
        # Extract maturity rating
        maturity = "Unknown"
        maturity_match = re.search(
            r'(?:maturity|rating)["\s:]+([GAM]|General|Moderate|Adult)',
            html,
            re.IGNORECASE
        )
        if maturity_match:
            mat = maturity_match.group(1).upper()
            if mat == 'G':
                maturity = "General"
            elif mat == 'M':
                maturity = "Moderate"
            elif mat == 'A':
                maturity = "Adult"
            else:
                maturity = maturity_match.group(1).title()
        
        # Extract creator/merchant from store links
        creator = None
        merchant_match = re.search(r'<a[^>]*href="/stores/[^"]*"[^>]*>([^<]+)</a>', html)
        if merchant_match:
            creator = merchant_match.group(1).strip()
        
        if not name and not category_full:
            logger.warning("Could not parse product page - may need login")
            return None
        
        product = ProductInfo(
            url=url,
            name=name,
            category_path=category_path,
            category_full=category_full or "Unknown",
            maturity=maturity,
            creator=creator,
            scraped_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        logger.info(f"  Name: {product.name}")
        logger.info(f"  Category: {product.category_full}")
        logger.info(f"  Maturity: {product.maturity}")
        if creator:
            logger.info(f"  Creator: {product.creator}")
        
        return product
    
    def cache_product(self, product: ProductInfo):
        """Add product to cache."""
        self.cache["products"][product.url] = asdict(product)
        
        # Also cache by normalized name for lookup
        normalized_name = self._normalize_name(product.name)
        if normalized_name:
            self.cache.setdefault("by_name", {})[normalized_name] = product.url
        
        self._save_cache()
    
    def _normalize_name(self, name: str) -> str:
        """Normalize product name for matching."""
        # Remove version numbers
        name = re.sub(r'\s*v?\d+(\.\d+)*\s*$', '', name, flags=re.IGNORECASE)
        # Remove common suffixes
        name = re.sub(r'\s*\((boxed|unpacked|copy|no copy|mod|no mod)\)\s*', '', name, flags=re.IGNORECASE)
        # Normalize whitespace
        name = ' '.join(name.split())
        return name.lower().strip()
    
    def lookup_by_name(self, item_name: str) -> Optional[ProductInfo]:
        """
        Try to find product in cache by name.
        Handles version number differences.
        """
        normalized = self._normalize_name(item_name)
        
        if normalized in self.cache.get("by_name", {}):
            url = self.cache["by_name"][normalized]
            if url in self.cache.get("products", {}):
                return ProductInfo(**self.cache["products"][url])
        
        return None
    
    def search_marketplace(self, query: str, num_results: int = 5) -> list[str]:
        """
        Search for Marketplace URLs.
        
        Note: Most search engines block automated searches. This method tries
        multiple approaches but may not always work. For reliable lookups,
        use direct product URLs with --url.
        
        Returns list of marketplace product URLs found.
        """
        logger.info(f"Searching for: {query}")
        urls_found = []
        
        # Try Marketplace search directly (requires login for adult content)
        try:
            # Login first to access all content
            if not self.authenticated:
                self.login()
            
            # Use marketplace search
            resp = self.session.get(
                f"{self.MARKETPLACE_BASE}/products/search",
                params={
                    'search[keywords]': query,
                    'search[maturity_level]': 'gma',  # General, Moderate, Adult
                },
                timeout=15
            )
            
            # Extract product URLs - they appear as data attributes or links
            # Format: /p/Product-Name/12345 (product page) or /s/Product-Name/12345 (search result)
            urls = re.findall(
                r'href="(/[ps]/[^"]+)"',
                resp.text
            )
            
            for url in urls:
                # Convert /s/ URLs to /p/ URLs (they're equivalent)
                url = url.replace('/s/', '/p/')
                full_url = f"{self.MARKETPLACE_BASE}{url}"
                if full_url not in urls_found:
                    urls_found.append(full_url)
                    if len(urls_found) >= num_results:
                        break
            
            if urls_found:
                logger.info(f"  Found {len(urls_found)} products via Marketplace search")
                return urls_found
                
        except requests.RequestException as e:
            logger.debug(f"Marketplace search failed: {e}")
        
        # Fallback: try DuckDuckGo (may be blocked)
        try:
            search_query = f"site:marketplace.secondlife.com {query}"
            resp = self.session.get(
                "https://html.duckduckgo.com/html/",
                params={'q': search_query},
                timeout=15
            )
            
            urls = re.findall(
                r'marketplace\.secondlife\.com/p/[^"&\s<>]+',
                resp.text
            )
            
            for url in urls:
                url = url.split('&')[0].split('?')[0]
                full_url = f"https://{url}"
                if full_url not in urls_found:
                    urls_found.append(full_url)
                    if len(urls_found) >= num_results:
                        break
                        
        except requests.RequestException as e:
            logger.debug(f"DuckDuckGo search failed: {e}")
        
        logger.info(f"  Found {len(urls_found)} marketplace URLs total")
        return urls_found
    
    def search_and_lookup(self, query: str, save: bool = True) -> Optional[ProductInfo]:
        """
        Search for a product and lookup the first matching result.
        
        Verifies that the result name matches the query to avoid
        false positives from Marketplace URL redirects.
        """
        urls = self.search_marketplace(query)
        
        if not urls:
            logger.warning("No marketplace URLs found in search results")
            return None
        
        # Normalize query for matching
        query_words = set(query.lower().split())
        
        # Try each result until we find a good match
        for url in urls:
            logger.info(f"Trying: {url}")
            product = self.get_product_info(url, use_cache=False)  # Don't use cache, verify fresh
            if product:
                # Verify the product name contains query words
                product_words = set(product.name.lower().split())
                common_words = query_words & product_words
                
                # Require at least 1 significant word match (excluding common words)
                common_words -= {'the', 'a', 'an', 'and', 'or', 'for', 'in', 'on', 'at', 'to'}
                
                if common_words:
                    logger.info(f"  ✓ Match found: {product.name}")
                    if save:
                        self.cache_product(product)
                    return product
                else:
                    logger.warning(f"  ✗ Skipping (name mismatch): {product.name}")
        
        logger.warning("No matching products found")
        return None
    
    def clear_cache(self):
        """Clear the entire cache."""
        self.cache = {"products": {}, "categories": {}, "by_name": {}}
        self._save_cache()
        logger.info("Cache cleared")
    
    def remove_from_cache(self, url: str):
        """Remove a specific URL from cache."""
        if url in self.cache.get("products", {}):
            del self.cache["products"][url]
            # Also remove from by_name
            by_name = self.cache.get("by_name", {})
            to_remove = [k for k, v in by_name.items() if v == url]
            for k in to_remove:
                del by_name[k]
            self._save_cache()
            logger.info(f"Removed {url} from cache")
    
    def map_to_sort_category(self, marketplace_category: str) -> Optional[str]:
        """
        Map a Marketplace category to our inventory sorting category.
        
        Returns a suggested target path for the inventory sorter.
        """
        cat_lower = marketplace_category.lower()
        
        # Mapping of Marketplace categories to our sorting structure
        mappings = {
            # BDSM
            'bdsm collars': 'BDSM/Restraints/Collars',
            'bdsm cuffs': 'BDSM/Restraints/Cuffs',
            'bdsm gags': 'BDSM/Restraints/Gags',
            'bdsm blindfolds': 'BDSM/Restraints/Blindfolds',
            'bdsm': 'BDSM',
            
            # Body parts
            'avatar components': 'Body Parts',
            'mesh bodies': 'Body Parts/Bodies',
            'mesh heads': 'Body Parts/Heads',
            'avatar skins': 'Body Parts/Skins',
            'shape': 'Body Parts/Shapes',
            'eyes': 'Body Parts/Eyes',
            'hair': 'Body Parts/Hair',
            
            # Clothing
            'women\'s clothing': 'Clothing',
            'men\'s clothing': 'Clothing',
            'unisex clothing': 'Clothing',
            'pants': 'Clothing/Pants',
            'shirts': 'Clothing/Tops',
            'dresses': 'Clothing/Dresses',
            'shoes': 'Clothing/Shoes',
            'lingerie': 'Clothing/Lingerie',
            'underwear': 'Clothing/Underwear',
            'hosiery': 'Clothing/Hosiery',
            'jewelry': 'Clothing/Accessories/Jewelry',
            'accessories': 'Clothing/Accessories',
            
            # Animation
            'animations': 'Animations',
            'animation override': 'Animation Overrides',
            'ao': 'Animation Overrides',
            'poses': 'Animations/Poses',
            
            # Other
            'textures': 'Materials',
            'scripts': 'Scripts',
            'furniture': 'Home/Furniture',
            'home and garden': 'Home',
        }
        
        # Try exact match first
        for mp_cat, sort_cat in mappings.items():
            if mp_cat in cat_lower:
                return sort_cat
        
        return None
    
    def suggest_category(self, item_name: str) -> Optional[dict]:
        """
        Try to suggest a category for an inventory item.
        
        Returns dict with 'marketplace_category' and 'suggested_path' if found.
        """
        # First check cache
        cached = self.lookup_by_name(item_name)
        if cached:
            suggested = self.map_to_sort_category(cached.category_full)
            return {
                'item_name': item_name,
                'marketplace_category': cached.category_full,
                'suggested_path': suggested,
                'source': 'cache',
                'url': cached.url,
            }
        
        # Try search (may not work due to rate limits)
        product = self.search_and_lookup(item_name, save=True)
        if product:
            suggested = self.map_to_sort_category(product.category_full)
            return {
                'item_name': item_name,
                'marketplace_category': product.category_full,
                'suggested_path': suggested,
                'source': 'search',
                'url': product.url,
            }
        
        return None


def main():
    parser = argparse.ArgumentParser(description='Lookup product category from SL Marketplace')
    parser.add_argument('--url', type=str, help='Marketplace product URL')
    parser.add_argument('--search', type=str, help='Search for product by name')
    parser.add_argument('--suggest', type=str, help='Suggest sorting category for an item name')
    parser.add_argument('--config', type=str, default='config.json', help='Config file with credentials')
    parser.add_argument('--save', action='store_true', help='Save result to cache')
    parser.add_argument('--cache-file', type=str, default='marketplace_cache.json', help='Cache file path')
    parser.add_argument('--test-login', action='store_true', help='Just test the login')
    parser.add_argument('--clear-cache', action='store_true', help='Clear the cache')
    parser.add_argument('--show-cache', action='store_true', help='Show cached products')
    
    args = parser.parse_args()
    
    # Load credentials from config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        logger.info("Create config.json with 'marketplace_username' and 'sl_password' fields")
        return 1
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Get credentials - try marketplace-specific first, then fall back to Corrade creds
    username = config.get('marketplace_username') or config.get('username', 'allonde')
    password = config.get('sl_password') or config.get('password', '')
    
    if not password:
        logger.error("No password found in config")
        return 1
    
    # Initialize lookup
    lookup = MarketplaceLookup(username, password, args.cache_file)
    
    # Handle cache operations
    if args.clear_cache:
        lookup.clear_cache()
        print("✓ Cache cleared")
        return 0
    
    if args.show_cache:
        products = lookup.cache.get("products", {})
        if not products:
            print("Cache is empty")
        else:
            print(f"\nCached products ({len(products)}):\n")
            for url, data in products.items():
                print(f"  {data.get('name', 'Unknown')}")
                print(f"    Category: {data.get('category_full', 'Unknown')}")
                print(f"    URL: {url}")
                print()
        return 0
    
    if args.test_login:
        success = lookup.login()
        return 0 if success else 1
    
    # Handle suggest (for sorting assistance)
    if args.suggest:
        result = lookup.suggest_category(args.suggest)
        if result:
            print("\n" + "="*60)
            print(f"Item: {result['item_name']}")
            print(f"Marketplace Category: {result['marketplace_category']}")
            if result['suggested_path']:
                print(f"Suggested Sort Path: {result['suggested_path']}")
            else:
                print("Suggested Sort Path: (no mapping available)")
            print(f"Source: {result['source']}")
            print(f"URL: {result['url']}")
            print("="*60)
            return 0
        else:
            logger.info("Could not find category suggestion for this item")
            return 1
    
    # Handle search
    if args.search:
        product = lookup.search_and_lookup(args.search, save=args.save)
        if product:
            print("\n" + "="*60)
            print(f"Product: {product.name}")
            print(f"Category: {product.category_full}")
            print(f"Path: {' > '.join(product.category_path)}")
            print(f"Maturity: {product.maturity}")
            if product.creator:
                print(f"Creator: {product.creator}")
            print(f"URL: {product.url}")
            print("="*60)
            return 0
        else:
            logger.error("Could not find product")
            return 1
    
    if not args.url:
        logger.error("Please provide --url, --search, or --test-login")
        return 1
    
    # Fetch product info
    product = lookup.get_product_info(args.url)
    
    if product:
        print("\n" + "="*60)
        print(f"Product: {product.name}")
        print(f"Category: {product.category_full}")
        print(f"Path: {' > '.join(product.category_path)}")
        print(f"Maturity: {product.maturity}")
        if product.creator:
            print(f"Creator: {product.creator}")
        print("="*60)
        
        if args.save:
            lookup.cache_product(product)
            print(f"\n✓ Saved to cache")
        
        return 0
    else:
        logger.error("Failed to get product info")
        return 1


if __name__ == '__main__':
    exit(main())

