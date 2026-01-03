# Activate Workflow
> Activate an n8n workflow to start automation.

## Variables
workflow_id: $1

## Run
./run tools/n8n_api.py activate "$workflow_id"

## Report
- Confirm the workflow was activated
- Report the workflow name
- Note the trigger type (schedule, webhook, etc.)
