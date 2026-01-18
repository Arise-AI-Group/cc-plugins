# Initialize Modular Architecture
> Initialize a project with BMAD modular architecture structure.

## Variables
project_name: $1

## Instructions

Initialize the project with modular architecture scaffolding.

### Step 1: Determine Output Location

Ask the user where to store architecture artifacts:

Use AskUserQuestion:
- **Question**: "Where should I store the architecture artifacts?"
- **Options**:
  - `.bmad/` - BMAD-specific directory (Recommended)
  - `docs/` - Standard documentation directory

### Step 2: Create Directory Structure

Based on user choice, create:

**If `.bmad/` chosen:**
```bash
mkdir -p .bmad/{asyncapi-specs,modules,router}
```

**If `docs/` chosen:**
```bash
mkdir -p docs/{asyncapi-specs,modules,router}
```

### Step 3: Create Architecture Document

Create the main architecture document:

```markdown
# Modular Architecture

## Overview

This project uses BMAD modular architecture with:
- **AsyncAPI 3.0** for API contracts
- **CloudEvents v1.0** for message format
- **Hub-and-Spoke** pattern for message routing

## Project Structure

```
<output-dir>/
├── architecture.md          # This file
├── module-registry.yaml     # Module catalog
├── cloudevents-taxonomy.md  # Event type definitions
├── routing-rules.yaml       # Message routing configuration
├── asyncapi-specs/          # AsyncAPI specifications
│   └── <module-name>.yaml
├── modules/                 # Module implementations
│   └── <module-name>/
│       ├── asyncapi.yaml
│       ├── manifest.yaml
│       └── ...
└── router/                  # Hub router
    └── workflow.json
```

## Communication Standards

### CloudEvents Format
All messages use CloudEvents v1.0:
- `specversion`: "1.0"
- `type`: "com.arise.<domain>.<action>.v<version>"
- `source`: "<module-id>"
- `id`: "<uuid>"
- `time`: "<ISO-8601>"
- `data`: { ... }

### Event Type Convention
```
com.arise.<domain>.<entity>.<action>.v<version>
```

## Modules

| Module | Type | Status | Description |
|--------|------|--------|-------------|
| (none yet) | | | |

## Next Steps

1. Design your architecture: Ask the integration-architect agent
2. Create modules: `/create-module <name> <type>`
3. Generate AsyncAPI specs: `/generate-asyncapi <module>`
4. Create router: `/create-router`
5. Validate contracts: `/validate-contracts`
```

### Step 4: Create Module Registry

```yaml
# module-registry.yaml
version: "1.0"
project: "{{PROJECT_NAME}}"
created: "{{TIMESTAMP}}"

modules: []
  # Example entry:
  # - id: "sensor-collector-v1"
  #   name: "Sensor Collector"
  #   type: "collector"
  #   version: "1.0.0"
  #   status: "development"
  #   endpoints:
  #     health: "http://localhost:3001/health"
  #     process: "http://localhost:3001/process"

router:
  type: "hub-and-spoke"
  implementation: "n8n"
  status: "not-created"
```

### Step 5: Create CloudEvents Taxonomy

```markdown
# CloudEvents Taxonomy

## Naming Convention

```
com.arise.<domain>.<entity>.<action>.v<version>
```

## Defined Event Types

(No event types defined yet. Add them as you create modules.)

### Example Format

```
### <Domain> Domain

- `com.arise.<domain>.<entity>.<action>.v1`
  - **Source**: <module-id>
  - **Data Schema**: <schema-reference>
  - **Description**: <what this event represents>
```
```

### Step 6: Create Routing Rules

```yaml
# routing-rules.yaml
version: "1.0"

# Default routing behavior
defaults:
  unmatched: "dead-letter"
  retry_count: 3
  retry_delay_ms: 1000

# Routing rules (evaluated in order)
rules: []
  # Example:
  # - pattern: "com.arise.sensor.*.reading.v1"
  #   destination: "data-validator-v1"
  #   weight: 100
  #
  # - pattern: "com.arise.sensor.*.validated.v1"
  #   destinations:
  #     - module: "data-enricher-v1"
  #       weight: 80
  #     - module: "data-enricher-v2"
  #       weight: 20  # A/B test

# Dead letter configuration
dead_letter:
  enabled: true
  retention_days: 7
```

### Step 7: Report Success

Report to user:
- Created directory structure
- Created architecture.md
- Created module-registry.yaml
- Created cloudevents-taxonomy.md
- Created routing-rules.yaml
- Suggest next steps (design architecture, create modules)
