"""
Accura – Search Service
Google Custom Search integration with domain whitelist/blacklist support.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from config import settings
from models.admin import DomainRule

logger = logging.getLogger("accura.search_service")


async def _get_domain_rules() -> tuple[set[str], set[str]]:
    """Load whitelist and blacklist domains from DB."""
    rules = await DomainRule.select().run()
    whitelist = {r["domain"] for r in rules if r["rule_type"] == "whitelist"}
    blacklist = {r["domain"] for r in rules if r["rule_type"] == "blacklist"}
    return whitelist, blacklist


def _domain_allowed(url: str, whitelist: set[str], blacklist: set[str]) -> bool:
    domain = urlparse(url).netloc.lower()
    if blacklist and domain in blacklist:
        return False
    if whitelist and domain not in whitelist:
        return False
    return True


async def google_search(query: str, num_results: int = 5, date_restrict: str | None = None) -> list[dict]:
    """Perform a Google Custom Search and return filtered results."""

    api_key = settings.get("search.google_api_key", "")
    cse_id = settings.get("search.google_cse_id", "")

    if not api_key or not cse_id:
        logger.warning("Google Search API not configured, returning mock results")
        return [
            {
                "title": f"Live Search Result for: {query}",
                "snippet": f"This is a mocked live web search result since API keys are missing. The user searched for: {query}. It is currently sunny and 35°C in Lahore.",
                "url": "https://example.com/mock-search-result"
            }
        ]

    whitelist, blacklist = await _get_domain_rules()

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": min(num_results, 10),
    }
    if date_restrict:
        params["dateRestrict"] = date_restrict

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("Google search failed")
        return []

    results = []
    for item in data.get("items", []):
        link = item.get("link", "")
        if not _domain_allowed(link, whitelist, blacklist):
            continue
        results.append({
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "url": link,
        })

    return results[:num_results]
