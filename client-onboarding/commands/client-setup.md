# Client Setup
> Onboard a new client following the client_onboarding runbook.

## Variables
slug: $1
display_name: $2

## Instructions
- Read `runbooks/client_onboarding.md` for the full process
- Execute the client setup command
- This creates:
  1. `#slug` channel (public, for client communication)
  2. `#slug-internal` channel (public, for internal discussion)
  3. Canvas from template in the main channel
  4. Welcome message (posted and pinned)

## Run
./run tools/slack_api.py client setup "$slug" --display-name "$display_name"

## Report
- Summarize what was created
- List the channel URLs
- Note any manual follow-up steps needed (inviting guests, etc.)
