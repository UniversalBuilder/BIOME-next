# BIOME-next 3.0.0-alpha.2 — first packaged preview

BIOME-next is the actively developed successor to [legacy BIOME 2.x](https://github.com/UniversalBuilder/BIOME). It redesigns project records around explicit, readable documentary catalogues and separate original-image storage. The old repository preserves the legacy application and its history.

## Download and run

- Download **BIOME-Windows-portable-3.0.0-alpha.2.zip**.
- Extract the entire archive and run **BIOME/BIOME.exe**. Keep `_internal` beside it.
- Windows x64 and Chrome or Edge are required. Python is bundled. No administrator installation is required in a writable user folder.
- First launch: create/open a catalogue or install the three fictional demo projects.
- Read the bundled **Guide/guide-utilisateur.fr.html** or **Guide/user-guide.html**. The guide archive is also available separately.
- **SHA256SUMS.txt** provides download checksums.

## Included

Project notebook, time records, scope and contact corrections, linked data, verified original-data receipt, annotated script versions, frozen delivery ZIPs, graphical activity reports with PDF/tabular export, access checks, recoverable project removal, catalogue backup/restore and relocation.

This release includes illustrated English and French guides with 23 actual screenshots using only synthetic demo data. Windows access probes now work independently of the console encoding, including Unicode paths. The Windows source-build script has also been corrected.

## Validation

54 Python tests, JavaScript sorting tests, and a compiled standalone smoke test from a relocated folder with spaces: first launch, catalogue creation, demo installation, external access, PDF export, singleton state, restart and unavailable-storage recovery. These checks do not constitute independent scientific validation.

## Preview limitations

- Interface currently **French**. English default and optional language packs remain planned.
- **Unsigned alpha**, for evaluation with backups; not a stable production release.
- Legacy BIOME 2.x databases are not automatically migrated by this package.
- External originals remain outside catalogue backups and require their own backup.
- CC BY-NC 4.0 is retained; see LICENSE. Public availability does not imply unrestricted commercial reuse.

Source code and subsequent development: https://github.com/UniversalBuilder/BIOME-next
