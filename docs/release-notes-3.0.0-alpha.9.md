# BIOME-next 3.0.0-alpha.9 — Close the window to quit

Closing the last dedicated BIOME window now shuts down the application and releases its lock. There is no need to click Quitter BIOME first. With multiple application windows, BIOME remains active until the last one closes. Server-side operations already running finish before shutdown; refreshing or minimizing a window does not stop the application.

The launcher uses an isolated temporary browser session with background mode disabled and tracks only its own Chromium windows. Additional windows are opened through the running application so their lifetime is tracked. Personal browser windows and explicitly headless/server launches are unaffected. Quitter BIOME remains available and closes the dedicated windows as well.

Update: quit the old version once, extract BIOME-Windows-portable-3.0.0-alpha.9.zip into a new program folder, keep _internal beside BIOME.exe, and reopen the existing catalogue. No project-format migration is needed. This remains an unsigned Windows x64 alpha with a French interface.

Validation: 82 Python tests, JavaScript regression tests, compiled standalone checks, and a source desktop test in which the user closed the actual demo window with its close button; process exit, lock cleanup and temporary-session cleanup were verified.
