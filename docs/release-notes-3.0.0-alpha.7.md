# BIOME-next 3.0.0-alpha.7 — version clarity and directory cleanup

The launcher previously reopened any running BIOME instance, including an older release. Alpha 7 detects a different running version and explains how to quit it before launching the new one. The actual running version is now visible in the header. Separate group/laboratory and contact columns and report coverage from alpha 6 remain included.

The directory now offers **Supprimer…**. Unused contacts/groups can be removed after confirmation. Used records require a replacement of the same type, with the affected project list shown first. Current project identities and contact email are updated; notes, deliveries and history are preserved. Stale previews are rejected, and interrupted updates can resume. Trashed projects are unchanged and may reintroduce old records when restored.

The application favicon is included and served without a 404.

**Upgrade:** click **Quitter BIOME** in the old application, extract **BIOME-Windows-portable-3.0.0-alpha.7.zip** into a new program folder, then launch **BIOME/BIOME.exe** with `_internal` beside it. Check that the header displays **3.0.0-alpha.7**. Open your existing catalogue; no format migration is required. Updated offline guides are included.

Unsigned Windows x64 alpha, French interface, Chrome/Edge application window.

Validation: 70 Python tests and JavaScript checks passed. The compiled executable passed standalone checks including favicon, authenticated directory reassignment and exports. Cross-version launch was tested against alpha 6. Interactive visual review was unavailable due to the browser-tool usage limit.
