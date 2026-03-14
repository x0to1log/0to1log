# MOC Templates

Three templates for Map of Content notes. Adapt to the project — replace placeholders (`{...}`) with actual note names.

## 1. Root Index (`00-INDEX.md`)

The vault's entry point. Links to every layer MOC and highlights current status.

```markdown
---
title: "{Project Name} Dashboard"
tags:
  - moc
  - root
---

# {Project Name}

> One-sentence project description.

## Navigation

| Layer | MOC | Focus |
|-------|-----|-------|
| Core | [[01-Core/_MOC\|Core]] | Vision, audience, roadmap |
| Architecture | [[02-Architecture/_MOC\|Architecture]] | System design |
| AI System | [[03-AI-System/_MOC\|AI System]] | Agents, pipelines |
| Content | [[04-Content/_MOC\|Content]] | Strategy, personas |
| Business | [[05-Business/_MOC\|Business]] | KPIs, growth |
| Implementation | [[06-Implementation/_MOC\|Implementation]] | Sprints, plans |

## Current Status

- Phase: [[Active-Sprint]]
- Stack: [[System-Architecture]]
- Recent decisions: [[ADR-Log]]

## Key Flows

- [[AI-Pipeline-Overview]] → [[Persona-System]] → [[Content-Strategy]]
- [[Business-Strategy]] → [[KPI-Dashboard]] → [[Growth-Loop]]
```

## 2. Layer MOC (`_MOC.md`)

Hub note for a single layer. Links to all notes within the layer, grouped by subtopic. Cross-references related layer MOCs.

```markdown
---
title: "{Layer Name}"
tags:
  - moc
  - {layer-tag}
---

# {Layer Name}

> Brief purpose of this layer (1 sentence).

## Notes

### {Subtopic A}
- [[Note-1]] — one-line description
- [[Note-2]] — one-line description

### {Subtopic B}
- [[Note-3]] — one-line description
- [[Note-4]] — one-line description

## Related

- [[{Other-Layer}/_MOC|{Other Layer Name}]] — why this connection matters
- [[{Another-Layer}/_MOC|{Another Layer Name}]] — why this connection matters
```

### Example: Architecture Layer MOC

```markdown
---
title: Architecture
tags:
  - moc
  - architecture
---

# Architecture

> System design decisions and stack documentation for 0to1log.

## Notes

### Stack
- [[System-Architecture]] — high-level system diagram and component overview
- [[Frontend-Stack]] — Astro v5 + Tailwind CSS v4 setup
- [[Backend-Stack]] — FastAPI + Railway configuration

### Data
- [[Database-Schema]] — Supabase PostgreSQL tables and RLS policies

## Related

- [[01-Core/_MOC|Core]] — architecture implements the vision defined here
- [[03-AI-System/_MOC|AI System]] — AI pipeline depends on backend architecture
- [[08-Operations/_MOC|Operations]] — deployment and infra for this architecture
```

## 3. Topic MOC (for large layers)

When a layer exceeds 10 notes, create focused sub-hubs. These live inside the layer folder alongside `_MOC.md`.

```markdown
---
title: "{Topic} MOC"
tags:
  - moc
  - {layer-tag}
  - {topic-tag}
---

# {Topic}

> Focused subset of [[_MOC|{Layer Name}]]: {what this topic covers}.

## Notes

- [[Note-A]] — description
- [[Note-B]] — description
- [[Note-C]] — description

## See Also

- [[_MOC|Back to {Layer Name}]]
- [[{Related-Note}]] — cross-reference
```

## Graph Optimization Tips

- Every note should have at least one inbound `[[link]]` from a MOC
- Layer MOCs should cross-link to 2-3 related layer MOCs (not all)
- Root Index links to all layer MOCs — this creates the hub-and-spoke backbone
- Avoid linking every note to every other note; prefer MOC as intermediary
- Result: graph shows clear clusters (layers) connected through MOC bridges
