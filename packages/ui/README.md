# `@vigil/ui`

Shared React components, design tokens, and reviewed-state localization support used by the workstation and companion.

## Component workbench

From the repository root:

- `npm --workspace=@vigil/ui run storybook` starts the component workbench.
- `npm --workspace=@vigil/ui run build-storybook` builds the static workbench.
- `npm --workspace=@vigil/ui run test:storybook` renders stories in Chromium, executes interaction checks, and fails on axe accessibility violations.

Stories use `parameters.a11y.test = "error"`; the checker covers automated rules only and does not replace the human WCAG 2.2 AA and clinical usability reviews in `docs/HANDOVER.md`.

The `RightToLeft` story tests the direction container only. It does not add or approve any translated patient copy.
