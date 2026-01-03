#!/usr/bin/env python3
"""
Scrape leads by industry and location using Apify.

Usage:
    python scrape_leads.py <industry> <location> [total_leads] [actor_id]

Arguments:
    industry: Target industry (e.g., "Software", "Plumbing")
    location: Target location (e.g., "San Francisco", "US")
    total_leads: Number of leads to scrape (default: 100)
    actor_id: Apify actor to use (default: compass/crawler-google-places)

Output:
    Saves leads to .tmp/leads_full.json
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from apify_client import ApifyClient

from .config import get_api_key

APIFY_TOKEN = get_api_key("APIFY_TOKEN")

def run_apify_scrape(industry, location, limit, output_file, actor_id="compass/crawler-google-places"):
    print(f"Scraping {limit} leads for '{industry}' in '{location}' using {actor_id}...")

    if not APIFY_TOKEN:
        print("Error: APIFY_TOKEN not found in .env")
        # For demo purposes, create a dummy file if no token
        dummy_data = [{"name": f"Company {i}", "industry": industry, "location": location} for i in range(limit)]
        with open(output_file, 'w') as f:
            json.dump(dummy_data, f, indent=2)
        print(f"Created dummy data at {output_file} (No API Token)")
        return

    client = ApifyClient(APIFY_TOKEN)

    run_input = {}

    if actor_id == "code_crafter/leads-finder":
        run_input = {
            "queries": [f"{industry} in {location}"],
            "maxItems": limit,
        }
    elif actor_id == "compass/crawler-google-places":
        run_input = {
            "searchStringsArray": [f"{industry} in {location}"],
            "locationQuery": location,
            "maxCrawledPlaces": limit,
            "language": "en",
        }
    else:
        print(f"Unknown actor ID: {actor_id}")
        return

    # Run the Actor and wait for it to finish
    try:
        run = client.actor(actor_id).call(run_input=run_input)
    except Exception as e:
        print(f"Error running actor {actor_id}: {e}")
        return

    # Fetch and save Actor results from the run's dataset (if there are any)
    print("Fetching results...")
    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        results.append(item)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Saved {len(results)} leads to {output_file}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python scrape_leads.py <industry> <location> [total_leads] [actor_id]")
        print("Supported actors: 'code_crafter/leads-finder', 'compass/google-maps-scraper'")
        sys.exit(1)

    industry = sys.argv[1]
    location = sys.argv[2]
    total_leads = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    actor_id = sys.argv[4] if len(sys.argv) > 4 else "compass/crawler-google-places"

    test_file = ".tmp/leads_test.json"
    full_file = ".tmp/leads_full.json"

    # Ensure .tmp directory exists
    os.makedirs(".tmp", exist_ok=True)

    # Step 1: Test Run
    print("--- Step 1: Test Run (25 leads) ---")
    run_apify_scrape(industry, location, 25, test_file, actor_id)

    # Step 2: Verification
    print("--- Step 2: Verification ---")
    # Call verify_leads.py
    try:
        subprocess.check_call([sys.executable, "tools/verify_leads.py", test_file, industry])
    except subprocess.CalledProcessError:
        print("Verification failed. Stopping workflow.")
        sys.exit(1)

    # Step 3: Full Run
    print(f"--- Step 3: Full Run ({total_leads} leads) ---")
    run_apify_scrape(industry, location, total_leads, full_file, actor_id)

    # Step 4: Update Sheets
    print("--- Step 4: Update Sheets ---")
    try:
        subprocess.check_call([sys.executable, "tools/update_sheets.py", full_file])
    except subprocess.CalledProcessError:
        print("Sheet update failed.")
        sys.exit(1)

    print("Workflow completed successfully.")

if __name__ == "__main__":
    main()
