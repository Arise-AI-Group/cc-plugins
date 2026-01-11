---
name: leads
description: This skill should be used when the user asks to "scrape leads", "find businesses in area", "get sales leads", "search for companies". Scrapes and verifies sales leads via Apify and uploads to Google Sheets.
---

# Scrape Leads Directive

## Goal
Scrape leads from a specified industry and location, verify their relevance, and upload them to a Google Sheet.

## Inputs
- **Industry**: Target industry (e.g., "Software", "Plumbing")
- **Location**: Target location (e.g., "San Francisco", "US")
- **Job Title**: (Optional) Specific job title to target
- **Total Leads**: Number of leads to scrape (default: 100)

## Process

1. **Test Run**: Fetch a small sample (~25 leads) to validate search parameters
2. **Verification**: Check if >80% of leads match the target industry
3. **Full Run**: If verification passes, scrape the full `Total Leads` count. If it fails, STOP and ask user for refined keywords/filters.
4. **Upload**: Push results to Google Sheets and return the URL

## Outputs
- Google Sheet URL containing the verified leads

## Edge Cases
- If verification fails (<80% relevance), stop and ask user for refined keywords
- If API rate limits hit, implement backoff and retry
- If Google Sheets auth fails, save to `.tmp/` and notify user

---

## Implementation

**Scripts:**
- `tool/scrape_leads.py` - Main orchestration script
- `tool/verify_leads.py` - Verifies lead relevance
- `tool/update_sheets.py` - Uploads data to Google Sheets

**Usage:**
```bash
./run tools/scrape_leads.py <industry> <location> [total_leads] [actor_id]
```

**Notes:**
- Uses Apify client library (`apify-client`)
- Actor ID options:
  - `compass/google-maps-scraper` (Free plan friendly, default)
  - `code_crafter/leads-finder` (Paid plan only)
- Requires `APIFY_TOKEN` in `.env`
- Test run saves to `.tmp/leads_test.json`
- Full run saves to `.tmp/leads_full.json`

