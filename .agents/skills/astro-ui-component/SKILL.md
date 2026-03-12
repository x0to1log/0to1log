---
description: Create consistent, localized, and styled Astro components for 0to1log
---

# Astro UI Component Generation Skill

## Trigger
Use when the user asks to:
- "create a new component for X"
- "build a UI for Y"
- "make an Astro component"
- "create a new UI element"

## Design System & Styling Rules
1. **Never use inline styles or ad-hoc Colors.** Use the existing variables from `frontend/src/styles/global.css`.
2. **Vanilla CSS:** Write standard, vanilla CSS inside `<style>` tags within the Astro file unless otherwise specified. Avoid Tailwind classes.
3. **Responsive Design:** Ensure the component is responsive. Use `rem` for sizing where appropriate and utilize media queries for larger screens.
4. **BEM/Structured Naming:** Use structural, readable class names (e.g., `.newsprint-item`, `.newsprint-item__title`).

## Localization (i18n) Rules
1. **Always accept a `locale` prop** (type `Locale` from `src/i18n/index.ts`).
   - Example interface:
     ```typescript
     import type { Locale } from '../../../i18n/index';
     interface Props {
       locale: Locale;
       // other props
     }
     ```
2. **Never hardcode text.** Use the translation objects (`t.ko`, `t.en`) from `src/i18n/index.ts`. If a translation does not exist for the component, add it to the `t` dictionaries.

## Component Structure Pattern
```astro
---
import type { Locale } from '../../../i18n/index';
import { t } from '../../../i18n/index';

// 1. Define Props interface
interface Props {
  locale: Locale;
  title: string;
  // ...
}

// 2. Destructure props
const { locale, title } = Astro.props;

// 3. Setup logic and translation strings
const str = t[locale];
---

<!-- 4. HTML Template -->
<div class="component-name">
  <h3 class="component-name__title">{title}</h3>
  <p class="component-name__desc">{str['some.translation.key']}</p>
</div>

<!-- 5. Styling -->
<style>
  .component-name {
    padding: var(--spacing-4);
    background-color: var(--color-bg-base);
    border: 1px solid var(--color-border);
  }
  .component-name__title {
    color: var(--color-text-base);
    font-size: var(--font-size-lg);
  }
</style>
```

## Quality Checklist
Before finalizing, verify:
- [ ] Component accepts `locale` as a prop appropriately typed.
- [ ] No English/Korean text is hardcoded in the HTML template.
- [ ] CSS relies on `var(--color-...)` for colors.
- [ ] No unhandled errors or missing imports.
