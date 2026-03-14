---
name: obsidian-vault-architect
description: >-
  Analyze, design, and restructure Obsidian vaults using a project-based
  numbered-layer structure with MOC hub-satellite graph patterns. Use when the
  user asks to: scan/audit a vault, reorganize or restructure folders, create
  MOC index notes, design vault structure, migrate/move/rename notes, fix naming
  issues (e.g. double .md.md extensions), or optimize Obsidian graph view
  connectivity. Also triggers on: "vault 정리", "폴더 구조", "MOC 만들어줘",
  "그래프 뷰 최적화".
---

# Obsidian Vault Architect

Architect Obsidian vaults using a **project-based numbered-layer** structure (not PARA). Each layer = one knowledge domain, numbered for sort order, with MOC hub notes connecting everything for graph view.

## Safety Rules

> [!CRITICAL] Follow these rules for ALL vault operations.

1. **Never delete files.** Unwanted files go to `90-Archive/YYYY-MM/` with the original path noted.
2. **Never overwrite existing note content.** Only append, or create new files.
3. **Bulk operations (3+ files):** Present a migration table and wait for explicit user approval before executing.
4. **Log all moves** in `_migration-log.md` at vault root: `| Date | From | To | Reason |`.
5. **After moves:** Scan vault for broken `[[wikilinks]]` referencing old paths/names. Report and fix them.
6. **Never touch `.obsidian/`** directory or its contents.

## Modes of Operation

### 1. Audit

Scan the vault and report its current state. Output a structured summary.

**Procedure:**
1. List all top-level directories with file counts
2. List root-level files (anything not in a numbered folder)
3. Flag naming issues:
   - Double extensions (`.md.md`)
   - Inconsistent separators (mixed hyphens/spaces/underscores)
   - Casing inconsistencies
4. Identify empty folders (0 files)
5. Identify orphan notes (no inbound or outbound `[[wikilinks]]`)
6. Check for broken wikilinks (links to non-existent notes)
7. Present findings as:

```markdown
## Vault Audit: {vault name}

### Structure
| Folder | Files | Issues |
|--------|-------|--------|
| ...    | ...   | ...    |

### Naming Issues
- ...

### Orphan Notes (no links)
- ...

### Broken Links
- ...

### Recommendations
1. ...
```

### 2. Design

Propose a layer structure tailored to the project. Read [LAYER_CATALOG.md](references/LAYER_CATALOG.md) for default layer definitions and note type taxonomy.

**Procedure:**
1. Ask or infer the project's key knowledge domains
2. Map domains to numbered layers (use catalog as starting point, customize as needed)
3. For each layer, suggest 3-8 notes with types (MOC, Spec, Overview, Log, Checklist)
4. Output as a structure tree:

```
vault/
├── 00-INDEX.md
├── 01-Core/
│   ├── _MOC.md
│   ├── Project-Vision.md       (Spec)
│   └── Phases-Roadmap.md       (Overview)
├── 02-Architecture/
│   ├── _MOC.md
│   └── ...
└── 90-Archive/
```

5. Explain rationale for layer groupings
6. Wait for user approval before executing

### 3. Execute

Create folders, MOC notes, and migrate files. Always follows an approved Design.

**Creating MOC notes:** Read [MOC_TEMPLATES.md](references/MOC_TEMPLATES.md) for templates. Key rules:
- Each layer gets a `_MOC.md` (underscore sorts to top in file explorer)
- Root vault gets `00-INDEX.md` (not underscore-prefixed)
- Every `_MOC.md` must link to all notes in its layer via `[[wikilinks]]`
- Every `_MOC.md` must cross-link to 2-3 related layer MOCs
- Use `obsidian-markdown` skill for wikilink syntax, callouts, and frontmatter

**Creating .base indexes (optional):** Use `obsidian-bases` skill to create `.base` files that provide filtered/sorted views of notes within a layer (e.g., filter by tag, sort by modified date).

## Layer Architecture Principles

- **Numbered prefixes** (`01-`, `02-`, ...) control sort order, not hierarchy depth
- **Flat structure**: each layer folder contains notes directly; avoid deep sub-folders
- **One domain per layer**: if notes span two unrelated topics, split into two layers
- **Special layers**: `00-` root index, `90-Archive`, `99-Reference`
- **Customizable**: the user can add, remove, or renumber layers at any time

See [LAYER_CATALOG.md](references/LAYER_CATALOG.md) for the full default catalog and customization guidelines.

## Migration Execution

### Single File Move
Execute directly. Update `_migration-log.md`. Check for broken links.

### Bulk Move (3+ files)
1. Present a table:

| # | Current Path | New Path | Reason |
|---|-------------|----------|--------|
| 1 | `03-Features/AI-News-Product.md` | `04-Content/AI-News-Product.md` | Content domain |
| 2 | ... | ... | ... |

2. Wait for user approval
3. Execute moves sequentially
4. Update `_migration-log.md`
5. Scan vault for broken `[[wikilinks]]` and fix them
6. Update affected MOC notes

### Fix Double Extensions (`.md.md` → `.md`)
1. List all affected files
2. Present as migration table
3. After approval: rename each file, scan vault for wikilinks referencing old name (without extension — Obsidian usually links by basename, so most links survive)
4. Verify in audit mode

### Folder Rename/Merge
1. Present plan showing old → new folder mapping
2. After approval: create new folder, move all files, update MOCs, archive empty old folder
3. Run audit to verify

## Graph View Optimization

For a well-connected Obsidian graph:
- Every note must have **at least 1 inbound link** from its layer's `_MOC.md`
- Layer MOCs cross-link to **2-3 related** layer MOCs (not all — avoid hairball)
- `00-INDEX.md` links to **all** layer MOCs (hub-and-spoke backbone)
- Notes link to related notes in **other layers** where meaningful (keeps graph connected)
- Avoid orphan notes: after any operation, check for notes with zero links

Result: graph shows **clear clusters** (one per layer) connected through MOC bridge nodes.

## Sibling Skill Integration

- **`obsidian-markdown`** — use for all note content: wikilink syntax, callouts, frontmatter properties, embeds, mermaid diagrams
- **`obsidian-bases`** — use when creating `.base` files for database-like views of notes within a layer
