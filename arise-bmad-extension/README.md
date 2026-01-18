# Arise BMAD Extension

BMAD methodology extension for designing and implementing modular, event-driven integration architectures using AsyncAPI and CloudEvents standards.

## Overview

This plugin extends BMAD with industry-standard patterns for:
- **AsyncAPI 3.0** - Contract-first API design for event-driven systems
- **CloudEvents v1.0** - Standardized message envelope format
- **Hub-and-Spoke** - Central router pattern for message distribution
- **A/B Routing** - Version-based traffic management

## Installation

```bash
/plugin install /path/to/cc-plugins/arise-bmad-extension
```

## Quick Start

1. **Initialize your project:**
   ```
   /modular-init
   ```

2. **Design your architecture:**
   Ask the integration-architect agent to design your system.

3. **Create modules:**
   ```
   /create-module sensor-collector collector
   /create-module data-validator validator
   ```

4. **Create the router:**
   ```
   /create-router
   ```

5. **Validate contracts:**
   ```
   /validate-contracts
   ```

## Commands

| Command | Description |
|---------|-------------|
| `/modular-init` | Initialize project with modular architecture structure |
| `/create-module <name> <type>` | Create new module with AsyncAPI spec |
| `/create-router` | Create hub router workflow |
| `/generate-asyncapi <module>` | Generate AsyncAPI specification |
| `/validate-contracts` | Validate all module contracts |

## Agents

| Agent | Use For |
|-------|---------|
| `integration-architect` | System design, module boundaries, routing strategy |
| `module-developer` | Implementing modules in n8n, Python, or JavaScript |
| `api-contract-designer` | Creating AsyncAPI specs and message schemas |
| `integration-tester` | Contract tests and CloudEvents validation |

## Module Types

- **collector** - Receives external data
- **validator** - Validates data against schemas
- **enricher** - Adds contextual information
- **processor** - Business logic processing
- **writer** - Persists data to storage

## Documentation

- [Quick Start Guide](docs/quick-start.md)
- [AsyncAPI Guide](docs/asyncapi-guide.md)
- [CloudEvents Guide](docs/cloudevents-guide.md)

## Templates

The plugin includes ready-to-use templates:
- AsyncAPI module and router specifications
- CloudEvents message format and validation schemas
- n8n workflow templates
- Python FastAPI module template
- JavaScript Express module template

## License

MIT
