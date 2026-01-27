# n8n Validation Expert Reference

## Error Severity Levels

### Errors (Execution Blockers)

Must be fixed before workflow can run:

| Error Type | Meaning | Common Fix |
|------------|---------|------------|
| `missing_required` | Required field not set | Add the missing property |
| `invalid_value` | Value not in allowed options | Check allowed values via get_node |
| `type_mismatch` | Wrong data type | Convert to correct type |
| `invalid_reference` | Node doesn't exist | Fix node name spelling |
| `invalid_expression` | Syntax error in `{{ }}` | Check expression syntax |

### Warnings (Non-Blocking)

Workflow will run but may have issues:
- Deprecated feature usage
- Performance concerns
- Best practice violations

### Suggestions (Enhancements)

Optional improvements:
- Alternative approaches
- Optimization opportunities

## The Validation Loop

Typical validation takes 2-3 cycles:

```
1. Validate workflow/node
2. Read error messages (avg 23 seconds)
3. Implement fixes (avg 58 seconds)
4. Re-validate
5. Repeat until clean
```

**Key principle**: Fix one error type at a time. Don't batch changes.

## Validation Profiles

| Profile | Best For | Strictness |
|---------|----------|------------|
| `minimal` | Quick edits, drafts | Low - required fields only |
| `runtime` | Pre-deployment | Medium - catches real issues |
| `ai-friendly` | AI-generated configs | Medium - reduces false positives |
| `strict` | Production workflows | High - maximum validation |

**Recommendation**: Use `runtime` for most validation tasks.

## Common Error Types and Fixes

### missing_required

```
Error: Missing required property "channel" in Slack node
```

**Fix Process**:
1. Run `get_node` to see required properties
2. Add the missing property with correct value
3. Re-validate

### invalid_value

```
Error: Invalid value "post" for operation. Allowed: ["create", "update", "delete"]
```

**Fix**: Change to one of the allowed values listed in error.

### type_mismatch

```
Error: Expected number, got string for "limit"
```

**Fix**: Convert value to correct type (remove quotes for numbers).

### invalid_expression

```
Error: Invalid expression syntax in "{{ $json.name"
```

**Common causes**:
- Missing closing `}}`
- Nested braces `{{ {{ }} }}`
- Using expressions in Code nodes (don't use braces there)

### invalid_reference

```
Error: Referenced node "HTTP Request" does not exist
```

**Fix**: Check exact node name (case-sensitive) or fix connection.

## Auto-Sanitization System

When you save any workflow, these issues are **automatically fixed**:

### Binary Operators (Fixed Automatically)

Operators requiring two values (`equals`, `contains`, `greaterThan`, etc.):
- Removes incorrect `singleValue` property

### Unary Operators (Fixed Automatically)

Operators requiring one value (`isEmpty`, `isNotEmpty`, `true`, `false`):
- Adds required `singleValue: true`

### What Auto-Sanitization CANNOT Fix

- Broken connections between nodes
- Missing required fields
- Invalid node references
- Branch count mismatches
- Corrupt/paradoxical states

**If you see operator structure errors**: Just save the workflow and re-validate - they often auto-fix.

## False Positives

Some validation errors aren't real problems:

| False Positive | Why It Happens | Action |
|----------------|----------------|--------|
| Missing optional field | Strict validation | Ignore or use runtime profile |
| Type warning on expression | Can't evaluate at validation time | Test at runtime |
| Deprecated warning | Old but functional | Consider updating, not urgent |

**Tip**: Use `ai-friendly` profile to reduce false positives when building with AI assistance.

## Recovery Strategies

### Strategy 1: Minimal Start

Build configuration incrementally:
1. Add only required fields
2. Validate
3. Add optional fields one at a time
4. Validate after each addition

### Strategy 2: Binary Search Isolation

For complex workflows with multiple errors:
1. Disable half the nodes
2. Validate
3. If clean, problem is in disabled half
4. Repeat to isolate problem node

### Strategy 3: Stale Connection Cleanup

For broken connection errors:
```javascript
// Use partial update with cleanStaleConnections
n8n_update_partial_workflow({
  id: "workflow-id",
  operations: [{ type: "cleanStaleConnections" }]
})
```

### Strategy 4: Auto-fix Preview

Before applying auto-fixes:
```javascript
n8n_autofix_workflow({
  id: "workflow-id",
  applyFixes: false  // Preview only
})
```

Review suggested fixes, then apply if appropriate.

## Best Practices

1. **Validate after every significant change** - Catch issues early
2. **Read complete error messages** - They usually tell you exactly what's wrong
3. **Use runtime profile** - Balanced strictness for most cases
4. **Trust auto-sanitization for operators** - Don't manually fix operator structure
5. **Fix one error at a time** - Easier to track what worked
6. **Re-validate after auto-fix** - Ensure all issues resolved
