---
name: printing-press-api-to-agent-workflow
description: Build an agent-native bridge from an OpenAPI API to a Printing Press-style CLI and companion Hermes skill.
version: 0.1.0
author: Printing Press
license: MIT
tags:
  - printing-press
  - openapi
  - cli
  - hermes
  - agent-workflows
related:
  - printing-press-openapi-cli-authoring
  - printing-press-companion-skill-authoring
---

# Printing Press API-to-Agent Workflow

Use this skill when a user asks to turn an OpenAPI API into an agent-usable CLI and Hermes workflow.

Trigger phrases include:

- "Make a Printing Press CLI for this API"
- "Turn this OpenAPI URL into a CLI"
- "Make this API agent-friendly"
- "Create the Hermes skill for this CLI"
- "Build the OpenAPI to CLI to skill bridge"
- "Do what we did for Kitchen Memory"

Do not merely wrap endpoints. Design an agent-native operational interface. Commands should map to real user workflows, return JSON by default, be safe for automation, and have a companion skill that teaches Hermes when and how to use the CLI.

## Inputs

Collect or infer:

- OpenAPI URL, usually ending in `/openapi.json`
- CLI name, for example `nt` or `hostfully`
- API base URL
- API token, if needed
- Desired workflow commands
- Whether writes are allowed in the first version
- Known quirks or data hazards

## Inspect the API

Fetch and inspect the schema:

```bash
curl -fsSL "$OPENAPI_URL" -o /tmp/openapi.json
jq '.info, (.paths | keys)' /tmp/openapi.json
```

Read the API as user workflows, not as route strings. Group endpoints into human domains such as `kitchen`, `diary`, `foods`, `bookings`, `guests`, or `properties`.

Identify:

- Auth scheme
- Health or status endpoint
- Read endpoints
- Write endpoints
- Destructive endpoints
- Required request bodies
- Response schemas
- Error schema

## CLI Requirements

Build a small Printing Press-style CLI. If no stricter standard exists, use Go with Cobra.

Every CLI must support:

```text
--json
--compact
--quiet
--agent
--base-url
--token
--config
--timeout
```

Install to:

```text
~/.local/bin/<cli>
```

Store config at:

```text
~/.config/<cli>/config.json
```

Create config files with `0600` permissions and avoid printing secrets.

Support environment variable overrides:

```text
<CLI>_BASE_URL
<CLI>_TOKEN
<CLI>_CONFIG
<CLI>_TIMEOUT
```

Precedence:

1. Flags
2. Environment variables
3. Config file
4. Built-in defaults

Implement commands in this order:

1. `health` or `doctor`
2. Read-only list/get/search commands
3. Safe creates
4. Updates
5. Destructive writes only when explicitly requested

## Prerequisite Checks

Before using a generated CLI in a workflow, run:

```bash
command -v <cli>
<cli> --help
<cli> health --json
<cli> config show --json
```

If supported, use:

```bash
<cli> doctor --json
```

Stop and report a concise blocker if the CLI is missing, auth fails, config is absent, or the API is unreachable.

## Common Natural-Language Mappings

Nutrition Tracker examples:

```text
"what can I make?"
nt kitchen matches --agent --json

"what can I make that's easy?"
nt kitchen matches --effort low --agent --json

"I have eggs"
nt kitchen have eggs --agent --json

"add spinach to use soon"
nt kitchen inventory set spinach --status use_soon --agent --json

"log this meal"
nt diary add --date today --meal dinner --food "<food>" --amount <n> --unit "<unit>" --agent --json

"how did I do today?"
nt stats daily today --agent --json
```

Hostfully examples:

```text
"who's checking in today?"
hostfully today --agent --json

"show tomorrow's arrivals"
hostfully arrivals --date tomorrow --agent --json

"find this guest"
hostfully guests search "<name or email>" --agent --json
```

## Safety Rules

- Prefer read-only commands first.
- Do not perform destructive writes unless the user explicitly asks.
- Require confirmation or `--yes` for delete, archive, cancel, overwrite, and bulk update commands.
- Use dry-run before bulk writes when available.
- Never print bearer tokens or config secrets.
- In `--agent` mode, return structured, actionable errors.
- Treat masked PII as incomplete data.
- Mention data freshness limits when local caches or imports are involved.

## Known Quirks to Capture

Document quirks in each service-specific skill. Common examples:

- Masked phone numbers may be incomplete.
- Apple Health steps can be stale if the local cache has not synced.
- Open Food Facts imports may contain zero-nutrient rows.
- Local cache sync may be required before reads reflect latest remote state.
- OpenAPI descriptions may be sparse, so command semantics may require live checks.

## Verification Checklist

Run:

```bash
command -v <cli>
<cli> --help
<cli> health --json
<cli> <read-command> --json
<cli> <representative-workflow> --json
```

Confirm:

- Standard root flags are present.
- Config file permissions are `0600`.
- Env var overrides work.
- One read-only live endpoint works.
- One representative workflow works.
- Destructive commands require explicit confirmation.
- The companion Hermes skill contains exact commands.
- The skill contains no real secrets.

## Completion Criteria

The work is complete only when the API has:

- A workflow-shaped CLI installed in `~/.local/bin`
- Safe config and secret handling
- Verified live read behavior
- Verified representative workflow behavior
- A companion Hermes skill with frontmatter, triggers, prerequisite checks, common workflows, safety notes, known quirks, and verification checklist
