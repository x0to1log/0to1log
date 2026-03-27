# Webhook Success Page Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the `/ko/news/test/` page into a "VIP Ticket" minimalist certificate style layout to celebrate successful Discord webhook integrations.

**Architecture:** We will modify the HTML structure in `src/pages/[locale]/news/test.astro` to add ticket-specific wrapper classes. We will create specific CSS classes in the `<style>` block of the component rather than `global.css` since these styles are highly specific to this page.

**Tech Stack:** Astro, Vanilla CSS, SVG Icons

---

### Task 1: Update HTML Structure & SVG Assets

**Files:**
- Modify: `src/pages/ko/news/test.astro`

**Step 1: Write the updated markup structure**
Replace the `.wh-test-card` with a new structure encompassing a ticket wrapper, an animated SVG seal, a menu-style digest list, and minimal text-link actions. Run `npm run dev` to preview structure.

**Step 2: Commit**
`git commit -m "feat(webhook): update HTML structure for ticket design"`

### Task 2: Implement "VIP Ticket" Layout CSS

**Files:**
- Modify: `src/pages/ko/news/test.astro`

**Step 1: Write CSS for the Ticket Container**
- Add `.wh-ticket-wrapper` with `border`, inner dashed border, and `box-shadow`.
- Add `.wh-seal-icon` with a simple keyframe stroke-dasharray animation for the checkmark.

**Step 2: Write CSS for Menus and Links**
- Style `.wh-menu-list` and `.wh-menu-item` with flexbox and bottom borders.
- Style `.wh-action-links` as elegant bordered ghost buttons.

**Step 3: Test and Commit**
Preview in browser to verify UI.
`git commit -m "style(webhook): apply VIP ticket CSS to success page"`

### Task 3: Testing & Polish

**Files:**
- Test: Browser rendering at `http://localhost:4321/ko/news/test/`.

**Step 1: Verify Desktop & Mobile styling**
Capture screenshots and ensure the 1px borders, typography, and SVG animations render as intended for both light and dark themes.
