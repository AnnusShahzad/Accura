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
    whitelist = {_normalize_rule(r["domain"]) for r in rules if r["rule_type"] == "whitelist"}
    blacklist = {_normalize_rule(r["domain"]) for r in rules if r["rule_type"] == "blacklist"}
    # YAML-level rules apply on top of the admin-managed ones
    whitelist |= {_normalize_rule(d) for d in settings.get("search.whitelist_domains", []) or []}
    blacklist |= {_normalize_rule(d) for d in settings.get("search.blacklist_domains", []) or []}
    return whitelist, blacklist


def _matches(domain: str, rules: set[str]) -> bool:
    """True if *domain* is one of *rules* or a subdomain of one."""
    return any(domain == r or domain.endswith("." + r) for r in rules)


def _normalize_rule(domain: str) -> str:
    domain = domain.strip().lower()
    if "://" in domain:
        domain = urlparse(domain).netloc
    return domain.removeprefix("www.").split("/")[0]


def _domain_allowed(url: str, whitelist: set[str], blacklist: set[str]) -> bool:
    domain = urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")
    if blacklist and _matches(domain, blacklist):
        return False
    if whitelist and not _matches(domain, whitelist):
        return False
    return True


async def google_search(query: str, num_results: int = 5, date_restrict: str | None = None) -> list[dict]:
    """Perform a Google Custom Search and return filtered results."""

    api_key = settings.get("search.google_api_key", "")
    cse_id = settings.get("search.google_cse_id", "")

    if not settings.get("search.enabled", True):
        return []
    if not api_key or not cse_id:
        # Previously this returned a fabricated "result" (complete with a
        # made-up weather report) that the model then cited as fact.
        logger.warning("Web search requested but GOOGLE_API_KEY / GOOGLE_CSE_ID are not set")
        return []

    whitelist, blacklist = await _get_domain_rules()

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        # Fetch extra so domain filtering still leaves enough results
        "num": 10,
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
