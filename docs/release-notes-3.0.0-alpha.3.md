# BIOME-next 3.0.0-alpha.3 — larger email exchanges

This preview fixes importing screenshot-heavy email exchanges. Both previewing
and saving now accept the original message together with extracted illustrations.

## Limits

- Original `.msg`, `.eml` or text message: **50 MB**.
- Individual extracted illustration or ordinary attachment: **10 MB**.
- Extracted illustrations: **50 MB total**, at most 99 images alongside the message.
- Saved entry: **100 files / 100 MB total**, including the original message.
- Browser validation, HTTP request limits and saved attachments now agree.

Unsupported or oversized illustrations are reported; their original content remains
in the retained message. Large research datasets should still use separate data
storage rather than notebook attachments. No images are recompressed by this fix.

## Download and update

Download **BIOME-Windows-portable-3.0.0-alpha.3.zip**, extract the entire ZIP
into a new application folder, and run **BIOME/BIOME.exe** after quitting the
previous instance. Keep `_internal` beside the executable. Open your existing
catalogue; no data-format migration is needed. Do not extract the program into
your catalogue or original-data folder.

The package includes English and French offline illustrated guides in **Guide/**.
The separate guide and source archives and **SHA256SUMS.txt** are also provided.
Some older screenshots show alpha.2 attachment limits; the guide text states the
new limits explicitly.

## Validation

56 Python tests, including a synthetic HTTP save larger than the former 35 MB
request limit, JavaScript sorting checks and a compiled standalone check.
The supplied real-world email was checked locally only: the original message and
all eight images were preserved and their hashes verified. It is not included in
the repository, release, public tests or screenshots.

Windows x64; Chrome or Edge for the dedicated application window. This remains
an unsigned alpha with a French interface. Back up catalogues and external
originals separately. Legacy BIOME 2.x databases are not automatically migrated.

BIOME-next continues legacy BIOME: https://github.com/UniversalBuilder/BIOME-next
