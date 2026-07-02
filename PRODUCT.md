# Product

## Register

product

## Users

A single deployment/support engineer managing DBS Change Request (CR) deployment work daily on Windows 10/11. Works from a local desktop app — no cloud, no server. Primary context: scanning the dashboard for project status, editing CR links/states, opening folders, writing notes. Secondary: running automations (Outlook drafts, Teams messages), generating reports, maintaining a knowledge base.

## Product Purpose

Track CR projects from UAT preparation through production implementation. Make project state visible and actionable from a single dashboard. Enforce deployment workflow discipline (T-10, state guards, folder transitions). Automate Outlook and Teams communications safely. Keep all data local-first on the filesystem, rebuildable from cache. No cloud, no server, no multi-user.

## Brand Personality

Professional, efficient, no-nonsense. Dense data UI that rewards expertise. Calm confidence — not flashy, not "hacker cool." Desktop-native feel on Windows: dark chrome shell frames a white work canvas. Red accent (DBS red) is punctuation, not a wash.

## Anti-references

- Over-engineered SaaS dashboards with gradient hero metrics and "analytics" panels
- Dark "hacker" tools (green-on-black terminals, cyber/neon aesthetics)
- Glassmorphism or heavy card shadows
- Tiny all-caps "eyebrow" labels above every section
- Generic project management tools (Jira, Trello, Asana clones)

## Design Principles

1. **Dense but scannable.** Every pixel earns its place. Data density rewards daily use; users who spend 8 hours in this tool should find information at a glance, not hidden behind clicks.
2. **Desktop-native, not web-wrapped.** Respect Windows conventions (frameless shell, native titlebar controls, context menus, Explorer-style folder workflows). Don't imitate a browser tab.
3. **State discipline, not freedom.** Workflow transitions are guarded (T-10, folder moves, state machines). The UI makes the next legal action obvious and the rest hard to reach by accident.
4. **Local-first conviction.** Filesystem is truth. The app never pretends to be more available than the files it reads. Cache is rebuildable; data loss is engineered out.
5. **Calm confidence.** Red is accent, not alarm. No unnecessary motion, no badges that shout. A well-organized table communicates more than a decorated card.

## Accessibility & Inclusion

- Clickable non-button elements need keyboard path and focus style (WCAG SC 2.1.1)
- Disabled controls must explain why
- Respect `prefers-reduced-motion` (no animation without fallback)
- Color is never the sole state indicator; text label always present
- Body text contrast targets WCAG AA (≥4.5:1)
