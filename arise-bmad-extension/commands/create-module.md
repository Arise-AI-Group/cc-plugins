# Create Module
> Create a new module with AsyncAPI spec and implementation scaffold.

## Variables
module_name: $1
module_type: $2

## Instructions

Create a new module with the specified name and type.

### Step 1: Validate Input

If `module_name` is not provided, ask the user:
- "What should the module be named?" (e.g., sensor-collector, data-validator)

If `module_type` is not provided, ask the user with options:
- **collector** - Receives external data
- **validator** - Validates data against schemas
- **enricher** - Adds contextual information
- **processor** - Business logic processing
- **writer** - Persists data to storage

### Step 2: Find Architecture Directory

Look for the architecture directory:
1. Check if `.bmad/` exists
2. Check if `docs/asyncapi-specs/` exists
3. If neither, run `/modular-init` first

### Step 3: Create Module Directory

```bash
mkdir -p <arch-dir>/modules/<module-name>
```

### Step 4: Create AsyncAPI Specification

Read template from: `arise-bmad-extension/templates/asyncapi/module-template.yaml`

Create `<arch-dir>/modules/<module-name>/asyncapi.yaml`:

Replace placeholders:
- `{{MODULE_NAME}}` - Capitalized module name (e.g., "Sensor Collector")
- `{{MODULE_ID}}` - Lowercase with dashes (e.g., "sensor-collector-v1")
- `{{VERSION}}` - "1.0.0"
- `{{DESCRIPTION}}` - Based on module type
- `{{PORT}}` - Auto-assign (3001, 3002, etc.)

Also copy to `<arch-dir>/asyncapi-specs/<module-name>.yaml`

### Step 5: Create Manifest

Create `<arch-dir>/modules/<module-name>/manifest.yaml`:

```yaml
module:
  id: "<module-name>-v1"
  name: "<Module Name>"
  version: "1.0.0"
  type: "<module-type>"

capabilities:
  # Based on type:
  # collector: receive_data, validate_format, forward_to_router
  # validator: validate_schema, enrich_metadata, forward_validated
  # enricher: load_context, enrich_data, forward_enriched
  # processor: process_data, apply_rules, generate_output
  # writer: receive_data, persist, acknowledge

endpoints:
  health: "http://localhost:<port>/health"
  process: "http://localhost:<port>/process"
  schema: "http://localhost:<port>/schema"
  manifest: "http://localhost:<port>/manifest"

routing:
  subscribe_to:
    - "<input-topic>"
  publish_to:
    - "<output-topic>"

versioning:
  current_version: "1.0.0"
  supported_versions: ["1.0.0"]
  deprecated: false
```

### Step 6: Ask Implementation Platform

Ask the user:
- "Which platform should I scaffold the implementation for?"
- Options:
  - **n8n workflow** (Recommended) - n8n JSON workflow
  - **Python FastAPI** - Python with FastAPI
  - **JavaScript Express** - Node.js with Express
  - **Spec only** - Just the AsyncAPI spec, no implementation

### Step 7: Create Implementation Scaffold

**If n8n:**
- Read template from `arise-bmad-extension/templates/n8n/module-workflow.json`
- Replace placeholders
- Save to `<arch-dir>/modules/<module-name>/workflow.json`

**If Python:**
- Read template from `arise-bmad-extension/templates/python/module-fastapi.py`
- Replace placeholders
- Save to `<arch-dir>/modules/<module-name>/main.py`
- Copy `requirements.txt`

**If JavaScript:**
- Read template from `arise-bmad-extension/templates/javascript/module-express.js`
- Replace placeholders
- Save to `<arch-dir>/modules/<module-name>/server.js`
- Copy `package.json`

### Step 8: Create README

Create `<arch-dir>/modules/<module-name>/README.md`:

```markdown
# <Module Name>

## Type
<module-type>

## Description
<based on type>

## AsyncAPI Specification
See: asyncapi.yaml

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /health | GET | Health check |
| /process | POST | Process CloudEvents message |
| /schema | GET | Return AsyncAPI spec |
| /manifest | GET | Return module manifest |

## CloudEvents

### Input
- Type: `com.arise.<domain>.<input-action>.v1`

### Output
- Type: `com.arise.<domain>.<output-action>.v1`

## Development

<platform-specific instructions>

## Testing

```bash
# Run contract tests
npx jest tests/contract/<module-name>.test.js
```
```

### Step 9: Update Module Registry

Add entry to `<arch-dir>/module-registry.yaml`:

```yaml
- id: "<module-name>-v1"
  name: "<Module Name>"
  type: "<module-type>"
  version: "1.0.0"
  status: "development"
  endpoints:
    health: "http://localhost:<port>/health"
    process: "http://localhost:<port>/process"
```

### Step 10: Report Success

Report:
- Created module directory
- Created asyncapi.yaml
- Created manifest.yaml
- Created implementation scaffold (if selected)
- Created README.md
- Updated module-registry.yaml
- Suggest: customize asyncapi.yaml with actual schemas, implement business logic
