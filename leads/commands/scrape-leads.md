# Scrape Leads
> Scrape leads by industry and location using Apify.

## Variables
industry: $1
location: $2

## Instructions
- Read `runbooks/scrape_leads.md` for the full process
- Use Apify Google Maps scraper to find businesses
- Verify lead relevance (>80% threshold)
- Optionally export to Google Sheets

## Run
```bash
# Scrape leads
./run tools/scrape_leads.py "$industry" "$location"

# Verify scraped leads
./run tools/verify_leads.py .tmp/leads.json

# Upload to Google Sheets (optional)
./run tools/update_sheets.py .tmp/verified_leads.json
```

## Report
- Number of leads found
- Number that passed verification
- Top categories/types of businesses
- Google Sheets URL if exported
