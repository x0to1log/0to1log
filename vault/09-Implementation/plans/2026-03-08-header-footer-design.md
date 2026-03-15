# Header/Footer Navigation Redesign ? Design Doc

**Date:** 2026-03-08
**Author:** Amy (Solo)

## Decision

Adopt an app-transition shell.

- Public product labels: `AI News`, `Handbook`, `Library`
- Internal/admin labels: `Posts`, `Handbook`
- Compatibility route: public AI News continues to live under `/{locale}/log/`

## Navigation Shell Contract

### Web

```
[Brand] [Primary Nav] [Utilities]
```

- Brand stays left-aligned
- Primary nav is fixed to `AI News | Handbook | Library`
- Utilities stay right-aligned
- Language and theme controls move into the utility drawer
- Portfolio is removed from primary navigation and treated as a secondary showcase surface

### Mobile / App

```
[Brand/Page] [Profile or Settings]
[Primary Nav Only]
```

- Utilities do not expand inline in the header
- Primary nav remains front-and-center
- The same IA can later map to app tabs: `AI News | Handbook | Library | Profile`

## Utility Drawer Contract

### Signed-in
- `Library`
- `Language`
- `Theme`
- `Admin` (when permitted)
- `Sign Out`

### Signed-out
- Same trigger shape and placement
- `Language`
- `Theme`
- `Sign In`

## Footer

Footer remains meta/support navigation.

```
About ? Portfolio ? RSS
```

- Do not repeat primary content navigation in the footer
- Keep Portfolio available as a secondary link, not a primary app surface

## Notes

- This redesign changes IA and product language, not the route structure
- `/log` continues to back the public AI News surface
- The goal is to keep web and future app navigation structurally aligned

## Related Plans

- [[plans/2026-03-08-admin-ui-redesign|Admin UI 리디자인]]
