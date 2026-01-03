# Deploy Workflow
> Deploy a workflow from a local JSON file to n8n.

## Variables
json_path: $1

## Instructions
- Read `runbooks/n8n_workflow.md` for workflow management details
- Deploy the workflow JSON to the n8n instance
- For new workflows, use create; for existing, use update

## Run
```bash
# Create new workflow
./run tools/n8n_api.py create "$json_path"

# Or update existing (if ID known)
# ./run tools/n8n_api.py update <workflow_id> "$json_path"
```

## Report
- Confirm deployment succeeded
- Report the workflow ID
- Note if the workflow is active or inactive
