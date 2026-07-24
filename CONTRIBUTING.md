# Contributing to streamflex-providers

Thank you for wanting to contribute! This guide covers everything you need.

---

## Provider Contribution Checklist

Before submitting a PR, confirm all of the following:

- [ ] Provider JSON validates against `schemas/provider/v1.json`
- [ ] `id` is unique and follows `lowercase-hyphen` format
- [ ] `domains.primary` is a working `https://` URL
- [ ] `testCases` contains at least 1 entry you personally verified works
- [ ] `extractorIds` only references IDs that exist in `extractors/registry.json`
- [ ] No parsing logic (selectors, regex, tokens) in the JSON
- [ ] `lifecycle` is set to `"beta"` for new providers (not `"stable"`)
- [ ] `maintainer.github` is your GitHub username
- [ ] `maintainer.lastVerified` is today's date

---

## What Belongs Here vs. In Code

| Belongs in this repo | Belongs in Kotlin/TypeScript code |
|---|---|
| Domain URLs | CSS selectors |
| Capability flags | Regex patterns |
| Extractor IDs | XPath expressions |
| Priority numbers | Authentication tokens |
| Rate limit config | JavaScript deobfuscation logic |
| Test case titles | Any conditional logic |

**If you're tempted to add a selector or regex to a JSON file — don't. Put it in the provider class.**

---

## Reporting a Broken Provider

If a provider stops working:

1. Check `health/health.json` for current status
2. Open an issue using the **Provider Broken** template
3. Include:
   - Provider ID
   - What's broken (search / detail / extractor)
   - Error or symptom you observed
   - New domain if you found one

---

## Updating a Provider's Domain

When a provider changes domains:

1. Update `domains.primary` in `providers/[id].json`
2. Add old domain to `domains.mirrors` if still works as redirect
3. Update `domains.updatedAt` to today
4. Increment `providerVersion` by 1
5. Update `maintainer.lastVerified` to today

---

## Code of Conduct

- Be respectful
- Keep PRs focused (one provider per PR)
- Test before submitting
- Do not add providers that serve illegal content
