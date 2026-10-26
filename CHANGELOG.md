# Changelog

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
