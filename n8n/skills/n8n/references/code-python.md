# n8n Python Code Node Reference

## Important: JavaScript First

**Use JavaScript for 95% of use cases.** Only use Python when:

- You need specific Python standard library functions
- You're significantly more comfortable with Python
- Data transformations are better suited to Python syntax

### Why JavaScript is Preferred

| Feature | JavaScript | Python |
|---------|------------|--------|
| Helper functions | Full access (`$helpers.httpRequest`) | Limited |
| DateTime library | Luxon (powerful) | Standard datetime |
| External libraries | Some supported | **None** |
| Community examples | Extensive | Limited |
| Documentation | Comprehensive | Basic |

## Critical Limitation: No External Libraries

**Python in n8n has NO external library support.**

You cannot use:
- `requests`
- `pandas`
- `numpy`
- `beautifulsoup4`
- Any pip-installable package

## Standard Library Available

You CAN use these built-in Python modules:

| Module | Use For |
|--------|---------|
| `json` | JSON parsing/serialization |
| `datetime` | Date/time operations |
| `re` | Regular expressions |
| `base64` | Encoding/decoding |
| `hashlib` | Hashing (MD5, SHA) |
| `urllib.parse` | URL manipulation |
| `math` | Mathematical functions |
| `random` | Random number generation |
| `statistics` | Statistical calculations |
| `collections` | Specialized containers |
| `itertools` | Iteration utilities |

## Quick Start Template

```python
# Run Once for All Items (default)
items = _input.all()
results = []

for item in items:
    data = item.json
    results.append({
        "json": {
            "originalField": data.get("fieldName"),
            "newField": "computed value"
        }
    })

return results
```

## Data Access Patterns

### _input.all() - Batch Operations

```python
items = _input.all()

results = []
for item in items:
    results.append({
        "json": {
            "name": item.json.get("name"),
            "processed": True
        }
    })

return results
```

### _input.first() - Single Item

```python
item = _input.first()
data = item.json

return [{
    "json": {
        "result": data.get("someField")
    }
}]
```

### _input.item - Each Item Mode Only

```python
# Only in "Run Once for Each Item" mode
current = _input.item

return [{
    "json": {
        "processed": current.json.get("value", 0) * 2
    }
}]
```

### _node - Access Other Nodes

```python
http_data = _node["HTTP Request"].json
webhook_data = _node["Webhook"].json

return [{
    "json": {
        "apiResponse": http_data.get("data"),
        "webhookBody": webhook_data.get("body")
    }
}]
```

## Critical: Webhook Data Structure

**Webhook data is nested under "body"!**

```python
# WRONG - KeyError or None
email = _input.first().json.get("email")

# CORRECT - access through body
body = _input.first().json.get("body", {})
email = body.get("email")

# Or with default
email = _input.first().json.get("body", {}).get("email", "default@example.com")
```

## Return Format

**Must return**: List of dicts with "json" key

```python
# CORRECT
return [
    {"json": {"field": "value"}},
    {"json": {"field": "value2"}}
]

# CORRECT - single item
return [{"json": {"result": "data"}}]

# WRONG - missing list
return {"json": {"field": "value"}}

# WRONG - missing json wrapper
return [{"field": "value"}]
```

## Top 5 Mistakes

### 1. Importing External Libraries

```python
# WRONG - will fail
import requests
import pandas as pd

# CORRECT - use standard library only
import json
import re
from datetime import datetime
```

### 2. Missing Return Statement

```python
# WRONG
data = _input.first().json
result = {"processed": data.get("value")}

# CORRECT
data = _input.first().json
return [{"json": {"processed": data.get("value")}}]
```

### 3. Wrong Return Format

```python
# WRONG - dict instead of list
return {"json": {"data": "value"}}

# WRONG - missing json wrapper
return [{"data": "value"}]

# CORRECT
return [{"json": {"data": "value"}}]
```

### 4. KeyError on Missing Keys

```python
# WRONG - crashes if "user" doesn't exist
email = item.json["user"]["email"]

# CORRECT - use .get() with defaults
user = item.json.get("user", {})
email = user.get("email", "unknown")
```

### 5. Webhook Body Nesting

```python
# WRONG
name = _input.first().json.get("name")

# CORRECT for webhook input
name = _input.first().json.get("body", {}).get("name")
```

## Common Patterns

### Filter Items

```python
items = _input.all()
results = []

for item in items:
    if item.json.get("status") == "active":
        results.append({"json": item.json})

return results
```

### Aggregate Data

```python
from statistics import mean

items = _input.all()
amounts = [item.json.get("amount", 0) for item in items]

return [{
    "json": {
        "total": sum(amounts),
        "count": len(amounts),
        "average": mean(amounts) if amounts else 0
    }
}]
```

### Date Processing

```python
from datetime import datetime, timedelta

items = _input.all()
results = []

for item in items:
    date_str = item.json.get("date")
    if date_str:
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        results.append({
            "json": {
                "original": date_str,
                "formatted": date.strftime("%Y-%m-%d"),
                "next_week": (date + timedelta(days=7)).isoformat()
            }
        })

return results
```

### String Processing with Regex

```python
import re

items = _input.all()
results = []

for item in items:
    text = item.json.get("text", "")
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    results.append({
        "json": {
            "original": text,
            "emails_found": emails
        }
    })

return results
```

## When to Use Python vs JavaScript

| Scenario | Recommendation |
|----------|---------------|
| Need `$helpers.httpRequest` | JavaScript |
| Need Luxon DateTime | JavaScript |
| Complex date/time logic | JavaScript (Luxon) |
| Need external library | JavaScript or use HTTP node |
| Simple data transformation | Either (preference) |
| Statistical calculations | Python (statistics module) |
| Regex-heavy processing | Either (both good) |
| List comprehensions | Python (cleaner syntax) |
