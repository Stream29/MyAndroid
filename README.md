# MyAndroid

Android & HyperOS privacy, Play Integrity / TEESimulator-RS tooling, ADB utilities, mobile IME notes, and the [`DashVoice/`](https://github.com/Stream29/DashVoice) voice-input client.

- [`bin/hyperos-privacy`](bin/hyperos-privacy): Audits (`check`) or applies (`apply`) HyperOS/MIUI telemetry, ad, and package lockdown rules over ADB (supports `--hma-config` or automatic local `secret/android/hma-policy.json`).
- [`bin/play-integrity`](bin/play-integrity): Audits (`check`), deploys keybox (`deploy-keybox`), refreshes/aligns PIF & security patches (`sync-pif`), enforces `target.txt` `!` entries (`ensure-targets`), restarts `TEESimulator-RS` (`restart`), and exports local `0700`/`0600` backups (`backup`, including LSPosed/HyperCeiler/KSU config backups).
- [`bin/adb-qr`](bin/adb-qr): Wireless ADB pairing via QR code.
- [`templates/`](templates/): Sanitized baseline templates for [`play-integrity/`](templates/play-integrity/) (`pif.prop`, `security_patch.txt`, core `target.txt`) and [`hyperos-privacy/`](templates/hyperos-privacy/) (`hma-policy.example.json`).
- [`tests/`](tests/): Offline unit and sanitization tests for repository scripts and templates.
- [`DashVoice/`](DashVoice/): Git submodule for the Android voice-input client (`io.github.stream29.dashvoice`).
- [`docs/root-and-modules.md`](docs/root-and-modules.md): Complete KernelSU root setup, Zygisk/LSPosed modules, `TEESimulator-RS` / `PlayIntegrityFix` configuration, self-service troubleshooting SOP, and proxy checklist.
- [`docs/ime.md`](docs/ime.md): Android Fcitx5 / Rime / Kagiroi / RimeSync + RSAF / DashVoice setup notes.
