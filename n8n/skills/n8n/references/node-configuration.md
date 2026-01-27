# n8n Node Configuration Reference

## Core Concepts

### Operation-Aware Configuration

Field requirements depend on the **operation** selected, not just the node type.

Example - Slack node:
- `postMessage` operation requires: `channel`
- `updateMessage` operation requires: `channel`, `messageId`
- `deleteMessage` operation requires: `channel`, `messageId`

**Always check required fields for your specific operation.**

### Property Dependencies (displayOptions)

Some fields only appear when other fields have specific values:

Example - HTTP Request node:
- `body` field only appears when method is POST/PUT/PATCH
- `authentication` fields only appear when auth type is selected

This is controlled by `displayOptions` in the node schema.

## Discovery Workflow

1. **Identify node and operation**: What are you trying to do?
2. **Get node info**: `get_node` with detail=standard
3. **Configure required fields**: Start with mandatory properties
4. **Validate**: Check for errors
5. **Search properties if needed**: `get_node` mode=search_properties
6. **Add optional fields**: Enhance as needed
7. **Validate again**: Before deployment

## get_node Detail Levels

| Level | Tokens | Use When |
|-------|--------|----------|
| `minimal` | ~200 | Checking if node exists |
| `standard` | 1-2K | Normal configuration (default, 95% of cases) |
| `full` | 3-8K | Complex nodes, AI agents, debugging |

**Start with standard** - only use full when standard doesn't have what you need.

### Using search_properties Mode

When you can't find a specific property:

```javascript
get_node({
  nodeType: "nodes-base.httpRequest",
  mode: "search_properties",
  propertyQuery: "header"
})
```

Returns all properties matching the search term.

## Common Node Patterns

### Resource/Operation Nodes

Nodes like Slack, Google Sheets, Notion:

```json
{
  "parameters": {
    "resource": "channel",
    "operation": "create",
    // Operation-specific fields
    "name": "my-channel"
  }
}
```

**Pattern**: Select resource -> Select operation -> Configure operation fields

### HTTP-Based Nodes

HTTP Request, Webhook Response:

```json
{
  "parameters": {
    "method": "POST",
    "url": "https://api.example.com",
    "authentication": "genericCredentialType",
    "body": {
      "mode": "json",
      "json": "={{ $json }}"
    }
  }
}
```

**Pattern**: Method determines which body/header fields appear

### Conditional Logic Nodes

IF, Switch, Filter:

```json
{
  "parameters": {
    "conditions": {
      "options": {
        "caseSensitive": true
      },
      "conditions": [
        {
          "leftValue": "={{ $json.status }}",
          "rightValue": "active",
          "operator": {
            "type": "string",
            "operation": "equals"
          }
        }
      ]
    }
  }
}
```

**Pattern**: Operator type determines if `singleValue` is needed (auto-sanitized)

### AI Agent Nodes

More complex configuration - use `detail=full`:

```json
{
  "parameters": {
    "agent": "conversationalAgent",
    "promptType": "define",
    "text": "You are a helpful assistant...",
    "options": {
      "systemMessage": "...",
      "maxIterations": 10
    }
  }
}
```

**8 tool connection types** available for AI agents.

## Data Table Node Configuration

Data Tables provide persistent storage. Key patterns:

### Row Operations

| Operation | Required Fields |
|-----------|----------------|
| `insert` | `dataTableId`, `columns` |
| `get` | `dataTableId` |
| `update` | `dataTableId`, `columns`, `filters` |
| `upsert` | `dataTableId`, `columns`, `filters` |
| `deleteRows` | `dataTableId` |
| `rowExists` | `dataTableId`, `filters` |
| `rowNotExists` | `dataTableId`, `filters` |

### Table Operations

| Operation | Required Fields |
|-----------|----------------|
| `create` | `tableName` |
| `list` | (none) |
| `update` | `dataTableId`, `newName` |
| `delete` | `dataTableId` |

### Data Table ID Reference

```json
"dataTableId": {
  "mode": "name",    // or "id" or "list"
  "value": "my_table_name"
}
```

### Column Mapping

```json
"columns": {
  "mappingMode": "defineBelow",
  "value": {
    "field1": "={{ $json.field1 }}",
    "field2": "static value"
  }
}
```

### Filter Conditions

```json
"filters": {
  "conditions": [
    {
      "keyName": "email",
      "condition": "eq",
      "keyValue": "={{ $json.email }}"
    }
  ]
}
```

**Available conditions**: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `contains`, `isEmpty`, `isNotEmpty`, `isTrue`, `isFalse`

## Configuration Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| Use `detail=full` for every lookup | Start with `detail=standard` |
| Manually set operator `singleValue` | Let auto-sanitization handle it |
| Guess field names | Use `mode=search_properties` |
| Configure all fields at once | Start with required, add optional |
| Skip validation | Validate after each significant change |

## Best Practices

1. **Always specify resource and operation first** - Other fields depend on these
2. **Use standard detail level by default** - 95% of cases
3. **Validate iteratively** - After each change
4. **Trust auto-sanitization** - Don't manually fix operator structure
5. **Use search_properties for unknown fields** - Better than guessing
6. **Check displayOptions** - Understand why fields appear/disappear
