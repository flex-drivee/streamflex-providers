# streamflex-providers

> **Provider definitions and extractor registry for the StreamFlex streaming engine.**  
> Used by both [StreamFlex Android](../StreamFlex%20Android/) and [StreamFlex Web](../StreamFlex%20Next/).

---

## What Is This Repository?

This repository is the **single source of truth** for all StreamFlex provider configurations.  
It contains **no parsing logic** — only declarations.

| File type | Purpose |
|-----------|---------|
| `providers/*.json` | Provider definitions (domains, capabilities, extractor IDs) |
| `extractors/registry.json` | Extractor registry (URL patterns, priorities, required headers) |
| `health/health.json` | Auto-updated provider health status (by GitHub Actions) |
| `config/alternate-titles.json` | Alternate title mappings for TitleMatcher confidence scoring |
| `schemas/provider/v1.json` | JSON Schema for validating provider definitions |

---

## Repository Structure

```
streamflex-providers/
├── .github/
│   └── workflows/
│       └── provider-health.yml     ← Daily health check (4am UTC)
├── config/
│   └── alternate-titles.json       ← TitleMatcher alternate names
├── extractors/
│   └── registry.json               ← All extractors + priorities + headers
├── health/
│   └── health.json                 ← Live provider status (auto-updated)
├── providers/
│   ├── hdhub4u.json                ← Provider definition
│   ├── netmirror.json
│   ├── ottmirror.json
│   └── vegamovies.json
├── schemas/
│   └── provider/
│       └── v1.json                 ← JSON Schema (validate against this)
└── scripts/
    └── health_check.py             ← Health check script
```

---

## Provider Health Status

Providers are automatically checked every day at **04:00 UTC**.  
Results are written to [`health/health.json`](health/health.json).

| Status | Meaning |
|--------|---------|
| `online` | All test cases passed |
| `degraded` | Some test cases failed but provider is partially reachable |
| `offline` | Domain unreachable or 3+ consecutive failures |
| `unknown` | Not yet verified |

---

## How to Add a New Provider

### Step 1 — Create the provider definition

Copy an existing definition and modify it:

```bash
cp providers/hdhub4u.json providers/your-provider.json
```

Edit the file. All fields are required. See [`schemas/provider/v1.json`](schemas/provider/v1.json) for the full schema.

**Key rules:**
- `id` must be lowercase alphanumeric + hyphens only
- No parsing logic (CSS selectors, regex, XPath) in this file — ever
- `testCases` must have at least 1 entry with a known working title
- `extractorIds` must match IDs defined in `extractors/registry.json`
- `domains.primary` must be `https://`

### Step 2 — Validate your definition

```bash
# Install ajv-cli
npm install -g ajv-cli

# Validate
ajv validate -s schemas/provider/v1.json -d providers/your-provider.json
```

### Step 3 — Add your provider to the engine

**Android** — add one line to `di/ProviderModule.kt`:
```kotlin
object ProviderModule {
    fun provide(): List<StreamFlexProvider> = listOf(
        HDHubProvider(),
        NetMirrorProvider(),
        YourProvider(),   // ← Add here
    )
}
```

**Web** — add one line to `src/lib/engine/ProviderModule.ts`:
```typescript
export const providers: WebProvider[] = [
    new HDHubProvider(),
    new NetMirrorProvider(),
    new YourProvider(),   // ← Add here
];
```

### Step 4 — Open a Pull Request

PR title format: `feat: add [provider-name] provider`

Include:
- The new `providers/your-provider.json`
- A screenshot or log showing a successful search test

---

## How to Add a New Extractor

Add a new entry to `extractors/registry.json`:

```json
{
  "id": "your-extractor",
  "name": "Your Extractor",
  "priority": 60,
  "status": "active",
  "domains": ["yourhost.com"],
  "outputFormats": ["mp4"],
  "requiresReferer": true,
  "headers": { "Referer": "https://yourhost.com/" },
  "notes": "How it works.",
  "androidClass": "com.streamflex.extractors.yourextractor.YourExtractor",
  "webTs": "src/lib/extractors/YourExtractor.ts"
}
```

Then implement:
- **Android**: `YourExtractor.kt` extending `BaseExtractor`
- **Web**: `YourExtractor.ts` implementing `WebExtractor`

---

## Architecture Reference

The engine consumes this repository as follows:

```
App startup
  → Fetch provider definitions from this repo (6h cache)
  → Fetch extractors/registry.json (24h cache)
  → Fetch health/health.json (session cache)

User plays a title
  → 12-stage resolution pipeline
  → Stages 1, 3, 4: Provider (search, detail, source)
  → Stages 5–12: Engine-owned (redirect, iframe, extractor dispatch, quality, headers, player)
```

**Stream URLs are never cached.** CDN hosts sign URLs with expiry (1–6h).

---

## License

MIT — see [LICENSE](LICENSE)
