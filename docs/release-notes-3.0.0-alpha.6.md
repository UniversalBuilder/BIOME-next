# BIOME-next 3.0.0-alpha.6 — clearer projects and meaningful activity reports

- Separate sortable **Group / laboratory** and **Contact** columns in the project list.
- Clarify group naming for a PI, laboratory, department or facility; preserve existing names.
- Exclude missing categories and unrecorded time from each relevant breakdown, with included/excluded project counts below the charts and tables.
- Keep projects without recorded time available in expandable details. Explicit zero values remain included.
- Apply the same rules to CSV and PDF exports and add **coverage.csv**. Full project details remain available in exports.

Coverage is calculated among projects with documented activity in the selected period. Total recorded time still includes sessions without a category and can exceed a breakdown total. No missing time is estimated.

Quit BIOME, extract **BIOME-Windows-portable-3.0.0-alpha.6.zip** into a new program folder, and launch **BIOME/BIOME.exe** with `_internal` beside it. Open your existing catalogue; no project-format migration is needed. Updated offline guides are included.

Unsigned Windows x64 alpha, French interface, dedicated Chrome/Edge application window.

Validation: 66 Python tests, JavaScript sorting, upload validation and delivery-selection checks passed. The compiled Windows application passed relocated standalone checks, including report coverage and PDF/CSV export.
