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

The AI pipeline went through 10 versions over 33 days, transitioning from gpt-4o to gpt-5. Version 1 spent 5 days systematically uncovering three architectural flaws -- and those findings made v2 possible in just 1 day. All metrics below are measured from production databases.

| Metric (measured) | v2-v4 | v5-v8 | v9 | v10 (gpt-5) |
|---|---|---|---|---|
| **Avg cost/run** | $0.18 | $0.20-$0.25 | $0.43 | $0.58 |
| **Model** | gpt-4o | gpt-4.1 | gpt-4.1 | gpt-5 |
| **Expert citations** | 1.8-2.7 | 12.9-16.8 | 17.5-20.5 | 17.5-20.5 |
| **Quality (R/B)** | 76/83 | 92/95 | 94/95 | 96/91 |

The full story -- including root cause discoveries, key decisions, gpt-5 migration, and quantitative results -- is in the [Development Journey](./docs/portfolio/pipeline-journey.en.md).

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
- [OpenAI](https://openai.com): gpt-4.1 (content generation), gpt-4.1-mini (classification, self-critique), o4-mini (quality checks, ranking)
- [Tavily API](https://tavily.com): Semantic news search + handbook term context enrichment
- Community APIs: HN Algolia + Reddit JSON (community reactions with real comment text)

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
- AI Product Guides (expanding detailed guides)

### 🏗️ Recently Completed (v7)
- News quality overhaul: user-perspective evaluation (76 → 85.3 avg score)
- Layered Reading Design: Expert adds prior work, limitations, practical signals on top of Learner
- Weighted Depth: lead story gets editorial emphasis, supporting stories get minimum coverage
- Community Pulse: real HN/Reddit comment text (not fabricated quotes)
- Bold markdown post-processing (news + handbook)
- 4-persona quality check (Research/Business × Expert/Learner)

**View roadmap:**
- Current sprint: [ACTIVE_SPRINT](./vault/09-Implementation/plans/ACTIVE_SPRINT.md)
- Full phase plan: [Phase-Flow](./vault/09-Implementation/plans/Phase-Flow.md)

## Getting Started

### 📖 As a User

Browse news, terminology, and blog on the 0to1log website.

→ [0to1log.vercel.app](https://0to1log.vercel.app)

### 👨‍💻 As a Developer

To understand the code and architecture:

- **Development Journey**: [Pipeline Journey](./docs/portfolio/pipeline-journey.en.md) — How the AI pipelines evolved through 7 versions, including a rollback lesson and user-perspective quality evaluation
- **Backend Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md) — Pipeline details with Mermaid diagrams
- **Backend setup**: [backend/CLAUDE.md](./backend/CLAUDE.md) — FastAPI + AI pipeline
- **Frontend setup**: [frontend/CLAUDE.md](./frontend/CLAUDE.md) — Astro v5 + Tailwind CSS
- **Korean docs**: [README_KR.md](./README_KR.md) — Korean version
- **Design & Planning**: [vault/](./vault/) — System design & decision history

## Get In Touch

Questions or interested in collaborating?

- 📧 **Email**: [x0to1log@gmail.com](mailto:x0to1log@gmail.com)
- 𝕏 **Twitter/X**: [@x0to1log](https://x.com/x0to1log)
