# Generate AsyncAPI
> Generate or update AsyncAPI specification for a module.

## Variables
module_name: $1

## Instructions

Generate a complete AsyncAPI 3.0 specification for the specified module.

### Step 1: Validate Input

If `module_name` is not provided:
- List existing modules from module-registry.yaml
- Ask user to select or provide a module name

### Step 2: Find Module

Look for the module:
1. Check `<arch-dir>/modules/<module-name>/`
2. Check if asyncapi.yaml already exists

### Step 3: Gather Information

If creating new spec, ask the user:

**Input Messages:**
- "What CloudEvents types does this module receive?"
- "What fields are in the input data schema?"

**Output Messages:**
- "What CloudEvents types does this module produce?"
- "What fields are in the output data schema?"

If updating existing spec:
- Read existing asyncapi.yaml
- Ask what to add/modify

### Step 4: Read Template

Read the base template from:
`arise-bmad-extension/templates/asyncapi/module-template.yaml`

### Step 5: Generate Specification

Create/update `<arch-dir>/modules/<module-name>/asyncapi.yaml`:

```yaml
asyncapi: '3.0.0'

info:
  title: <Module Name>
  version: '1.0.0'
  description: |
    <Module description based on type and user input>

    Part of Arise modular integration platform.

    ## Capabilities
    <List capabilities from manifest or user input>
  contact:
    name: Arise AI Group

servers:
  production:
    host: api.example.com
    protocol: https
  development:
    host: localhost:<port>
    protocol: http

channels:
  input:
    address: <input-topic>
    description: Receives <input-event-type> messages
    messages:
      inputMessage:
        name: <InputMessageName>
        title: <Input Message Title>
        summary: <Brief description>
        contentType: application/cloudevents+json
        payload:
          $ref: '#/components/schemas/InputCloudEvent'
        examples:
          - name: valid-input
            summary: Example valid input
            payload:
              specversion: "1.0"
              type: "<input-event-type>"
              source: "<source-module>"
              id: "example-uuid"
              time: "2026-01-17T10:30:00Z"
              datacontenttype: "application/json"
              data:
                <example-input-data>

  output:
    address: <output-topic>
    description: Produces <output-event-type> messages
    messages:
      outputMessage:
        name: <OutputMessageName>
        title: <Output Message Title>
        summary: <Brief description>
        contentType: application/cloudevents+json
        payload:
          $ref: '#/components/schemas/OutputCloudEvent'
        examples:
          - name: valid-output
            summary: Example valid output
            payload:
              specversion: "1.0"
              type: "<output-event-type>"
              source: "<module-id>"
              id: "example-uuid"
              time: "2026-01-17T10:30:00Z"
              datacontenttype: "application/json"
              data:
                <example-output-data>

operations:
  receiveInput:
    action: receive
    channel:
      $ref: '#/channels/input'
    messages:
      - $ref: '#/channels/input/messages/inputMessage'

  sendOutput:
    action: send
    channel:
      $ref: '#/channels/output'
    messages:
      - $ref: '#/channels/output/messages/outputMessage'

components:
  schemas:
    InputCloudEvent:
      type: object
      required: [specversion, type, source, id, data]
      properties:
        specversion:
          type: string
          const: "1.0"
        type:
          type: string
          const: "<input-event-type>"
        source:
          type: string
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
          $ref: '#/components/schemas/InputData'

    OutputCloudEvent:
      type: object
      required: [specversion, type, source, id, data]
      properties:
        specversion:
          type: string
          const: "1.0"
        type:
          type: string
          const: "<output-event-type>"
        source:
          type: string
          const: "<module-id>"
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
          $ref: '#/components/schemas/OutputData'

    InputData:
      type: object
      description: <Input data description>
      required: <required-fields>
      properties:
        <input-data-properties>

    OutputData:
      type: object
      description: <Output data description>
      required: <required-fields>
      properties:
        <output-data-properties>
```

### Step 6: Copy to AsyncAPI Specs Directory

Copy the spec to the central location:
```bash
cp <arch-dir>/modules/<module-name>/asyncapi.yaml <arch-dir>/asyncapi-specs/<module-name>.yaml
```

### Step 7: Update CloudEvents Taxonomy

If new event types were defined, add them to `<arch-dir>/cloudevents-taxonomy.md`:

```markdown
### <Domain> Domain

- `<event-type>`
  - **Source**: <module-id>
  - **Data Schema**: <schema-reference>
  - **Description**: <what this event represents>
```

### Step 8: Validate Specification

Check the specification:
- YAML syntax is valid
- All $ref references resolve
- Required fields are defined
- Examples match schemas

### Step 9: Report Success

Report:
- Created/updated asyncapi.yaml
- Copied to asyncapi-specs/
- Updated cloudevents-taxonomy.md (if new types)
- Validation results
- Suggest: implement module to match spec, create contract tests
