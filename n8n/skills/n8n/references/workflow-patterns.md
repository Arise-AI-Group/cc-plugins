# n8n Workflow Patterns Reference

## The 5 Core Patterns

### 1. Webhook Processing

**Structure**: Receive HTTP request -> Process -> Respond

**Use When**:
- External systems need to trigger workflows
- Real-time event processing
- API endpoints for other services

**Key Nodes**: Webhook, Set, IF/Switch, Respond to Webhook

**Example Flow**:
```
Webhook -> Validate Input -> Process Data -> Send Response
                         -> Log to Database (parallel)
```

**Critical**: Webhook data is under `$json.body`, not at root level.

### 2. HTTP API Integration

**Structure**: Trigger -> Fetch External Data -> Transform -> Output

**Use When**:
- Pulling data from external APIs
- Syncing between services
- Data enrichment workflows

**Key Nodes**: HTTP Request, Set, Code, Merge

**Example Flow**:
```
Schedule Trigger -> HTTP Request (API) -> Transform Data -> Update Database
                                       -> Send Notification
```

### 3. Database Operations

**Structure**: Trigger -> Query/Write Database -> Process Results

**Use When**:
- Data synchronization
- Batch processing
- CRUD operations on records

**Key Nodes**: Postgres/MySQL/MongoDB, Data Table, Spreadsheet nodes

**Example Flow**:
```
Schedule -> Query Database -> Filter Changed -> Update External System
                           -> Archive Old Records
```

### 4. AI Agent Workflow

**Structure**: Trigger -> AI Agent -> Tool Execution -> Response

**Use When**:
- Conversational interfaces
- Complex decision making
- Multi-step AI tasks

**Key Nodes**: AI Agent, Chat Model, Tools (Calculator, Code, HTTP, etc.)

**Example Flow**:
```
Chat Trigger -> AI Agent (with memory) -> Execute Tools -> Format Response
                                       -> Store Conversation
```

**Special Considerations**:
- Use `get_node` detail=full for AI agent configuration
- 8 tool connection types available
- Memory nodes for conversation continuity

### 5. Scheduled Tasks

**Structure**: Schedule Trigger -> Batch Process -> Report/Notify

**Use When**:
- Regular maintenance tasks
- Periodic data syncs
- Scheduled reports

**Key Nodes**: Schedule Trigger, Loop nodes, Aggregate

**Example Flow**:
```
Schedule (daily) -> Fetch All Records -> Process Each -> Aggregate Results -> Send Report
```

## Pattern Selection Guide

| Need | Pattern |
|------|---------|
| React to external events | Webhook Processing |
| Pull data from APIs | HTTP API Integration |
| Work with databases | Database Operations |
| AI/LLM interactions | AI Agent Workflow |
| Regular automated tasks | Scheduled Tasks |

## Data Flow Architectures

### Linear Flow
```
A -> B -> C -> D
```
Simple sequential processing. Use for straightforward transformations.

### Branching
```
A -> IF -> B (true)
       -> C (false)
```
Conditional logic. Use IF or Switch nodes.

### Parallel Processing
```
A -> B
  -> C
  -> D
```
Multiple simultaneous operations. Connect one node to multiple outputs.

### Loop/Iteration
```
A -> Loop -> Process Each -> Aggregate
```
Batch processing. Use SplitInBatches or Loop nodes.

### Error Handler Separation
```
Main Flow: A -> B -> C
Error Flow: Error Trigger -> Log -> Notify
```
Keep error handling separate for clarity.

## Common Workflow Components

### Triggers (How workflows start)
- **Webhook**: External HTTP requests
- **Schedule**: Time-based (cron)
- **Manual**: UI button (testing only)
- **Polling**: Check external source periodically

### Data Sources
- HTTP Request, Database nodes, Service integrations, Code nodes

### Transformation
- **Set**: Add/modify fields
- **Code**: Complex JavaScript/Python logic
- **IF/Switch**: Conditional routing
- **Merge**: Combine data streams

### Outputs
- HTTP Request (to APIs), Database writes, Email/Slack/SMS, File storage

## Workflow Creation Checklist

1. **Identify the trigger**: What starts this workflow?
2. **Map data flow**: What transforms happen?
3. **Handle errors**: What if something fails?
4. **Consider scale**: Will this handle expected volume?
5. **Add logging**: Can you debug issues later?

## Statistics from Templates

- Most common triggers: Webhooks (35%), Schedules (28%)
- Most used transformation: Set node (68%)
- Most common output: HTTP Request (45%)
