# Quick Start Guide

Get started with the Arise BMAD Extension in 5 minutes.

## Prerequisites

- Claude Code with plugin support
- Basic understanding of event-driven architecture concepts

## Step 1: Initialize Your Project

Run the initialization command in your project directory:

```
/modular-init
```

This will:
- Ask where to store architecture artifacts (`.bmad/` or `docs/`)
- Create the directory structure
- Set up initial configuration files

**Created files:**
- `architecture.md` - System design documentation
- `module-registry.yaml` - Module catalog
- `cloudevents-taxonomy.md` - Event type definitions
- `routing-rules.yaml` - Message routing configuration

## Step 2: Design Your Architecture

Ask the integration-architect agent to design your system:

```
Design a modular architecture for processing IoT sensor data with validation, enrichment, and alerting capabilities
```

The agent will:
- Analyze requirements
- Define module boundaries
- Create communication patterns
- Document event types

## Step 3: Create Your First Module

Create a sensor collector module:

```
/create-module sensor-collector collector
```

Choose your implementation platform:
- **n8n workflow** (recommended for quick start)
- **Python FastAPI**
- **JavaScript Express**

This creates:
- `modules/sensor-collector/asyncapi.yaml` - API contract
- `modules/sensor-collector/manifest.yaml` - Module metadata
- `modules/sensor-collector/workflow.json` (or implementation file)
- `modules/sensor-collector/README.md`

## Step 4: Create Additional Modules

```
/create-module data-validator validator
/create-module data-enricher enricher
/create-module alert-manager processor
```

## Step 5: Create the Router

```
/create-router
```

The router handles message distribution based on CloudEvents `type` field.

## Step 6: Update Routing Rules

Edit `routing-rules.yaml` to define how messages flow:

```yaml
rules:
  - pattern: "com.arise.sensor.*.reading.v1"
    destination: "data-validator-v1"

  - pattern: "com.arise.sensor.*.validated.v1"
    destination: "data-enricher-v1"

  - pattern: "com.arise.sensor.*.enriched.v1"
    destinations:
      - module: "alert-manager-v1"
        weight: 100
```

## Step 7: Validate Your System

```
/validate-contracts
```

This checks:
- All modules have AsyncAPI specs
- CloudEvents format compliance
- Event type naming conventions
- Schema completeness
- Routing coverage

## Next Steps

1. **Customize AsyncAPI specs** - Add your actual data schemas
2. **Implement business logic** - Fill in the TODO sections in module code
3. **Add tests** - Use the integration-tester agent
4. **Deploy** - Export n8n workflows or deploy Python/JS modules

## Example: Complete Sensor Processing System

```
# Initialize
/modular-init

# Create modules
/create-module sensor-collector collector
/create-module data-validator validator
/create-module alert-manager processor
/create-module time-series-writer writer

# Create router
/create-router

# Validate
/validate-contracts
```

## Getting Help

- Ask any of the specialized agents for guidance
- Read the [AsyncAPI Guide](asyncapi-guide.md) for contract details
- Read the [CloudEvents Guide](cloudevents-guide.md) for message format
