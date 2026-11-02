# BIOME-next 3.0.0-alpha.8 — Structured project data folders

Create an identifiable external data folder directly from the project Files tab. The suggested name includes the project creation date, group, contact, title and a short ID. Choose an existing parent folder outside the catalogue, check the name, then create and link it.

The folder contains 01_raw, 02_processed, 03_results and a bilingual README identifying the project without BIOME. Direct buttons open the project data folder or 01_raw. Image reception automatically proposes 01_raw and retains the existing verified-copy behavior. Existing folders can still be linked without reorganizing them. Existing destinations are never overwritten, and catalogue overlap is rejected.

External originals remain separate from the documentary catalogue and require their own backup. Files deposited manually have no BIOME reception receipt. Existing project folders are not renamed or moved; no project-format migration is required.

Update: quit the previous BIOME instance, extract BIOME-Windows-portable-3.0.0-alpha.8.zip into a new program folder, keep _internal beside BIOME.exe, and reopen your existing catalogue. The running version is shown in the header. This remains an unsigned Windows x64 preview with a French interface.

Validation: 77 Python tests, JavaScript regression checks, compiled standalone folder/reception checks, and a browser test using a fictional project. No real user images or project data are included in the release.
