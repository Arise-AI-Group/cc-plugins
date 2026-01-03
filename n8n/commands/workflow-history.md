# Workflow History
> View execution history for an n8n workflow.

## Variables
workflow_id: $1

## Run
./run tools/n8n_api.py executions "$workflow_id"

## Report
Format recent executions as a table:
| Execution ID | Started | Status | Duration |

Note any failures with error summaries.
