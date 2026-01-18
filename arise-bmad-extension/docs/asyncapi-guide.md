# AsyncAPI Integration Guide

This guide explains how to use AsyncAPI 3.0 specifications in your modular architecture.

## What is AsyncAPI?

AsyncAPI is a specification for defining asynchronous APIs. It's like OpenAPI but for event-driven architectures. Each module in your system has an AsyncAPI spec that defines:

- What messages it receives (subscribes to)
- What messages it produces (publishes)
- The schema of those messages
- Server information

## AsyncAPI 3.0 Structure

```yaml
asyncapi: '3.0.0'

info:
  title: Module Name
  version: '1.0.0'
  description: What this module does

servers:
  production:
    host: api.example.com
    protocol: https
  development:
    host: localhost:3000
    protocol: http

channels:
  input-channel:
    address: /process
    messages:
      inputMessage:
        payload:
          $ref: '#/components/schemas/InputSchema'

  output-channel:
    address: /output
    messages:
      outputMessage:
        payload:
          $ref: '#/components/schemas/OutputSchema'

operations:
  receiveInput:
    action: receive
    channel:
      $ref: '#/channels/input-channel'

  sendOutput:
    action: send
    channel:
      $ref: '#/channels/output-channel'

components:
  schemas:
    InputSchema:
      type: object
      properties: ...
    OutputSchema:
      type: object
      properties: ...
```

## CloudEvents Integration

All messages in this system use CloudEvents v1.0 format. Your AsyncAPI schemas should define the full CloudEvents envelope:

```yaml
components:
  schemas:
    CloudEventsMessage:
      type: object
      required: [specversion, type, source, id, data]
      properties:
        specversion:
          type: string
          const: "1.0"
        type:
          type: string
          description: Event type identifier
        source:
          type: string
          description: Module that produced the event
        id:
          type: string
          format: uuid
        time:
          type: string
          format: date-time
        datacontenttype:
          type: string
          const: "application/json"
        data:
          $ref: '#/components/schemas/YourDataSchema'
```

## Event Type Naming Convention

Follow this pattern for event types:

```
com.arise.<domain>.<entity>.<action>.v<version>
```

**Examples:**
- `com.arise.sensor.temperature.reading.v1`
- `com.arise.sensor.temperature.validated.v1`
- `com.arise.order.customer.placed.v1`
- `com.arise.alert.threshold.exceeded.v1`

## Schema Design Best Practices

### 1. Be Explicit About Requirements

```yaml
InputData:
  type: object
  required: [sensorId, value, timestamp]
  properties:
    sensorId:
      type: string
      description: Unique sensor identifier
    value:
      type: number
      description: Sensor reading value
    timestamp:
      type: string
      format: date-time
    unit:
      type: string
      default: "celsius"
      description: Optional measurement unit
```

### 2. Use Enums for Constrained Values

```yaml
status:
  type: string
  enum: [pending, processing, completed, failed]

priority:
  type: string
  enum: [low, medium, high, urgent]
```

### 3. Include Formats

```yaml
email:
  type: string
  format: email

correlationId:
  type: string
  format: uuid

timestamp:
  type: string
  format: date-time
```

### 4. Provide Examples

```yaml
examples:
  - name: valid-reading
    summary: Example valid sensor reading
    payload:
      specversion: "1.0"
      type: "com.arise.sensor.temperature.reading.v1"
      source: "sensor-collector-v1"
      id: "550e8400-e29b-41d4-a716-446655440000"
      time: "2026-01-17T10:30:00Z"
      data:
        sensorId: "temp-01"
        value: 72.5
        unit: "fahrenheit"
```

## Generating AsyncAPI Specs

Use the `/generate-asyncapi` command:

```
/generate-asyncapi sensor-collector
```

Or ask the api-contract-designer agent:

```
Create an AsyncAPI spec for a temperature sensor collector that receives readings and outputs validated data
```

## Validating Specs

The `/validate-contracts` command checks:
- YAML syntax
- Required fields present
- CloudEvents compliance
- Event type naming convention
- Schema completeness

## Using the Template

The plugin includes a template at `templates/asyncapi/module-template.yaml`. When creating modules, the template is automatically applied with placeholders:

- `{{MODULE_NAME}}` - Human-readable name
- `{{MODULE_ID}}` - Lowercase identifier (e.g., sensor-collector-v1)
- `{{VERSION}}` - Semantic version
- `{{INPUT_EVENT_TYPE}}` - Input CloudEvents type
- `{{OUTPUT_EVENT_TYPE}}` - Output CloudEvents type

## Tools and Validation

### AsyncAPI CLI

For advanced validation:

```bash
# Install
npm install -g @asyncapi/cli

# Validate
asyncapi validate asyncapi-specs/sensor-collector.yaml

# Generate documentation
asyncapi generate fromTemplate asyncapi-specs/sensor-collector.yaml @asyncapi/html-template -o docs/
```

### JSON Schema Validation

Your implementation should validate incoming messages against the AsyncAPI schema. Libraries:

- **Python**: `jsonschema`
- **JavaScript**: `ajv`
- **n8n**: Function node with validation logic

## Best Practices

1. **Version your schemas** - Use semantic versioning
2. **Document everything** - Add descriptions to all fields
3. **Include examples** - Show valid message payloads
4. **Keep schemas focused** - One responsibility per schema
5. **Use $ref** - Reference shared schemas to avoid duplication
