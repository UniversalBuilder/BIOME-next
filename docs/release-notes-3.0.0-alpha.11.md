# BIOME-next 3.0.0-alpha.11 — Refined interface and contextual help

BIOME-next now has persistent workspace navigation, clearer project tabs and real catalogue overview counts. The Pandora dark theme is retained, with bundled Roboto fonts, consistent sizes and weights, softer borders, subtle gradients, shadows and hover states. Catalogue columns fit intermediate window widths; small screens retain horizontal table scrolling.

The separate help page and large “Understand this screen” button have been replaced by action tooltips and a discreet question-mark button. Tooltips work on mouse hover and keyboard focus. The question mark opens short guidance for the current screen or editor, including project creation, notebook entries, framing, files, original-data reception, deliveries, contacts, activity reports and catalogue management. Closing help preserves unsaved fields and the selected project tab, and returns focus to the trigger.

Fonts and help are included locally, without an external font service. The Windows distribution includes the Roboto licence. The illustrated guides include updated interface screenshots and explain the new help controls.

## Update

Quit BIOME, extract **BIOME-Windows-portable-3.0.0-alpha.11.zip** into a new program folder, keep `_internal` beside `BIOME.exe`, and reopen your existing catalogue. No project-format migration is required. Original data and project documents remain at their existing locations. This remains an unsigned Windows x64 alpha with a French interface.

## Validation

91 Python tests, the three JavaScript regression checks, browser checks for fonts, mouse/keyboard tooltips, contextual dialogs, preserved drafts, project tabs and mobile layout, plus compiled standalone checks from a relocated installation. These checks use generated fictional data and do not constitute a complete accessibility audit.
