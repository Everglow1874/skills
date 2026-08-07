# JSON Schemas

This reference document defines the JSON structures used throughout the skill-creator workflow.

## evals.json

The main evaluation file that contains test cases and their assertions.

```json
{
  "skill_name": "string",
  "evals": [
    {
      "id": "number",
      "prompt": "string",
      "expected_output": "string",
      "files": ["string"],
      "assertions": [
        {
          "type": "string",
          "value": "string",
          "description": "string"
        }
      ]
    }
  ]
}
```

### Fields

- **skill_name**: Name of the skill being evaluated
- **evals**: Array of evaluation test cases
  - **id**: Unique identifier for the test case
  - **prompt**: The user prompt to test
  - **expected_output**: Description of expected result
  - **files**: Array of input files (if any)
  - **assertions**: Array of quantitative assertions

### Assertion Types

- **contains**: Output must contain the specified text
- **not_contains**: Output must not contain the specified text
- **regex**: Output must match the regular expression
- **file_exists**: A specific file must be created
- **file_content**: File content must match expected value

## eval_metadata.json

Metadata for each evaluation run.

```json
{
  "eval_id": "number",
  "eval_name": "string",
  "prompt": "string",
  "assertions": [
    {
      "type": "string",
      "value": "string",
      "description": "string"
    }
  ]
}
```

## grading.json

Results from grading assertions against outputs.

```json
{
  "expectations": [
    {
      "text": "string",
      "passed": "boolean",
      "evidence": "string"
    }
  ]
}
```

**Important**: The grading.json expectations array must use the fields `text`, `passed`, and `evidence` (not `name`/`met`/`details` or other variants) — the viewer depends on these exact field names.

## timing.json

Performance metrics for each run.

```json
{
  "total_tokens": "number",
  "duration_ms": "number",
  "total_duration_seconds": "number"
}
```

## benchmark.json

Aggregated benchmark results across multiple runs.

```json
{
  "skill_name": "string",
  "configurations": [
    {
      "name": "string",
      "pass_rate": "number",
      "mean_time": "number",
      "stddev_time": "number",
      "mean_tokens": "number",
      "stddev_tokens": "number",
      "evals": [
        {
          "eval_name": "string",
          "pass_rate": "number",
          "time": "number",
          "tokens": "number"
        }
      ]
    }
  ],
  "delta": {
    "pass_rate": "number",
    "time": "number",
    "tokens": "number"
  }
}
```

## feedback.json

User feedback from the eval viewer.

```json
{
  "reviews": [
    {
      "run_id": "string",
      "feedback": "string",
      "timestamp": "string"
    }
  ],
  "status": "string"
}
```

## trigger_eval.json

Evaluation queries for description optimization.

```json
[
  {
    "query": "string",
    "should_trigger": "boolean"
  }
]
```
