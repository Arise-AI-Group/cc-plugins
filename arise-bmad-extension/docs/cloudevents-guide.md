# CloudEvents Implementation Guide

This guide explains how to implement CloudEvents v1.0 in your modular architecture.

## What is CloudEvents?

CloudEvents is a specification for describing event data in a common way. It provides:

- **Interoperability** - Standard format across all modules
- **Portability** - Works with any messaging system
- **Traceability** - Built-in support for correlation and tracing

## CloudEvents v1.0 Format

Every message in the system uses this format:

```json
{
  "specversion": "1.0",
  "type": "com.arise.sensor.temperature.reading.v1",
  "source": "sensor-collector-v1",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "time": "2026-01-17T10:30:00Z",
  "datacontenttype": "application/json",
  "data": {
    "sensorId": "temp-01",
    "value": 72.5,
    "unit": "fahrenheit"
  }
}
```

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `specversion` | string | Always "1.0" |
| `type` | string | Event type identifier |
| `source` | string | Module that produced the event |
| `id` | string | Unique event identifier (UUID) |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `time` | string | ISO 8601 timestamp |
| `datacontenttype` | string | Content type of data (usually "application/json") |
| `dataschema` | string | URI of the schema |
| `subject` | string | Subject of the event |

## Extension Attributes

You can add custom attributes. We use:

| Field | Type | Description |
|-------|------|-------------|
| `correlationid` | string | ID of the original triggering event |
| `traceparent` | string | W3C Trace Context for distributed tracing |

## Event Type Naming

Follow this convention:

```
com.arise.<domain>.<entity>.<action>.v<version>
```

**Components:**
- `com.arise` - Organization prefix
- `<domain>` - Business domain (sensor, order, alert, etc.)
- `<entity>` - Entity within domain (temperature, customer, threshold)
- `<action>` - What happened (reading, validated, placed, exceeded)
- `v<version>` - Schema version (v1, v2, etc.)

**Examples:**
```
com.arise.sensor.temperature.reading.v1
com.arise.sensor.temperature.validated.v1
com.arise.sensor.temperature.enriched.v1
com.arise.alert.threshold.exceeded.v1
com.arise.order.customer.placed.v1
com.arise.order.payment.processed.v1
```

## Implementation Examples

### JavaScript/n8n

```javascript
// Creating a CloudEvent
const createCloudEvent = (data, eventType, sourceModule) => ({
  specversion: '1.0',
  type: eventType,
  source: sourceModule,
  id: crypto.randomUUID(),
  time: new Date().toISOString(),
  datacontenttype: 'application/json',
  data: data
});

// With correlation
const createCorrelatedEvent = (data, eventType, sourceModule, correlationId) => ({
  ...createCloudEvent(data, eventType, sourceModule),
  correlationid: correlationId
});

// Usage
const event = createCloudEvent(
  { sensorId: 'temp-01', value: 72.5 },
  'com.arise.sensor.temperature.validated.v1',
  'data-validator-v1'
);
```

### Python

```python
from datetime import datetime, timezone
import uuid

def create_cloud_event(data: dict, event_type: str, source: str) -> dict:
    return {
        "specversion": "1.0",
        "type": event_type,
        "source": source,
        "id": str(uuid.uuid4()),
        "time": datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data": data
    }

def create_correlated_event(data: dict, event_type: str, source: str, correlation_id: str) -> dict:
    event = create_cloud_event(data, event_type, source)
    event["correlationid"] = correlation_id
    return event

# Usage
event = create_cloud_event(
    {"sensorId": "temp-01", "value": 72.5},
    "com.arise.sensor.temperature.validated.v1",
    "data-validator-v1"
)
```

### Using CloudEvents SDK

**Python:**
```python
from cloudevents.http import CloudEvent, to_structured

event = CloudEvent({
    "type": "com.arise.sensor.temperature.reading.v1",
    "source": "sensor-collector-v1",
    "data": {"sensorId": "temp-01", "value": 72.5}
})

# Serialize for HTTP
headers, body = to_structured(event)
```

**JavaScript:**
```javascript
const { CloudEvent } = require('cloudevents');

const event = new CloudEvent({
  type: 'com.arise.sensor.temperature.reading.v1',
  source: 'sensor-collector-v1',
  data: { sensorId: 'temp-01', value: 72.5 }
});
```

## Validation

### JavaScript (ajv)

```javascript
const Ajv = require('ajv');
const addFormats = require('ajv-formats');

const ajv = new Ajv();
addFormats(ajv);

const cloudEventSchema = {
  type: 'object',
  required: ['specversion', 'type', 'source', 'id'],
  properties: {
    specversion: { type: 'string', const: '1.0' },
    type: { type: 'string', minLength: 1 },
    source: { type: 'string', minLength: 1 },
    id: { type: 'string', minLength: 1 },
    time: { type: 'string', format: 'date-time' },
    data: { type: 'object' }
  }
};

const validate = ajv.compile(cloudEventSchema);

function validateCloudEvent(event) {
  const valid = validate(event);
  if (!valid) {
    throw new Error(`Invalid CloudEvent: ${ajv.errorsText(validate.errors)}`);
  }
  return true;
}
```

### Python (jsonschema)

```python
import jsonschema

CLOUD_EVENT_SCHEMA = {
    "type": "object",
    "required": ["specversion", "type", "source", "id"],
    "properties": {
        "specversion": {"type": "string", "const": "1.0"},
        "type": {"type": "string", "minLength": 1},
        "source": {"type": "string", "minLength": 1},
        "id": {"type": "string", "minLength": 1},
        "time": {"type": "string", "format": "date-time"},
        "data": {"type": "object"}
    }
}

def validate_cloud_event(event: dict) -> bool:
    jsonschema.validate(instance=event, schema=CLOUD_EVENT_SCHEMA)
    return True
```

## Routing by Event Type

The hub router uses the `type` field for routing:

```yaml
# routing-rules.yaml
rules:
  - pattern: "com.arise.sensor.*.reading.v1"
    destination: "data-validator-v1"

  - pattern: "com.arise.sensor.*.validated.v1"
    destinations:
      - module: "data-enricher-v1"
        weight: 80
      - module: "data-enricher-v2"
        weight: 20  # A/B test
```

## Correlation and Tracing

Use `correlationid` to trace events through the system:

```
Original Event (sensor-collector)
├── id: "event-001"
└── data: {...}

Processed Event (data-validator)
├── id: "event-002"
├── correlationid: "event-001"  ← Links to original
└── data: {...}

Alert Event (alert-manager)
├── id: "event-003"
├── correlationid: "event-001"  ← Still links to original
└── data: {...}
```

## Best Practices

1. **Always validate incoming events** - Check specversion and required fields
2. **Use UUIDs for event IDs** - Ensures global uniqueness
3. **Include timestamps** - Helps with debugging and ordering
4. **Maintain correlation** - Pass correlationid through the chain
5. **Use consistent event types** - Follow the naming convention
6. **Keep data focused** - Each event type should have a specific purpose
