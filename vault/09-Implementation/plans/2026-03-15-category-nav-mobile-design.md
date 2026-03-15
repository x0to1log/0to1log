# Mobile Optimization for AI Product Category Selection Tab

## Context
The current `CategoryNav.astro` uses a horizontal scroll with `overflow-x: auto` and a gradient mask. On mobile devices, this design has several pain points:
1. The text-only tabs with bottom borders have small touch targets.
2. The gradient mask at the edges makes the text blurry and obscures the availability of more items to scroll.
3. The lack of scroll snapping makes it difficult to align items comfortably.

## Approved Approach: Enhanced "Chip" Style with Native Scroll

We will maintain the horizontal scroll pattern but optimize it for mobile UX following the `ui-ux-pro-max` guidelines.

### Features
1. **Chip-style Buttons**
   - Convert tabs from plain text to rounded "chips" (`border-radius: 9999px`).
   - Active state: Highly visible background color (e.g., solid accent or primary text color) to clearly indicate selection.
   - Inactive state: Transparent or subtle background (`bg-secondary`) with a 1px border.
   - Ensures touch targets are adequately large (aiming for near 44px height).

2. **Clear Scroll Affordance (Off-screen Hint)**
   - Remove the gradient mask (`mask-image`).
   - Use padding such that the last visible chip is partially cut off at the edge of the screen, providing a strong visual cue that horizontal scrolling is possible.
   - Remove the `margin: 0 -1rem` negative margin hack and rely on normal padding, potentially using CSS grid or specific padding behavior for horizontal scroll containers to maintain edge alignment.

3. **Scroll Snapping**
   - Apply `scroll-snap-type: x mandatory` (or proximity) to the container.
   - Apply `scroll-snap-align: start` (or center) to the individual chips.
   - This ensures a smooth, native-feeling scroll experience where items neatly align into place after a swipe.

## Implementation Details

We will likely only need to modify `frontend/src/styles/global.css` and potentially `frontend/src/components/products/CategoryNav.astro` (if HTML adjustments are needed, like removing the spacer/adjusting padding classes).

## Related Plans

- [[plans/2026-03-15-category-nav-mobile-impl|카테고리 모바일 구현]]
- [[plans/2026-03-15-ai-products-design|AI Products 설계]]

