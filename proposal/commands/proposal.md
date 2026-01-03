# Generate Proposal
> Generate a sales proposal and create Google Slides presentation.

## Variables
company_info: $ARGUMENTS

## Instructions
- Read `runbooks/generate_proposal.md` for the full process
- Parse the company information provided
- Generate proposal JSON and create slides from template
- Use the GOOGLE_SLIDES_TEMPLATE_ID env var or ask user for template ID

## Input Format
Provide company info as structured text or JSON:
- Company name
- Industry
- Pain points
- Proposed solution
- Key metrics

## Run
```bash
# Generate proposal JSON and pipe to slides generator
echo '$company_info' | ./run tools/generate_proposal.py | ./run tools/copy_slides_template.py $GOOGLE_SLIDES_TEMPLATE_ID
```

## Report
- Confirm the presentation was created
- Report the Google Slides URL
- Summarize the proposal content
