# Create Router
> Create the hub router workflow for message routing and distribution.

## Instructions

Create a central hub router that routes CloudEvents messages to appropriate modules.

### Step 1: Find Architecture Directory

Look for the architecture directory:
1. Check if `.bmad/` exists
2. Check if `docs/` exists with architecture files
3. If neither, run `/modular-init` first

### Step 2: Read Module Registry

Read `<arch-dir>/module-registry.yaml` to understand:
- What modules exist
- Their endpoints
- Their input/output types

### Step 3: Read Routing Rules

Read `<arch-dir>/routing-rules.yaml` to understand:
- Existing routing patterns
- A/B routing configurations
- Default behaviors

### Step 4: Ask Implementation Platform

Ask the user:
- "Which platform should I create the router for?"
- Options:
  - **n8n workflow** (Recommended) - n8n JSON workflow
  - **Python FastAPI** - Python router application
  - **JavaScript Express** - Node.js router application

### Step 5: Create Router Directory

```bash
mkdir -p <arch-dir>/router
```

### Step 6: Create Router Implementation

**If n8n:**

Read template from: `arise-bmad-extension/templates/n8n/router-workflow.json`

Create `<arch-dir>/router/workflow.json` with:

```json
{
  "name": "Hub Router",
  "nodes": [
    {
      "name": "Webhook Receiver",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "httpMethod": "POST",
        "path": "route",
        "responseMode": "responseNode"
      }
    },
    {
      "name": "Validate CloudEvents",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": "// Validate CloudEvents format\nconst event = $json;\n\nif (!event.specversion || event.specversion !== '1.0') {\n  throw new Error('Invalid CloudEvents version');\n}\nif (!event.type || !event.source || !event.id) {\n  throw new Error('Missing required CloudEvents fields');\n}\n\nreturn { json: event };"
      }
    },
    {
      "name": "Route by Type",
      "type": "n8n-nodes-base.switch",
      "parameters": {
        "rules": [
          // Generated based on routing-rules.yaml
        ]
      }
    },
    {
      "name": "Forward to Module",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "={{$json.targetEndpoint}}",
        "method": "POST",
        "bodyContentType": "json"
      }
    }
  ]
}
```

**If Python:**

Create `<arch-dir>/router/main.py`:

```python
"""
Hub Router - Central message routing for modular architecture
"""
from fastapi import FastAPI, HTTPException
import httpx
import yaml
import re

app = FastAPI(title="Hub Router")

# Load routing rules
with open('routing-rules.yaml') as f:
    ROUTING_CONFIG = yaml.safe_load(f)

# Load module registry
with open('module-registry.yaml') as f:
    MODULE_REGISTRY = yaml.safe_load(f)

@app.post("/route")
async def route_message(event: dict):
    """Route CloudEvents message to appropriate module(s)"""

    # Validate CloudEvents
    if event.get('specversion') != '1.0':
        raise HTTPException(400, "Invalid CloudEvents version")

    event_type = event.get('type')
    if not event_type:
        raise HTTPException(400, "Missing event type")

    # Find matching rules
    destinations = find_destinations(event_type)

    if not destinations:
        # Send to dead letter
        return {"routed_to": "dead-letter", "event_type": event_type}

    # Forward to destinations
    results = []
    async with httpx.AsyncClient() as client:
        for dest in destinations:
            endpoint = get_module_endpoint(dest['module'])
            response = await client.post(endpoint, json=event)
            results.append({
                "module": dest['module'],
                "status": response.status_code
            })

    return {"routed_to": results}

def find_destinations(event_type: str) -> list:
    """Find destination modules based on event type"""
    for rule in ROUTING_CONFIG.get('rules', []):
        pattern = rule['pattern'].replace('*', '.*')
        if re.match(pattern, event_type):
            if 'destinations' in rule:
                return rule['destinations']
            return [{'module': rule['destination'], 'weight': 100}]
    return []

def get_module_endpoint(module_id: str) -> str:
    """Get process endpoint for module"""
    for module in MODULE_REGISTRY.get('modules', []):
        if module['id'] == module_id:
            return module['endpoints']['process']
    raise ValueError(f"Module not found: {module_id}")

@app.get("/health")
async def health():
    return {"status": "healthy", "component": "hub-router"}
```

**If JavaScript:**

Create `<arch-dir>/router/server.js`:

```javascript
const express = require('express');
const axios = require('axios');
const yaml = require('js-yaml');
const fs = require('fs');

const app = express();
app.use(express.json());

// Load configuration
const routingConfig = yaml.load(fs.readFileSync('routing-rules.yaml', 'utf8'));
const moduleRegistry = yaml.load(fs.readFileSync('module-registry.yaml', 'utf8'));

app.post('/route', async (req, res) => {
  const event = req.body;

  // Validate CloudEvents
  if (event.specversion !== '1.0') {
    return res.status(400).json({ error: 'Invalid CloudEvents version' });
  }

  const eventType = event.type;
  if (!eventType) {
    return res.status(400).json({ error: 'Missing event type' });
  }

  // Find destinations
  const destinations = findDestinations(eventType);

  if (destinations.length === 0) {
    return res.json({ routed_to: 'dead-letter', event_type: eventType });
  }

  // Forward to destinations
  const results = await Promise.all(
    destinations.map(async (dest) => {
      const endpoint = getModuleEndpoint(dest.module);
      const response = await axios.post(endpoint, event);
      return { module: dest.module, status: response.status };
    })
  );

  res.json({ routed_to: results });
});

function findDestinations(eventType) {
  for (const rule of routingConfig.rules || []) {
    const pattern = new RegExp(rule.pattern.replace(/\*/g, '.*'));
    if (pattern.test(eventType)) {
      if (rule.destinations) return rule.destinations;
      return [{ module: rule.destination, weight: 100 }];
    }
  }
  return [];
}

function getModuleEndpoint(moduleId) {
  const module = moduleRegistry.modules.find(m => m.id === moduleId);
  if (!module) throw new Error(`Module not found: ${moduleId}`);
  return module.endpoints.process;
}

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', component: 'hub-router' });
});

app.listen(3000, () => console.log('Hub Router listening on port 3000'));
```

### Step 7: Create Router AsyncAPI Spec

Create `<arch-dir>/router/asyncapi.yaml`:

```yaml
asyncapi: '3.0.0'
info:
  title: Hub Router
  version: '1.0.0'
  description: Central message router for modular architecture

channels:
  route:
    address: /route
    description: Main routing endpoint
    messages:
      cloudEvent:
        contentType: application/cloudevents+json
        payload:
          $ref: '#/components/schemas/CloudEvent'

operations:
  routeMessage:
    action: receive
    channel:
      $ref: '#/channels/route'

components:
  schemas:
    CloudEvent:
      type: object
      required: [specversion, type, source, id, data]
      properties:
        specversion:
          type: string
          const: "1.0"
        type:
          type: string
        source:
          type: string
        id:
          type: string
        time:
          type: string
        data:
          type: object
```

### Step 8: Update Module Registry

Update `<arch-dir>/module-registry.yaml` router section:

```yaml
router:
  type: "hub-and-spoke"
  implementation: "<platform>"
  status: "created"
  endpoints:
    health: "http://localhost:3000/health"
    route: "http://localhost:3000/route"
```

### Step 9: Report Success

Report:
- Created router directory
- Created router implementation
- Created router asyncapi.yaml
- Updated module-registry.yaml
- Explain how to run the router
- Suggest updating routing-rules.yaml with actual rules
