---
name: arise-bmad-extension
description: This skill should be used when the user asks to "design modular architecture", "create AsyncAPI spec", "implement CloudEvents module", "set up n8n integration", "configure A/B routing", "create event-driven system". Provides BMAD methodology extension for event-driven modular architectures using AsyncAPI and CloudEvents standards.
---

# Arise BMAD Extension

BMAD methodology extension for designing and implementing modular, event-driven integration architectures using industry standards.

## Core Standards

- **AsyncAPI 3.0**: Contract-first API design for event-driven systems
- **CloudEvents v1.0**: Standardized message envelope format
- **Hub-and-Spoke**: Central router pattern for message distribution
- **A/B Routing**: Version-based traffic management

## Available Commands

| Command | Purpose |
|---------|---------|
| `/modular-init` | Initialize project with modular architecture structure |
| `/create-module <name> <type>` | Create new module with AsyncAPI spec |
| `/create-router` | Create hub router workflow |
| `/generate-asyncapi <module>` | Generate AsyncAPI specification |
| `/validate-contracts` | Validate all module contracts |

## Available Agents

| Agent | Use When |
|-------|----------|
| `integration-architect` | Designing system architecture, defining module boundaries |
| `module-developer` | Implementing modules in n8n, Python, or JavaScript |
| `api-contract-designer` | Creating AsyncAPI specs and message schemas |
| `integration-tester` | Creating contract tests, validating compliance |

## Quick Start

1. **Initialize Project**
   ```
   /modular-init
   ```
   Creates project structure with module registry and architecture docs.

2. **Design Architecture**
   Ask the integration-architect agent to design your system:
   ```
   Design a modular architecture for processing sensor data with validation, enrichment, and alerting
   ```

3. **Create Modules**
   ```
   /create-module sensor-collector collector
   /create-module data-validator validator
   /create-module alert-manager processor
   ```

4. **Generate AsyncAPI Specs**
   ```
   /generate-asyncapi sensor-collector
   ```

5. **Validate Contracts**
   ```
   /validate-contracts
   ```

## CloudEvents Message Format

All modules use CloudEvents v1.0 format:

```json
{
  "specversion": "1.0",
  "type": "com.arise.<domain>.<action>.v1",
  "source": "<module-id>",
  "id": "<uuid>",
  "time": "<ISO-8601>",
  "datacontenttype": "application/json",
  "data": { ... }
}
```

## Event Type Naming Convention

```
com.arise.<domain>.<entity>.<action>.v<version>

Examples:
- com.arise.sensor.temperature.reading.v1
- com.arise.sensor.temperature.validated.v1
- com.arise.alert.threshold.exceeded.v1
```

## Module Types

- **collector**: Receives external data, validates format
- **validator**: Validates data against schemas
- **enricher**: Adds contextual information
- **processor**: Business logic processing
- **router**: Message routing and distribution
- **writer**: Persists data to storage

## Architecture Patterns

### Hub-and-Spoke (Recommended for <10 modules)
Central router distributes messages based on CloudEvents `type` field.

### Event Mesh (For >20 modules)
Distributed routing with multiple brokers.

### Direct Pub/Sub (Simple fan-out)
Static subscriptions without routing logic.

## Templates Location

Templates are in the plugin's `templates/` directory:
- `templates/asyncapi/` - AsyncAPI specification templates
- `templates/cloudevents/` - CloudEvents message templates
- `templates/n8n/` - n8n workflow templates
- `templates/python/` - FastAPI module templates
- `templates/javascript/` - Express module templates

## Environment Variables

No environment variables required for basic usage.

For n8n integration, ensure n8n plugin is configured.
