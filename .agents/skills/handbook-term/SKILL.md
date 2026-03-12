# Handbook Term Generation Skill

## Trigger

Use when the user asks to:
- "write a handbook term for [X]"
- "generate handbook content for [X]"
- "create a handbook entry for [X]"
- "handbook term: [X]"

## Language Strategy

1. **Generate EN first** (authoritative version)
2. **Then rewrite KO** — not a direct translation. Rewrite for a Korean-speaking engineer audience. Adjust examples, analogies, and phrasing to feel natural in Korean.

## Tone & Voice

- Senior engineer explaining to a peer over coffee
- Practical and opinionated — say what actually matters in production
- Skip textbook definitions; focus on "why should I care?" and "when does this bite me?"
- Use concrete numbers, real-world scenarios, and system names where appropriate
- Avoid: marketing language, hedging ("it depends"), vague generalities

## Output Format

Output a single JSON object with all DB fields. Once generated, ask the user if they want you to automatically insert it into the database (e.g., via the `insert_term` script if provided, or by writing a quick API request script).

```json
{
  "term": "English Term Name",
  "korean_name": "Korean Name",
  "slug": "kebab-case-slug",
  "difficulty": "beginner | intermediate | advanced",
  "categories": ["primary-cat", "secondary-cat"],
  "related_term_slugs": ["slug-1", "slug-2"],
  "definition_en": "...",
  "definition_ko": "...",
  "plain_explanation_en": "...",
  "plain_explanation_ko": "...",
  "technical_description_en": "...",
  "technical_description_ko": "...",
  "example_analogy_en": "...",
  "example_analogy_ko": "...",
  "body_markdown_en": "...",
  "body_markdown_ko": "..."
}
```

## Field Rules

### Summary Fields (plain text only — NO markdown)

These fields render as `{variable}` in Astro templates, meaning markdown syntax would appear as literal text. Keep them as clean prose.

| Field                   | Purpose                                                        | Length        |
| ----------------------- | -------------------------------------------------------------- | ------------- |
| `definition`            | One-sentence technical definition                              | 1-2 sentences |
| `plain_explanation`     | ELI5-style explanation using everyday analogy                  | 2-3 sentences |
| `technical_description` | How it works under the hood — mechanisms, protocols, data flow | 2-4 sentences |
| `example_analogy`       | Concrete real-world example or analogy                         | 1-2 sentences |

### Body Markdown

The main content. This IS rendered as HTML via `marked`, so full markdown is allowed.

**Structure pattern:**

```markdown
## What It Actually Does

[Core concept explanation — what problem it solves, why it exists]

## How It Works

[Mechanism, architecture, data flow. Use tables or diagrams where helpful]

| Component | Role |
| --------- | ---- |
| ...       | ...  |

## When You'll See It

[Real production scenarios, common use cases]

## Common Pitfalls

[What goes wrong, misconfigurations, performance traps]

## Key Takeaway

[1-2 sentence summary of what to remember]
```

**Rules:**
- Use `##` headers (H2). Do not use H1.
- Tables, code blocks, and lists are encouraged
- Keep sections focused — each should earn its place
- Minimum 3 sections, no maximum
- Total length: 300-800 words (EN), similar for KO

### Categories

Choose 1-4 from this exact list:

- `ai-ml` — AI/ML & Algorithm
- `db-data` — DB / Data Infra
- `backend` — Backend / Service Architecture
- `frontend-ux` — Frontend & UX/UI
- `network` — Network / Communication
- `security` — Security / Access Control
- `os-core` — OS / Core Principle
- `devops` — DevOps / Operation
- `performance` — Performance / Cost Mgt
- `web3` — Decentralization / Web3

Pick the primary category first, then add secondary categories only if the term genuinely spans domains (e.g., "Rate Limiting" could be `backend` + `performance` + `security`).

### Slug

- Kebab-case, lowercase
- Use the English term: `support-vector-machine`, `rate-limiting`, `b-tree-index`
- Keep it short but unambiguous

### Difficulty

- `beginner` — CS101 level, foundational concepts
- `intermediate` — Working engineer should know this
- `advanced` — Senior/specialist territory

### Related Term Slugs

- Reference other handbook terms by their slug only
- Only include terms that are genuinely related (same domain, prerequisite, or frequently compared)
- 2-5 related terms is typical
- If a related term doesn't exist yet, include the slug anyway (it will link when created)

## Quality Checklist

Before finalizing, verify:
- [ ] `definition` is a single crisp sentence (EN), not a paragraph
- [ ] `plain_explanation` uses a concrete analogy, not abstract rewording
- [ ] `technical_description` explains mechanism, not just "what"
- [ ] `body_markdown` has at least 3 `##` sections
- [ ] KO versions are natural rewrites, not translations
- [ ] Categories are from the valid slug list (1-4)
- [ ] Slug is kebab-case and matches the English term
- [ ] No markdown syntax in summary fields
