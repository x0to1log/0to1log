# 0to1log

**AI news curation + AI glossary + IT blog platform**

[한국어 버전 보기](./README_KR.md)

## Why We Built This

AI moves fastest in English, and English content is most diverse. But Korean readers face two problems: information gap and fragmentation.

### Four Core Problems

- **News overload** → Which English AI news truly matters?
- **Technical terminology is confusing** → What are "Agent", "RAG", "Fine-tuning"? Why do they matter?
- **News and learning are separated** → How do I systematically understand concepts from today's AI news?
- **Can't find tools after learning** → So many AI products—where do I find them? Which fits me?

**0to1log solves all four in one place.**

## How It Was Built

The AI pipeline went through 5 redesigns over 22 days. Version 1 failed after 5 days and $25 of wasted LLM calls — the architecture was wrong, and no amount of patches could fix it. After deleting everything and rebuilding from scratch, each iteration got exponentially faster: v2 took 1 day, v3 half a day. Six rounds of prompt engineering raised the quality score from 56 to 90 out of 100.

| | v1 | v2 | v3 | v4 | v5–v6 |
|---|---|---|---|---|---|
| **Time** | 5 days (failed) | 1 day | half day | half day | 9 days |
| **Daily cost** | N/A | $0.43 | $0.59 | $0.39 | $0.50–0.80 |
| **Output** | Nothing | 2 articles | 6–10 articles | 6–10 (2 personas) | + quality scoring |

The full story — including what went wrong, key decisions, and quantitative results — is in the [Development Journey](./docs/portfolio/pipeline-journey.en.md).

## The Three Pillars of 0to1log

### 🔍 Daily News Digest

**Automatically curate English AI news with LLM curation.**
Only real important news, no spam.

- **Research persona**: Academic papers & technology trends
- **Business persona**: Business impact & industry shifts
- **Bilingual**: Korean + English simultaneous delivery

**Solves:** News overload + Missing English updates

### 📚 AI Glossary

**Systematically explain core AI terminology.**
Understand concepts from today's news in depth.

- **Basic level**: Simple explanations with analogies and examples
- **Advanced level**: Technical depth with benchmarks, architecture details, and references
- **Auto-linked**: Click terms in news articles to see definitions via popup
- **Quality pipeline**: Tavily search context + type classification + self-critique (score < 75 triggers regeneration) + quality scoring

**Solves:** Confusing terminology + Fragmented learning

### ✍️ Blog & AI Product Guides

**Curate AI tool selection guides and technical insights.**
When new AI products launch, find them, understand differences, learn how to use them.

- **Product comparisons** (ChatGPT vs Claude vs Gemini...)
- **Use cases** (What can I do with this tool?)
- **In-depth technical blog**

**Solves:** Can't find tools after learning + Hard to apply knowledge

## Tech Stack

**Frontend**
- [Astro](https://astro.build) v5: Fast, lightweight static site generation
- [Tailwind CSS](https://tailwindcss.com) v4: Modern design system
- Deploy: [Vercel](https://vercel.com)

**Backend**
- [FastAPI](https://fastapi.tiangolo.com): High-performance Python API framework
- [PydanticAI](https://ai.pydantic.dev/): Type-safe AI agent development
- Deploy: [Railway](https://railway.app)

**Database & Auth**
- [Supabase](https://supabase.com): PostgreSQL-based, built-in Auth & RLS

**AI & Search**
- [OpenAI](https://openai.com): gpt-4.1 (content generation), gpt-4.1-mini (classification, quality checks, self-critique)
- [Tavily API](https://tavily.com): Semantic news search + handbook term context enrichment

**Automation**
- Cron jobs: Daily news pipeline automation
- GitHub Actions: Deployment automation

## Current Status & Roadmap

### ✅ Stable and Running
- Daily News Digest (auto-generated daily)
- AI Glossary (1000+ terms)
- Blog (technical articles publishing)

### 🔄 In Progress
- Weekly Recap (digest bundling, awaiting quality stabilization)
- News quality improvements (prompt audit, citation format normalization)
- AI Product Guides (expanding detailed guides)

**View roadmap:**
- Current sprint: [ACTIVE_SPRINT](./vault/09-Implementation/plans/ACTIVE_SPRINT.md)
- Full phase plan: [Phase-Flow](./vault/09-Implementation/plans/Phase-Flow.md)

## Getting Started

### 📖 As a User

Browse news, terminology, and blog on the 0to1log website.

→ [0to1log.vercel.app](https://0to1log.vercel.app)

### 👨‍💻 As a Developer

To understand the code and architecture:

- **Development Journey**: [Pipeline Journey](./docs/portfolio/pipeline-journey.en.md) — How the AI pipelines evolved through 5 redesigns and 6 prompt iterations
- **Backend Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md) — Pipeline details with Mermaid diagrams
- **Backend setup**: [backend/CLAUDE.md](./backend/CLAUDE.md) — FastAPI + AI pipeline
- **Frontend setup**: [frontend/CLAUDE.md](./frontend/CLAUDE.md) — Astro v5 + Tailwind CSS
- **Korean docs**: [README_KR.md](./README_KR.md) — Korean version
- **Design & Planning**: [vault/](./vault/) — System design & decision history

## Get In Touch

Questions or interested in collaborating?

- 📧 **Email**: [x0to1log@gmail.com](mailto:x0to1log@gmail.com)
- 𝕏 **Twitter/X**: [@x0to1log](https://x.com/x0to1log)
