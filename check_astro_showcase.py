#!/usr/bin/env python3
"""
Periodic checker for sites in Astro.build showcase.
Checks which page a site appears on in https://astro.build/showcase/
"""

import asyncio
import aiohttp
import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

# Fix SSL certs for PyInstaller
try:
    import certifi
    os.environ.setdefault('SSL_CERT_FILE', certifi.where())
    os.environ.setdefault('REQUESTS_CA_BUNDLE', certifi.where())
    # Ensure certifi is bundled by PyInstaller
    import sys
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
except ImportError:
    pass


class AstroShowcaseChecker:
    BASE_URL = "https://astro.build/showcase"
    MAX_PAGES = 109  # Known total pages
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.cache_file = Path("showcase_cache.json")
        self.cache: Dict[str, int] = {}
        self.load_cache()
    
    def load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
    
    def save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    async def fetch_page(self, page: int) -> str:
        """Fetch a showcase page."""
        url = self.BASE_URL if page == 1 else f"{self.BASE_URL}/{page}/"
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()
    
    async def find_site(self, site: str, max_pages: Optional[int] = None) -> Optional[int]:
        """Find which page a site appears on. Returns page number or None."""
        site_lower = site.lower()
        max_pages = max_pages or self.MAX_PAGES
        
        # Check cache first
        if site in self.cache:
            cached_page = self.cache[site]
            # Verify it's still there
            html = await self.fetch_page(cached_page)
            if site_lower in html.lower():
                return cached_page
            else:
                # Site moved or removed, invalidate cache
                del self.cache[site]
        
        # Search pages
        for page in range(1, max_pages + 1):
            html = await self.fetch_page(page)
            if site_lower in html.lower():
                self.cache[site] = page
                self.save_cache()
                return page
        
        return None
    
    async def find_multiple(self, sites: List[str], max_pages: Optional[int] = None) -> Dict[str, Optional[int]]:
        """Find multiple sites concurrently."""
        tasks = [self.find_site(site, max_pages) for site in sites]
        results = await asyncio.gather(*tasks)
        return dict(zip(sites, results))
    
    async def get_all_sites(self, max_pages: Optional[int] = None) -> List[Dict]:
        """Extract all sites from showcase (slow, scans all pages)."""
        max_pages = max_pages or self.MAX_PAGES
        all_sites = []
        
        for page in range(1, max_pages + 1):
            html = await self.fetch_page(page)
            # Extract site cards - pattern: <a href="https://domain" ...><span class="sr-only">Title</span>
            import re
            # Match the site card pattern
            pattern = r'<a href="(https://[^"]+)"[^>]*>\s*<span class="sr-only">([^<]+)</span>'
            matches = re.findall(pattern, html)
            for url, title in matches:
                domain = urlparse(url).netloc
                all_sites.append({
                    "page": page,
                    "domain": domain,
                    "url": url,
                    "title": title.strip()
                })
        
        return all_sites


async def check_uses_astro(session: aiohttp.ClientSession, url: str) -> Dict:
    """Check if a site uses Astro by inspecting headers and HTML."""
    result = {
        "url": url,
        "uses_astro": False,
        "indicators": [],
        "generator": None,
        "astro_version": None,
        "error": None
    }
    
    try:
        # Ensure URL has scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            html = await resp.text()
            headers = resp.headers
            
            # Check generator meta tag
            import re
            gen_match = re.search(r'<meta name="generator" content="([^"]*)"', html, re.IGNORECASE)
            if gen_match:
                result["generator"] = gen_match.group(1)
                if 'astro' in gen_match.group(1).lower():
                    result["uses_astro"] = True
                    result["indicators"].append(f"Generator meta: {gen_match.group(1)}")
            
            # Check for astro:island or data-astro-cid attributes
            if 'astro:island' in html or 'data-astro-cid' in html:
                result["uses_astro"] = True
                result["indicators"].append("Astro island/cid attributes found")
            
            # Check for _astro/ assets (Astro's default asset prefix)
            if '/_astro/' in html:
                result["uses_astro"] = True
                result["indicators"].append("Astro asset prefix /_astro/ found")
            
            # Check for Astro-specific scripts
            if 'astro:' in html.lower() and ('hydrate' in html.lower() or 'island' in html.lower()):
                result["uses_astro"] = True
                result["indicators"].append("Astro hydration/island markers found")
            
            # Check Server header
            server = headers.get('Server', '')
            if 'astro' in server.lower():
                result["uses_astro"] = True
                result["indicators"].append(f"Server header: {server}")
            
            # Check X-Powered-By
            powered = headers.get('X-Powered-By', '')
            if 'astro' in powered.lower():
                result["uses_astro"] = True
                result["indicators"].append(f"X-Powered-By: {powered}")
                
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def main():
    parser = argparse.ArgumentParser(description="Check Astro showcase for sites")
    parser.add_argument("sites", nargs="*", help="Sites to search for (domains or full URLs)")
    parser.add_argument("--all", action="store_true", help="Extract all sites from showcase")
    parser.add_argument("--check-astro", action="store_true", help="Check if sites use Astro")
    parser.add_argument("--max-pages", type=int, default=109, help="Max pages to scan")
    parser.add_argument("--output", choices=["json", "table"], default="table", help="Output format")
    args = parser.parse_args()
    
    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit=5)
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        checker = AstroShowcaseChecker(session)
        
        if args.all:
            print(f"Scanning all {args.max_pages} pages...", file=sys.stderr)
            sites = await checker.get_all_sites(args.max_pages)
            if args.output == "json":
                print(json.dumps(sites, indent=2))
            else:
                for s in sites:
                    print(f"Page {s['page']:3d} | {s['domain']:40s} | {s['title']}")
            return
        
        if not args.sites:
            parser.print_help()
            return
        
        # Search for specified sites
        print(f"Searching for {len(args.sites)} site(s) in showcase...", file=sys.stderr)
        results = await checker.find_multiple(args.sites, args.max_pages)
        
        if args.check_astro:
            print("Checking if sites use Astro...", file=sys.stderr)
            astro_results = {}
            for site in args.sites:
                # Use the showcase URL if found, otherwise try the site directly
                page = results.get(site)
                if page:
                    # We'd need to extract the actual URL from showcase
                    # For now just check the domain
                    astro_results[site] = await check_uses_astro(session, f"https://{site}")
                else:
                    astro_results[site] = await check_uses_astro(session, f"https://{site}")
            
            if args.output == "json":
                output = {
                    "showcase_pages": results,
                    "astro_check": astro_results
                }
                print(json.dumps(output, indent=2))
            else:
                for site in args.sites:
                    page = results.get(site)
                    astro = astro_results.get(site, {})
                    status = f"Page {page}" if page else "Not found"
                    astro_status = "✅ Uses Astro" if astro.get("uses_astro") else "❌ Not Astro"
                    if astro.get("error"):
                        astro_status = f"⚠️ Error: {astro['error']}"
                    print(f"{site:30s} | {status:12s} | {astro_status}")
                    if astro.get("indicators"):
                        for ind in astro["indicators"]:
                            print(f"{'':32s} └─ {ind}")
        else:
            if args.output == "json":
                print(json.dumps(results, indent=2))
            else:
                for site, page in results.items():
                    status = f"Page {page}" if page else "Not found"
                    print(f"{site:30s} | {status}")


if __name__ == "__main__":
    asyncio.run(main())