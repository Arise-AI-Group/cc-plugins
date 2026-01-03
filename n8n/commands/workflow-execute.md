# Execute Workflow
> Test run an n8n workflow manually.

## Variables
workflow_id: $1

## Run
./run tools/n8n_api.py execute "$workflow_id"

## Report
- Confirm execution started
- Report execution status (success/failure)
- Summarize any output or errors
