# n8n JavaScript Code Node Reference

## Quick Start Template

```javascript
// Run Once for All Items (default, recommended)
const items = $input.all();
const results = [];

for (const item of items) {
  results.push({
    json: {
      // Your transformed data
      originalField: item.json.fieldName,
      newField: "computed value"
    }
  });
}

return results;
```

## Mode Selection

### Run Once for All Items (Default - Use 95% of the time)

- Executes once with access to all input items
- Use `$input.all()` to get array of items
- Better for batch operations, aggregations

### Run Once for Each Item

- Executes separately for each input item
- Use `$input.item` to get current item
- Use for operations that must be isolated per item

**Recommendation**: Start with "All Items" mode. Only switch if you need isolated execution.

## Data Access Patterns

### $input.all() - Batch Operations

```javascript
const items = $input.all();

// Process all items
const results = items.map(item => ({
  json: {
    name: item.json.name,
    processed: true
  }
}));

return results;
```

### $input.first() - Single Item

```javascript
const item = $input.first();
const data = item.json;

return [{
  json: {
    result: data.someField
  }
}];
```

### $input.item - Each Item Mode Only

```javascript
// Only in "Run Once for Each Item" mode
const currentItem = $input.item;

return [{
  json: {
    processed: currentItem.json.value * 2
  }
}];
```

### $node - Access Other Nodes

```javascript
// Get output from a specific node
const httpData = $node["HTTP Request"].json;
const webhookData = $node["Webhook"].json;

return [{
  json: {
    apiResponse: httpData.data,
    webhookBody: webhookData.body
  }
}];
```

## Critical: Webhook Data Structure

**Webhook data is nested under `.body`!**

```javascript
// WRONG - data is undefined
const email = $input.first().json.email;

// CORRECT - access through body
const email = $input.first().json.body.email;

// Or with null safety
const body = $input.first().json.body || {};
const email = body.email;
```

## Return Format

**Must return**: Array of objects with `json` property

```javascript
// CORRECT
return [
  { json: { field: "value" } },
  { json: { field: "value2" } }
];

// ALSO CORRECT - single item
return [{ json: { result: "data" } }];

// WRONG - missing array
return { json: { field: "value" } };

// WRONG - missing json wrapper
return [{ field: "value" }];

// WRONG - no return
// (missing return statement)
```

## Top 5 Mistakes

### 1. Missing Return Statement

```javascript
// WRONG
const data = $input.first().json;
const result = { processed: data.value };

// CORRECT
const data = $input.first().json;
return [{ json: { processed: data.value } }];
```

### 2. Using Expression Syntax

```javascript
// WRONG - this is n8n expression syntax, not JavaScript
const value = {{ $json.field }};

// CORRECT - pure JavaScript
const value = $input.first().json.field;
```

### 3. Wrong Return Format

```javascript
// WRONG - object instead of array
return { json: { data: "value" } };

// WRONG - missing json wrapper
return [{ data: "value" }];

// CORRECT
return [{ json: { data: "value" } }];
```

### 4. Not Handling Null/Undefined

```javascript
// WRONG - crashes if user is undefined
const email = item.json.user.email;

// CORRECT - null safety
const email = item.json.user?.email || "default@example.com";

// Or with explicit check
const user = item.json.user;
if (!user) {
  return [{ json: { error: "No user data" } }];
}
const email = user.email;
```

### 5. Webhook Body Nesting

```javascript
// WRONG
const name = $input.first().json.name;

// CORRECT for webhook input
const name = $input.first().json.body.name;
```

## Built-in Functions

### $helpers.httpRequest()

Make HTTP requests from Code node:

```javascript
const response = await $helpers.httpRequest({
  method: 'GET',
  url: 'https://api.example.com/data',
  headers: {
    'Authorization': 'Bearer ' + $env.API_KEY
  }
});

return [{ json: response }];
```

### DateTime (Luxon)

Date/time operations:

```javascript
const { DateTime } = require('luxon');

const now = DateTime.now();
const formatted = now.toFormat('yyyy-MM-dd');
const future = now.plus({ days: 7 });

return [{
  json: {
    today: formatted,
    nextWeek: future.toISO()
  }
}];
```

### $jmespath()

Query JSON with JMESPath:

```javascript
const data = $input.first().json;
const names = $jmespath(data, 'users[*].name');

return [{ json: { names } }];
```

## Common Patterns

### Filter Items

```javascript
const items = $input.all();
const filtered = items.filter(item => item.json.status === 'active');

return filtered.map(item => ({ json: item.json }));
```

### Aggregate Data

```javascript
const items = $input.all();
const total = items.reduce((sum, item) => sum + item.json.amount, 0);

return [{
  json: {
    total,
    count: items.length,
    average: total / items.length
  }
}];
```

### Transform and Flatten

```javascript
const items = $input.all();
const flattened = items.flatMap(item =>
  item.json.records.map(record => ({
    json: {
      parentId: item.json.id,
      ...record
    }
  }))
);

return flattened;
```

## When to Use Code Node vs Other Nodes

| Task | Use Code Node? | Alternative |
|------|---------------|-------------|
| Simple field mapping | No | Set node |
| Basic filtering | No | Filter node |
| Simple conditional | No | IF node |
| Complex transformation | Yes | - |
| Data aggregation | Yes | - |
| Multiple operations | Yes | - |
| External API call | Maybe | HTTP Request node |

**Rule**: If a built-in node can do it, prefer the built-in node for clarity.
