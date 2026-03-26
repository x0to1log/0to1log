# 0to1log

**AI news curation + AI glossary + IT blog platform for Korean readers**

[한국어 버전 보기](./README_KR.md)

## Why We Built This

AI moves fastest in English, and English content is most diverse. But Korean readers face two problems: information gap and fragmentation.

### Four Core Problems

- **News overload** → Which English AI news truly matters?
- **Technical terminology is confusing** → What are "Agent", "RAG", "Fine-tuning"? Why do they matter?
- **News and learning are separated** → How do I systematically understand concepts from today's AI news?
- **Can't find tools after learning** → So many AI products—where do I find them? Which fits me?

**0to1log solves all four in one place.**

## The Three Pillars of 0to1log

### 🔍 Daily News Digest

**Automatically curate English AI news with LLM curation.**
Only real important news, no spam.

- **Research persona**: Academic papers & technology trends
- **Business persona**: Business impact & industry shifts
- **Bilingual**: Korean + English simultaneous delivery

**Solves:** News overload + Missing English updates

### 📚 AI Handbook

**Systematically explain core AI terminology.**
Understand concepts from today's news in depth.

- **Beginner level**: Simple explanations for newcomers
- **Advanced level**: Technical depth for developers & practitioners
- **Auto-linked**: Click terms in articles to jump to glossary

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
- [OpenAI](https://openai.com): gpt-4.1, gpt-4.1-mini (news curation, glossary generation)
- [Tavily API](https://tavily.com): Semantic news search (latest updates collection)

**Automation**
- Cron jobs: Daily news pipeline automation
- GitHub Actions: Deployment automation

## Current Status & Roadmap

### ✅ Stable and Running
- Daily News Digest (auto-generated daily)
- AI Handbook (1000+ terms)
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

- **Backend Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md) — Pipeline details with Mermaid diagrams
- **Backend setup**: [backend/CLAUDE.md](./backend/CLAUDE.md) — FastAPI + AI pipeline
- **Frontend setup**: [frontend/CLAUDE.md](./frontend/CLAUDE.md) — Astro v5 + Tailwind CSS
- **Korean docs**: [README_KR.md](./README_KR.md) — Korean version
- **Design & Planning**: [vault/](./vault/) — System design & decision history

## Get In Touch

Questions or interested in collaborating?

- 📧 **Email**: [x0to1log@gmail.com](mailto:x0to1log@gmail.com)
- 𝕏 **Twitter/X**: [@x0to1log](https://x.com/x0to1log)
