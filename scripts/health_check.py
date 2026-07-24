#!/usr/bin/env python3
"""
StreamFlex Provider Health Check Script
Runs daily at 4am UTC via GitHub Actions.

For each provider:
  1. Resolve active domain
  2. Run test cases (search → verify results)
  3. Update health/health.json with results
"""

import json
import os
import sys
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
PROVIDERS_DIR = REPO_ROOT / "providers"
HEALTH_FILE = REPO_ROOT / "health" / "health.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

REQUEST_TIMEOUT = 15  # seconds

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✔ Saved {path.name}")

def check_domain(domain: str) -> bool:
    """Returns True if the domain responds with 2xx or 3xx."""
    try:
        r = requests.get(domain, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False

def resolve_active_domain(provider: dict) -> str | None:
    """Tries primary, then mirrors. Returns first working domain or None."""
    candidates = [provider["domains"]["primary"]] + provider["domains"].get("mirrors", [])
    for domain in candidates:
        print(f"    Trying domain: {domain}")
        if check_domain(domain):
            print(f"    ✔ Active: {domain}")
            return domain
        print(f"    ✗ Unreachable")
    return None

def run_search_test(provider: dict, test_case: dict, active_domain: str) -> bool:
    """
    Basic smoke test: verify that a search for the test case title
    returns at least 1 result. Full extractor pipeline is NOT run here.
    """
    try:
        search_type = provider["endpoints"]["searchType"]

        if search_type == "TYPESENSE_API":
            search_url = provider["domains"].get("search")
            if not search_url:
                return False
            # Typesense search
            params = {
                "q": test_case["title"],
                "query_by": "post_title",
                "per_page": 5
            }
            r = requests.get(search_url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            data = r.json()
            hits = data.get("hits", [])
            found = len(hits) > 0
            print(f"    Search '{test_case['title']}': {len(hits)} hit(s) — {'✔' if found else '✗'}")
            return found

        elif search_type == "HTML_PAGE":
            search_url = f"{active_domain}/?s={requests.utils.quote(test_case['title'])}"
            r = requests.get(search_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            # Very basic: check if title appears in HTML
            found = test_case["title"].lower() in r.text.lower()
            print(f"    Search '{test_case['title']}': {'✔ found in HTML' if found else '✗ not found'}")
            return found

        else:
            print(f"    Search type '{search_type}' not implemented in health check — skipping")
            return True  # Don't fail on unimplemented check types

    except Exception as e:
        print(f"    ✗ Search test error: {e}")
        return False

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"StreamFlex Provider Health Check — {now_iso()}")
    print(f"{'='*60}\n")

    # Load current health data
    health = load_json(HEALTH_FILE)
    health["_meta"]["lastChecked"] = now_iso()

    provider_files = list(PROVIDERS_DIR.glob("*.json"))
    print(f"Found {len(provider_files)} provider(s)\n")

    critical_failures = []

    for pf in sorted(provider_files):
        provider = load_json(pf)
        pid = provider["id"]

        print(f"[{pid.upper()}]")

        # Skip disabled providers
        if provider["lifecycle"] in ("disabled", "deprecated"):
            print(f"  ⏭ Skipping — lifecycle: {provider['lifecycle']}\n")
            continue

        # Initialize health entry if missing
        if pid not in health["providers"]:
            health["providers"][pid] = {
                "status": "unknown",
                "lastSuccess": None,
                "lastFailure": None,
                "consecutiveFailures": 0,
                "avgSearchResultCount": 0,
                "avgStreamCount": 0,
                "activeDomain": None
            }

        entry = health["providers"][pid]

        # Step 1: Resolve active domain
        print(f"  Resolving domain...")
        active_domain = resolve_active_domain(provider)

        if not active_domain:
            entry["status"] = "offline"
            entry["lastFailure"] = now_iso()
            entry["consecutiveFailures"] = entry.get("consecutiveFailures", 0) + 1
            entry["activeDomain"] = None
            print(f"  ✗ All domains unreachable — status: OFFLINE\n")
            critical_failures.append(pid)
            continue

        entry["activeDomain"] = active_domain

        # Step 2: Run test cases
        test_cases = provider.get("testCases", [])
        if not test_cases:
            print(f"  ⚠ No test cases defined\n")
            entry["status"] = "degraded"
            continue

        all_passed = True
        for tc in test_cases:
            passed = run_search_test(provider, tc, active_domain)
            if not passed:
                all_passed = False
                break
            time.sleep(1)  # Be polite

        if all_passed:
            entry["status"] = "online"
            entry["lastSuccess"] = now_iso()
            entry["consecutiveFailures"] = 0
            print(f"  ✔ Status: ONLINE\n")
        else:
            entry["status"] = "degraded"
            entry["lastFailure"] = now_iso()
            entry["consecutiveFailures"] = entry.get("consecutiveFailures", 0) + 1
            print(f"  ⚠ Status: DEGRADED\n")
            if entry["consecutiveFailures"] >= 3:
                entry["status"] = "offline"
                critical_failures.append(pid)

    # Save results
    save_json(HEALTH_FILE, health)

    print(f"\n{'='*60}")
    if critical_failures:
        print(f"❌ Critical failures: {', '.join(critical_failures)}")
        sys.exit(1)  # Triggers GitHub Actions issue creation
    else:
        print(f"✅ All providers checked successfully")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
