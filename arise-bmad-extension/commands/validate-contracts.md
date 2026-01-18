# Validate Contracts
> Validate all modules against their AsyncAPI specifications.

## Instructions

Validate that all modules in the project conform to their AsyncAPI contracts.

### Step 1: Find Architecture Directory

Look for the architecture directory:
1. Check if `.bmad/` exists
2. Check if `docs/` exists with architecture files
3. If neither, report no architecture found

### Step 2: Load Module Registry

Read `<arch-dir>/module-registry.yaml` to get list of modules.

### Step 3: Validate Each Module

For each module in the registry:

#### 3.1 Check AsyncAPI Spec Exists

```bash
# Check module has asyncapi.yaml
test -f <arch-dir>/modules/<module-name>/asyncapi.yaml
```

Report: "Module <name>: AsyncAPI spec exists/missing"

#### 3.2 Validate YAML Syntax

Read the asyncapi.yaml file and check:
- Valid YAML syntax
- Has required fields (asyncapi, info, channels)
- Version is 3.0.0

Report: "Module <name>: YAML syntax valid/invalid"

#### 3.3 Validate CloudEvents Compliance

Check that all message payloads include CloudEvents fields:
- specversion (const: "1.0")
- type (defined)
- source (defined)
- id (format: uuid)
- data (defined)

Report: "Module <name>: CloudEvents format valid/invalid"

#### 3.4 Check Event Type Naming

Verify event types follow convention:
```
com.arise.<domain>.<entity>.<action>.v<version>
```

Pattern: `^com\.arise\.[a-z]+\.[a-z]+\.[a-z]+\.v[0-9]+$`

Report: "Module <name>: Event type naming valid/invalid"

#### 3.5 Check Schema Completeness

For each schema in components/schemas:
- Has type defined
- Required fields listed
- Properties have types
- Has description

Report: "Module <name>: Schemas complete/incomplete"

#### 3.6 Check Manifest Exists

```bash
test -f <arch-dir>/modules/<module-name>/manifest.yaml
```

Report: "Module <name>: Manifest exists/missing"

#### 3.7 Validate Manifest

If manifest exists, check:
- module.id matches module name
- module.version is semver
- endpoints are defined
- routing is defined

Report: "Module <name>: Manifest valid/invalid"

### Step 4: Cross-Module Validation

#### 4.1 Check Routing Coverage

Read `<arch-dir>/routing-rules.yaml`

For each module's output event type:
- Check if a routing rule exists that handles it
- Warn if no rule matches

Report: "Routing coverage: X of Y event types have routes"

#### 4.2 Check Event Type Consistency

Cross-reference:
- Event types in asyncapi specs
- Event types in cloudevents-taxonomy.md
- Event types in routing rules

Report any mismatches.

### Step 5: Generate Validation Report

Create or display a validation report:

```markdown
# Contract Validation Report

Generated: <timestamp>

## Summary

| Check | Passed | Failed | Warnings |
|-------|--------|--------|----------|
| AsyncAPI Specs | X | Y | Z |
| CloudEvents Format | X | Y | Z |
| Event Type Naming | X | Y | Z |
| Schema Completeness | X | Y | Z |
| Manifests | X | Y | Z |
| Routing Coverage | X | Y | Z |

## Module Details

### <module-name>

| Check | Status | Details |
|-------|--------|---------|
| AsyncAPI Spec | PASS/FAIL | |
| CloudEvents Format | PASS/FAIL | |
| Event Type Naming | PASS/FAIL | |
| Schemas | PASS/FAIL/WARN | |
| Manifest | PASS/FAIL | |

### <next-module>
...

## Routing Coverage

| Event Type | Routed To | Status |
|------------|-----------|--------|
| com.arise.x.y.v1 | module-a | OK |
| com.arise.x.z.v1 | (none) | WARNING |

## Recommendations

1. <Fix suggestion for any failures>
2. <Improvement suggestion for warnings>
```

### Step 6: Report Results

Display:
- Overall validation status (PASS/FAIL)
- Summary counts
- Any critical issues that need fixing
- Warnings and suggestions

If all pass:
"All modules pass contract validation."

If failures:
"Contract validation found X issues that need to be fixed:"
- List each issue with module name and fix suggestion
