---
name: proposal
description: Generate sales proposals and create Google Slides presentations from templates. Use when the user asks about proposal operations, management, or automation.
---

# Generate Proposal Directive

## Goal
Generate a proposal from prospect information and create a Google Slides presentation with all content populated.

## Inputs
- **Customer Name**: Company name
- **Website**: Company website URL
- **Problem**: The challenge/pain point they're facing
- **Proposed Solution**: Our approach to solving it
- **Timeline**: Project duration (e.g., "30 days", "6 weeks")

All fields are required - do not proceed with missing data.

## Process

1. **Gather Input**: Collect all 5 required inputs from the user
2. **Generate Proposal JSON**: Create structured JSON following the schema below
3. **Validate**: Ensure all 24 fields are present and meet constraints
4. **Create Presentation**: Copy Google Slides template and replace placeholders
5. **Deliver**: Return the Google Slides URL to the user

## Outputs
- Google Slides presentation URL with all placeholders replaced

## Edge Cases
- If timeline is vague (e.g., "a few weeks"), default to 30 days
- Convert weeks to days (1 week = 7 days) for metric calculations
- If Google API fails, return the validated JSON so user can manually populate

---

## Proposal Schema

Generate EXACTLY this JSON structure:

```json
{
  "proposal_title": "3-5 word compelling title based on solution",
  "proposal_subtitle": "Subtitle hinting at methodology/approach",
  "overview": "2-3 sentences summarizing strategic opportunity and value proposition",
  "problem1": "Primary problem in 3-6 words",
  "problem2": "Secondary problem in 3-6 words",
  "problem3": "Tertiary problem in 3-6 words",
  "problem4": "Fourth problem in 3-6 words",
  "objective": "1 sentence with specific measurable goal and timeline",
  "proposed_solution": "1-2 sentences high-level approach",
  "process_step1_title": "1. First Phase Name",
  "process_step1_desc": "1-2 sentences what happens in phase 1",
  "process_step2_title": "2. Second Phase Name",
  "process_step2_desc": "1-2 sentences what happens in phase 2",
  "process_step3_title": "3. Third Phase Name",
  "process_step3_desc": "1-2 sentences what happens in phase 3",
  "deliverables": "2-3 sentences listing concrete outputs",
  "benefit_metric1_title": "Speed/efficiency metric name (2-3 words)",
  "benefit_metric1_value": "Number with optional unit, MAX 6 CHARS (e.g., 4x, 60%, 45)",
  "benefit_metric1_desc": "1 sentence explaining this metric",
  "benefit_metric2_title": "Automation/reduction metric name (2-3 words)",
  "benefit_metric2_value": "Number with optional unit, MAX 6 CHARS",
  "benefit_metric2_desc": "1 sentence explaining this metric",
  "benefit_metric3_title": "Time-to-value metric name (2-3 words)",
  "benefit_metric3_value": "Timeline in days, MAX 6 CHARS",
  "benefit_metric3_desc": "1 sentence explaining this metric"
}
```

## Field Generation Rules

1. **problem1-4**: Derive from the stated problem. Break into 4 distinct pain points or symptoms.
2. **process steps**: Divide timeline into 3 logical phases (Discovery -> Build -> Deploy pattern).
3. **benefit metrics**:
   - Metric 1: Speed/efficiency gain (e.g., "4x", "3x")
   - Metric 2: Automation/reduction percentage (e.g., "60%", "80%")
   - Metric 3: Timeline to value (use the provided timeline converted to days)

## Style Rules

- **Tone**: Spartan, casual, professional. No fluff.
- **Audience**: Sophisticated decision-makers
- **Metric values**: Numbers + optional 1-2 char units, MAX 6 characters total

---

## Implementation

**Scripts:**
- `tool/generate_proposal.py` - Validates the proposal JSON structure
- `tool/copy_slides_template.py` - Copies template and replaces text placeholders

**Usage:**
```bash
echo '<proposal_json>' | ./run tools/generate_proposal.py | ./run tools/copy_slides_template.py <template_id>
```

**Notes:**
- Placeholders use `{{field_name}}` format
- Supports both Service Account (`service_account.json`) and OAuth (`credentials.json`, `token.json`)
- JSON piped through stdin, URL output to stdout

