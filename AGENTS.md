# UI/UX design-system instructions

For every UI/UX redesign or new screen in this repository, use the central design reference:
https://github.com/gba45684-lab/premium-ui-library

Before implementing, consult:
- https://github.com/gba45684-lab/premium-ui-library/blob/main/UI_UX_RULES.md
- https://github.com/gba45684-lab/premium-ui-library/blob/main/presets/STYLE_PRESETS.md
- https://github.com/gba45684-lab/premium-ui-library/blob/main/presets/OPEN_SOURCE_RESOURCES.md
- https://github.com/gba45684-lab/premium-ui-library/blob/main/prompts/REDESIGN_PROMPT.md

Rules:
1. Inspect this repository's real framework, routes, components, dependencies, build and tests before editing.
2. Choose one primary style preset and at most one supporting motif. Use Glassmorphism/Liquid Glass-inspired effects selectively and maintain legibility.
3. Preserve existing features, business logic, navigation, data, storage, ads, purchases, authentication and platform behavior unless explicitly asked to change them.
4. Check upstream licenses and framework compatibility before adding dependencies/assets. Do not copy proprietary assets.
5. Build responsive, accessible, performant UI with meaningful loading, empty, error, success and disabled states; respect contrast, focus, touch targets and reduced motion.
6. Run available lint, tests, type checks and build. Report results accurately.
7. Prefer a feature branch and pull request. Never force-push or silently replace production code.
8. Do not claim the central repository automatically updates this app: read its current guidance during UI tasks and adapt it to this project's stack.
