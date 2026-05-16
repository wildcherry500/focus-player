# Known Issues — Focus Player Beta

## Dark Reader / Browser Dark Mode Extensions

**Symptom:** Focus Player appears dark/black instead of the cream light theme in Chrome.

**Cause:** Chrome extensions like Dark Reader override the app's CSS color scheme. This is a browser extension issue, not a Focus Player bug.

**Workaround:** Disable Dark Reader (or any dark mode extension) for this site.

**Status:** Partially mitigated — `<meta name="color-scheme" content="light only">` has been added to signal the app's intent to browsers. Full extension override prevention is a V2 item.

---

*Last updated: 2026-05-14*