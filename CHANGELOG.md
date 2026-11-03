# Changelog

## 3.0.0-alpha.13 — 2026-11-03

- Add a reversible, project-level exclusion from all activity report indicators, with an optional reason.
- Add dated independent time records without creating notebook entries, including labelled historical estimates.
- Preserve corrections and removed time records in an audit history; reject stale changes and recover interrupted writes without duplicating time.
- Keep unknown durations distinct from explicit zeros, including project totals, monthly charts and average denominators.
- Omit missing groups, contacts and categories only from calculations requiring those fields; explain report populations and exclusions.
- Align JSON, CSV, HTML and PDF exports, with separate scope and excluded-project tables.
- Protect project views from late responses during navigation and retain existing help, drafts and responsive layouts.

## 3.0.0-alpha.12 — 2026-11-03

- Restore a more vivid Pandora palette with a blue-violet background, cyan lighting and stronger surface contrast.
- Distinguish primary actions, imports, exports and deliveries through blue, violet, green and pink accents.
- Strengthen labelled project status colours and highlight catalogue/report metrics.
- Use luminous chart gradients and stable label-based category colours without changing values or calculations.
- Add colour markers for notebook entry types and retain keyboard help, unsaved drafts and responsive layouts.

## 3.0.0-alpha.11 — 2026-11-03

- Add persistent workspace navigation, clearer project tabs and catalogue overview counts.
- Refine typography with bundled Roboto fonts, consistent weights, quieter borders, subtle gradients and shadows.
- Fit catalogue columns at intermediate widths while retaining horizontal scrolling on small screens.
- Explain actions through mouse and keyboard tooltips, including dynamically created controls.
- Replace the separate help workspace with a discreet question-mark button and contextual modal guidance for screens and editors.
- Preserve unsaved fields and the selected project tab when opening and closing help; return keyboard focus to its trigger.
- Bundle interface assets and font licensing in the Windows portable application; keep the project format unchanged.

## 3.0.0-alpha.10 — 2026-11-02

- Edit the project date and optional known activity date for historical and current projects.
- Offer a valid date found at the start of an original folder name or project title for explicit confirmation.
- Preserve import timestamps and source metadata; allow incomplete historical contacts to remain unknown.
- Do not count administrative information corrections as recent activity or create report sessions from date metadata.
- Use confirmed project dates in catalogue sorting, future data-folder suggestions and frozen delivery summaries.

## 3.0.0-alpha.9 — 2026-11-02

- Stop the desktop application when its last dedicated window closes, after any active server operation finishes.
- Track only session-owned browser windows, with a startup allowance and a brief closure grace period.
- Reopen additional windows through the running application so their lifetime is tracked correctly.
- Use isolated temporary browser sessions and disable background mode; keep headless/server usage unchanged.

## 3.0.0-alpha.8 — 2026-11-02

- Create a named, separate project data folder from the Files tab, with 01_raw, 02_processed, 03_results and a bilingual identifying README.
- Show direct actions to open the data folder and originals, and prefill 01_raw when receiving new images.
- Keep existing linked locations unchanged; reject overwrites, invalid names and catalogue overlaps.
- Test persistent folder linking, original reception, HTTP authentication and the compiled application workflow.

## 3.0.0-alpha.7 — 2026-10-26

- Show the actual running version and prevent the new launcher from silently reopening a different release already running.
- Add directory removal with an affected-project preview and mandatory reassignment for used contacts/groups. Preserve historical records and reject stale previews.
- Serve the packaged application favicon.

## 3.0.0-alpha.6 — 2026-10-26

- Separate sortable group/laboratory and contact columns in the project list.
- Clarify that group labels can identify a PI, laboratory, department or facility.
- Exclude missing categories and unrecorded time per report breakdown; show included and excluded project counts.
- Collapse projects without recorded time in the report details; preserve their records and explicit zero values.
- Use the same coverage rules for screen charts, tables, CSV and PDF exports; add coverage.csv.

## 3.0.0-alpha.5 — 2026-10-19

- Group delivery contents by notebook entry with readable titles and image, script, text and mail previews.
- Preserve selection through filters and allow delivery-specific labels without renaming source files.
- Separate source messages and technical archives; add an explicit review before ZIP creation.
- Freeze readable provenance and labels in each delivery; reject changed selections.
- Cover inventory, previews, ZIP contents and selection behavior with synthetic fixtures.

## 3.0.0-alpha.4 — 2026-10-19

- Fix the remaining old 5 MB / 20 MB validation in the browser save form.
- Test the actual notebook form validation, not only server persistence.

## 3.0.0-alpha.3 — 2026-10-19

- Import messages up to 50 MB and extract illustrations up to 10 MB each,
  with a 50 MB extraction budget and 100 MB per saved entry (100 files).
- Align browser validation, server request budgets and persistence limits so
  large messages can be saved together with their illustrations.
- Cover large-message persistence over HTTP with entirely synthetic fixtures.

## 3.0.0-alpha.2 — 2026-10-16

- Fix external-access checks on Windows with legacy console encodings; preserve
  Unicode paths and handle invalid probe responses without crashing.

- First Windows portable GitHub release with an installable fictional demo.
- English and French illustrated offline guides with 23 actual demo screenshots.
- Explicit succession from legacy BIOME 2.x.
- Correct Windows build and folder-picker script syntax; validate scripts in CI.

## 3.0.0-alpha.1

First source preview of the folder-based redesign, separate from BIOME 2.x.

- Explicit catalogues with separate original-image storage.
- Project notebook, attachments, delivery snapshots and activity reports.
- Verified data receipt, access checks, backups and recoverable project removal.
- Installable fictional demo with generated images and three example projects.
- Windows application window and portable build instructions.

The interface is currently French. English as default and optional translation
packs remain planned. This preview is not a production release or a migration
tool for legacy databases.
