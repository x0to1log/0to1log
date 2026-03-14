# Default Layer Catalog

Default numbered-layer structure for a software product vault. Customize by adding, removing, or renumbering layers to match the project's knowledge domains.

## Layer Definitions

| Prefix | Layer | Purpose | Suggested Notes |
|--------|-------|---------|-----------------|
| `00` | Root | Vault dashboard and navigation hub | `00-INDEX.md` |
| `01` | Core | Project vision, target audience, roadmap | Project-Vision, Target-Audience, Phases-Roadmap |
| `02` | Architecture | System design, stack choices, database schemas | System-Architecture, Frontend-Stack, Backend-Stack, Database-Schema |
| `03` | AI-System | AI agents, pipelines, prompts, quality gates | AI-Pipeline-Overview, Agent-Catalog, Prompt-Library, Quality-Gates |
| `04` | Content | Content strategy, personas, writing guidelines | Content-Strategy, Persona-System, Global-Local-Intelligence, Handbook-Rules |
| `05` | Business | Strategy, KPIs, monetization, growth loops | Business-Strategy, KPI-Dashboard, Monetization-Roadmap, SEO-Strategy, Growth-Loop |
| `06` | Implementation | Sprint tracking, checklists, phase plans | Active-Sprint, Implementation-Plan, Phase-Checklist, Definition-of-Done |
| `07` | Design | UI patterns, component states, page layouts | Component-Library, Page-Layouts, Animation-Guidelines |
| `08` | Operations | Infra, deployment, cost model, monitoring | Infrastructure-Topology, Deployment-Pipeline, Cost-Model, Backup-Playbook |
| `90` | Archive | Superseded or deprecated notes | Organized in `YYYY-MM/` dated subfolders |
| `99` | Reference | ADRs, API docs, migration records | ADR-Log, API-Endpoints, Database-Migrations |

## Note Type Taxonomy

Each note in a layer should have a clear type. Use these as naming/tagging conventions:

| Type | Naming Convention | Purpose | Example |
|------|-------------------|---------|---------|
| **MOC** | `_MOC.md` | Hub note linking all notes in the layer + cross-layer links | `02-Architecture/_MOC.md` |
| **Spec** | `{Topic}.md` | Detailed specification of a system, feature, or process | `Frontend-Stack.md` |
| **Overview** | `{Domain}-Overview.md` | High-level summary connecting multiple specs | `AI-Pipeline-Overview.md` |
| **Log** | `{Topic}-Log.md` | Append-only record (decisions, changes, meetings) | `ADR-Log.md` |
| **Checklist** | `{Topic}-Checklist.md` | Actionable items with `- [ ]` tasks | `Phase-Checklist.md` |
| **Reference** | `{Topic}-Reference.md` | Lookup table, API docs, schema definitions | `API-Endpoints.md` |

## Customizing Layers

### Adding a Layer

Insert a new numbered folder when a knowledge domain grows beyond 5-8 notes scattered across existing layers:

```
09-Research/       # Academic project: papers, experiments, literature reviews
10-Legal/          # Regulated product: compliance, audits, policies
11-Analytics/      # Data-heavy product: dashboards, metrics, A/B tests
12-Journal/        # Decision log, daily notes, retrospectives
```

### Removing a Layer

If a layer has fewer than 2 notes after 30 days, consider merging its notes into the closest related layer. Move the empty folder to `90-Archive/`.

### Renumbering

Renumber only when the reading order becomes confusing. When renumbering:
1. Present a migration table to the user first
2. Update all `[[wikilinks]]` vault-wide after moving
3. Update the root `00-INDEX.md` links

### Layer Size Guidelines

| Notes in Layer | Action |
|---------------|--------|
| 0-1 | Consider merging into a related layer |
| 2-8 | Ideal range |
| 9-12 | Consider adding sub-grouping via a Topic MOC |
| 13+ | Split into two layers |
