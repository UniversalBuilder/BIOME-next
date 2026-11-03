# BIOME-next 3.0.0-alpha.13 — Report scope and independent time

Each project now has a **Temps & bilan** panel beside its recorded time. The **Exclure ce projet de tous les bilans** checkbox removes an atypical or incomplete project from every report indicator and statistical export, for all periods. An optional reason is retained. Uncheck and save to include the project again; notes, files and time records remain preserved.

**Saisir du temps** adds a dated duration without creating a notebook entry. These durations are additive to notebook time. Historical estimates are explicitly labelled and assigned to their chosen date; split estimates across dates if they cover multiple report periods. Independent records can be corrected or removed with history. Time attached to a notebook entry is still edited from that entry. Avoid re-entering totals that already include recorded notebook sessions.

Unknown durations are no longer displayed as zero. Monthly charts distinguish an unrecorded duration (—) from an explicit recorded zero. Duration averages use only projects with recorded time, including explicit zeros, after manual exclusions. Missing groups, contacts and scientific categories are omitted only from the calculations requiring them.

The report explains retained projects, voluntary exclusions, unknown durations and explicit zeros. Screen totals and JSON, CSV, HTML and PDF exports share the same population. `excluded-projects.csv` preserves the exclusion list and reasons separately; `scope.csv` explains the populations. Historical estimate minutes are included within independent minutes and the overall total, not additional amounts to sum again.

Stale writes are refused, interrupted time transactions recover without duplication, and late responses cannot overwrite another project’s displayed time. Backups and restores retain time records, scope choices and their history.

## Update

Quit BIOME, extract **BIOME-Windows-portable-3.0.0-alpha.13.zip** into a new program folder, keep `_internal` beside `BIOME.exe`, and reopen your existing catalogue. No project-format migration is required. Use alpha.13 or later for reports that must respect project exclusions; older versions do not apply the new scope setting. This remains an unsigned Windows x64 alpha with a French interface.

## Validation

102 Python tests, three JavaScript regression checks, browser workflows for unknown/zero time, exclusions, independent estimates, period boundaries, missing metadata, preserved drafts, navigation races and mobile layouts, plus compiled standalone checks including independent time and report scope from a relocated installation. Tests and guide screenshots use fictional data.
