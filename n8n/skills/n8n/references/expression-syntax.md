# n8n Expression Syntax Reference

## Expression Format

All dynamic content in n8n requires **double curly braces**: `{{ expression }}`

Without braces, content is treated as literal text.

## Core Variables

### $json - Current Node Output

Access data from the current node's output:

```javascript
{{ $json.fieldName }}           // Direct field
{{ $json.nested.property }}     // Nested field
{{ $json['field name'] }}       // Field with spaces (bracket notation)
{{ $json.items[0].name }}       // Array access
```

### $node - Reference Other Nodes

Access output from previous nodes by name:

```javascript
{{ $node["HTTP Request"].json.data }}
{{ $node["Webhook"].json.body.email }}
```

**Important**: Node names are case-sensitive and must be quoted.

### $now - Timestamps

Current timestamp with Luxon formatting:

```javascript
{{ $now }}                           // Current ISO timestamp
{{ $now.toFormat('yyyy-MM-dd') }}    // Formatted date
{{ $now.plus({days: 7}) }}           // Date math
{{ $today }}                         // Today at midnight
```

### $env - Environment Variables

Access n8n environment variables:

```javascript
{{ $env.API_KEY }}
{{ $env.BASE_URL }}
```

### Other Variables

```javascript
{{ $execution.id }}           // Current execution ID
{{ $workflow.id }}            // Workflow ID
{{ $workflow.name }}          // Workflow name
{{ $runIndex }}               // Current run index (in loops)
{{ $itemIndex }}              // Current item index
```

## Critical: Webhook Data Structure

**Webhook data is NOT at the root level!**

When receiving webhook data, user content is nested under `.body`:

```javascript
// WRONG - accessing root level
{{ $json.email }}

// CORRECT - accessing body
{{ $json.body.email }}
{{ $json.body.user.name }}
```

Full webhook structure:
```json
{
  "headers": { ... },
  "params": { ... },
  "query": { ... },
  "body": {
    // Your actual data is here
    "email": "user@example.com",
    "name": "John"
  }
}
```

## Common Patterns

### Conditional/Default Values

```javascript
{{ $json.name || 'Unknown' }}                    // Default if falsy
{{ $json.status ? 'Active' : 'Inactive' }}       // Ternary
{{ $json.items?.length || 0 }}                   // Optional chaining
```

### String Operations

```javascript
{{ $json.name.toUpperCase() }}
{{ $json.email.split('@')[0] }}
{{ `Hello ${$json.name}!` }}                     // Template literal
```

### Array Operations

```javascript
{{ $json.items.length }}
{{ $json.items.map(i => i.name).join(', ') }}
{{ $json.items.filter(i => i.active) }}
```

### Date Formatting

```javascript
{{ DateTime.fromISO($json.date).toFormat('dd/MM/yyyy') }}
{{ $now.diff(DateTime.fromISO($json.created), 'days').days }}
```

## When NOT to Use Expressions

### In Code Nodes

Code nodes use pure JavaScript - no `{{ }}` braces:

```javascript
// In Code node - use direct JavaScript
const email = $json.body.email;        // Correct
const email = {{ $json.body.email }};  // WRONG
```

### In Webhook Paths

Webhook paths don't support expressions - use static strings.

## Quick Fix Reference

| Problem | Solution |
|---------|----------|
| `$json.field` (no output) | Add braces: `{{ $json.field }}` |
| `{{ $json.email }}` returns undefined for webhook | Use body: `{{ $json.body.email }}` |
| `{{ $node.HTTP Request }}` error | Quote name: `{{ $node["HTTP Request"] }}` |
| `{{ {{ $json.x }} }}` nested braces | Remove inner braces: `{{ $json.x }}` |
| Field name has space | Use bracket notation: `{{ $json['field name'] }}` |
| Undefined error on nested field | Use optional chaining: `{{ $json.user?.email }}` |

## Expression Testing

Use n8n's built-in expression editor (click the expression icon next to any field) to:
- Test expressions in real-time
- See available variables
- Preview output with sample data
