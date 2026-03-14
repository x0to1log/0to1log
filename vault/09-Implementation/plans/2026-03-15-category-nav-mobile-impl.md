# Category Nav Mobile Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optimize the AI product category navigation tab in `CategoryNav.astro` for mobile devices by implementing a native-feeling horizontal scroll with "Chip" style buttons and scroll snapping.

**Architecture:** Modify existing CSS in `global.css` for `.product-category-nav` and `.product-category-tab` to use responsive padding, remove the gradient mask, style tabs as rounded chips, and introduce CSS scroll snapping.

**Tech Stack:** Astro, CSS

---

### Task 1: Update CSS for Category Nav Container

**Files:**
- Modify: `frontend/src/styles/global.css`

**Step 1: Write the minimal implementation**
We need to remove the gradient mask, negative margins, and add scroll snapping logic to the `.product-category-nav` container.

```css
/* Replace the current .product-category-nav definition */
.product-category-nav {
  position: sticky;
  top: var(--header-h, 0px);
  z-index: 20;
  background-color: var(--color-bg-primary);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  gap: 0.5rem; /* Change from 0 to 0.5rem to space out chips */
  overflow-x: auto;
  scrollbar-width: none;
  /* Use padding for off-screen hint instead of mask */
  padding: 0.75rem 1rem;
  margin: 0; /* Remove negative margin for full width container with inner padding */
  transition: top 300ms ease;
  /* Scroll snapping for native feel */
  scroll-snap-type: x mandatory;
  scroll-padding-left: 1rem; /* Offset snap position by padding */
}
```

**Step 2: Commit**

```bash
cd frontend && git add src/styles/global.css
git commit -m "style: optimize category nav container for mobile scroll snapping"
```

---

### Task 2: Update CSS for Category Tabs (Chips)

**Files:**
- Modify: `frontend/src/styles/global.css`

**Step 1: Write the minimal implementation**
Convert `.product-category-tab` from a text line to a pill/chip shape.

```css
/* Replace the current .product-category-tab and hover/active definitions */
.product-category-tab {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 1rem; /* Better shape for a chip */
  font-size: 0.82rem;
  font-family: var(--font-ui);
  color: var(--color-text-secondary);
  background-color: transparent;
  text-decoration: none;
  border-radius: 9999px; /* Pill shape */
  border: 1px solid var(--color-border); /* Subtle border */
  white-space: nowrap;
  transition: all 0.2s ease;
  /* Snapping item */
  scroll-snap-align: start;
}

.product-category-tab:hover {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  border-color: var(--color-text-muted);
}

.product-category-tab.active {
  background-color: var(--color-text-primary);
  color: var(--color-bg-primary);
  border-color: var(--color-text-primary);
  font-weight: 500;
}
```

**Step 2: Commit**

```bash
cd frontend && git add src/styles/global.css
git commit -m "style: redesign category tabs as interactive chips"
```

