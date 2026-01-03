# Tunnel Status
> Check Cloudflare tunnel configuration and status.

## Instructions
- Query Cloudflare API for tunnel ingress rules
- Show all configured routes and their targets

## Run
./run tools/cloudflare_api.py tunnel list

## Report
Format as a table showing:
| Hostname | Service | Status |

Include:
- Total number of routes
- Any routes that may be misconfigured
