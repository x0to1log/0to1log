---
description: Read external article URLs or text and curate them into a structured News item for 0to1log.
---

# News Curation Skill

## Trigger
Use when the user asks to:
- "curate this news: [URL/Text]"
- "summarize this article for news: [URL/Text]"
- "write news curation for [URL/Text]"
- "이거 뉴스 큐레이션 해줘"

## Core Principle
Do not literally translate the source article. Extract only the signal that matters to an audience of engineers, developers, and product makers. Transform a long read into a structured, highly scannable, insight-driven curation.

## Language Strategy
1. **Generate EN first** (authoritative structure). 
2. **Rewrite KO** (localize for the Korean tech community — use natural phrasing, do not literally translate sentences).

## Tone & Voice
- Professional, objective, and dry. 
- Avoid marketing fluff and exaggerations ("revolutionary", "unprecedented"). 
- Focus on technical improvements, cost, performance metrics, and actionable changes.

## Output Format
Output a single JSON object with all DB fields. Once generated, ask the user if they want you to automatically insert it into the database via the `insert_news.ts` script.

```json
{
  "title_en": "OpenAI Releases New Embedding Model v3",
  "title_ko": "OpenAI, 성능 높이고 가격 낮춘 임베딩 모델 v3 출시",
  "slug": "openai-embedding-v3-release",
  "excerpt_en": "A 1-2 sentence high-level summary of the news.",
  "excerpt_ko": "가장 중요한 핵심 내용 1~2줄 요약.",
  "category": "ai-news",
  "tags": ["openai", "embeddings", "llm"],
  "reading_time_min": 3,
  "body_markdown_en": "...",
  "body_markdown_ko": "...",
  "source_url": "https://openai.com/..."
}
```

## Field Rules

### Body Markdown (`body_markdown_en` and `body_markdown_ko`)
Must use exactly the following `##` headers to keep curations structurally identical.

**Structure pattern:**
```markdown
## TL;DR
[One short paragraph (2-3 sentences max) explaining what happened and why it's a big deal.]

## Key Takeaways
- [Concrete fact/release item 1 (e.g. "Cost reduced by 5X to $0.02 / 1k tokens")]
- [Concrete fact/change 2]
- [Concrete fact/performance metric 3]

## Why It Matters
[Insight for engineers/makers. How does this change the way we build? What new use cases does it open up? What is the strategic implication?]

## Source
[Include the original Source URL if available]
```

### Category String (`category`)
Only use:
- `ai-news`

### Slug (`slug`)
- Kebab-case, lowercase English terms. e.g. `openai-embedding-v3-release`. Keep it short and descriptive. 

### Tags (`tags`)
- Provide 2-4 lowercase strings relevant to the topic. Prefer existing common tags (e.g., `llm`, `vercel`, `react`, `database`).

## Quality Checklist
Before finalizing, verify:
- [ ] Language is objective and skips marketing fluff. 
- [ ] `body_markdown` contains exactly 4 `##` sections (TL;DR, Key Takeaways, Why It Matters, Source).
- [ ] KO version is a natural rewrite, not a rigid translation.
- [ ] `Key Takeaways` are bullet points with concrete facts or numbers if available.
