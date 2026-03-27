# Webhook Success Page - VIP Ticket Design Spec

## Concept & Goal
The page at `/ko/news/test/` serves as a success state after users connect their Discord webhook for AI news digests. To convey a premium and "celebratory" feel without breaking the 0to1log brand aesthetic, we will redesign it using a "VIP Ticket / Certificate" paradigm.

## Visual Specifications

### 1. The Container (The Ticket)
- **Shape:** A vertically elongated, centered card resembling a beautiful paper ticket or certificate.
- **Border:** 1px solid `var(--color-border)` with an inner 1px dashed or subtle metallic line to simulate physical print.
- **Background:** `var(--color-bg-primary)` floating cleanly on the `var(--color-bg-secondary)` page background.
- **Shadow:** Extremely soft, elegant shadow (`0 12px 24px rgba(0,0,0,0.05)`).

### 2. The Header (The Seal)
- **Graphic:** A minimalist SVG checkmark animation or an elegant circular "seal" at the top center.
- **Title (`h1`):** "준비 완료!" using `Playfair Display` (serif), large size (2.5rem), high contrast (`var(--color-text-primary)`).
- **Subtitle:** Clear, refined sans-serif text stating the webhook is successfully connected.

### 3. The Content (The Menu)
- **Digest List:** Replaces the current bullet points with a structured "fine dining menu" layout.
- **Layout:** Flex columns separated by elegant 1px horizontal dividers (`var(--color-border)`).
- **Items:** 'Research Digest', 'Business Digest', 'Weekly Recap' with their descriptions in muted serif/sans-serif combination.

### 4. The Footer Actions
- **Links:** Replace the large grey blocks with elegant, minimalist text links or finely outlined ghost buttons.
- **Icons:** Thin stroke (1.5px) icons in `var(--color-accent)`.

## Responsive Behavior
- Smoothly scales down on mobile, maintaining the vertical "ticket" ratio but adjusting padding (e.g., from `3rem 4rem` desktop to `2rem 1.5rem` mobile).
