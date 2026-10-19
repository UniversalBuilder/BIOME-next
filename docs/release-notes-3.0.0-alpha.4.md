# BIOME-next 3.0.0-alpha.4 — complete large-message save fix

Alpha.3 raised message parsing, HTTP and persistence limits, but the notebook's
browser save form still enforced the former 5 MB / 20 MB limits. Alpha.4 fixes
that remaining validation, so the prepared message can actually be saved.

Limits remain: 50 MB per message/text file, 10 MB per other file, 100 files and
100 MB per saved entry. Outlook illustration extraction is capped at 50 MB.

A JavaScript regression test now executes the validation taken directly from
the actual save form, with a large synthetic email and screenshots. The real
reported message was also tested locally through the application buttons:
choose message → prepare eight illustrations → save entry → verify all nine
saved files and their hashes. No private message or image is published.

## Update

Quit the previous BIOME application, extract **BIOME-Windows-portable-3.0.0-alpha.4.zip**
into a new program folder, and run **BIOME/BIOME.exe**. Keep `_internal` beside it
and open the existing catalogue. No project-format migration is required.
This fix requires alpha.4; alpha.3 still contains the browser validation bug.

The ZIP includes offline illustrated guides. Sources, guide archive and
**SHA256SUMS.txt** are available separately. This remains an unsigned Windows
x64 alpha with a French interface and a dedicated Chrome/Edge application window.

Validation: 56 Python tests, JavaScript sorting and notebook-upload validation,
compiled standalone smoke test, and the full local browser import/save workflow.
