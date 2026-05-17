# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Focus Player is a distraction-free YouTube learning player for homeschool families. Live app: https://focusplayermvp.netlify.app

The entire application is a **single static file**: `index.html` (~3600 lines). There is no build system, no package manager, no bundler, no framework, and no `node_modules`. HTML, CSS, and JavaScript are all inline in that one file.

## Running and deploying

- Local dev: `python3 -m http.server 8000` from the repo root, then open http://localhost:8000. There is no watch/reload — refresh the browser to pick up edits.
- Deploy: Netlify auto-publishes the repo root (see `netlify.toml`). Pushing to the deploy branch is the entire release process.
- There are no tests, no linter, and no typecheck. "Verify" means loading `index.html` in a browser and exercising the flow you changed.

## Editing `index.html`

The file is divided into clearly labeled sections delimited by header comments like `// ─── SUPABASE CLIENT ─────────────`. Use these to navigate — `grep -n "^// ───" index.html` lists them. Notable section anchors:

- `<style>` ends at line ~1351; `<script>` begins ~1594.
- `SUPABASE CLIENT` (~1595): creates `sb`, the global Supabase client. Publishable key and URL are hardcoded.
- Profile / screen rendering, lesson library, between-video/clip overlays, clip helpers, controls, thought modal, speech, write queue, table helpers, lesson save/update/fetch, notes rendering — in that rough order.

The codebase uses `var` and ES5-style function declarations throughout. Match the existing style rather than introducing `let`/`const`/arrow functions piecemeal.

## Architecture you need to know before changing anything

**Dual persistence: localStorage is the source of truth; Supabase is async cloud sync.**

Four localStorage keys hold the entire client state:

- `focusplayer_profiles_v1` — family member profiles `{ id, name, color, role }`
- `focusplayer_active_profile_v1` — id of the currently selected profile
- `focusplayer_notes_v3` — all notes for all users (filtered at render time)
- `focusplayer_lessons_v1` — all lessons (curators see all; learners filter by `learnerId`)

Writes to Supabase go through a write queue (search `SUPABASE WRITE QUEUE`) so the UI never blocks on the network. Supabase tables in use: `profiles`, `videos`, `session_events`, `notes`, `lessons`, `lesson_videos`. The `lesson_videos` table is a child of `lessons` and must be deleted before deleting a lesson row (see existing delete flows around lines 2018 and 2621).

**Roles.** Each profile is either `curator` or `learner`. Curators see Build Lesson, My Lessons, and lesson editing UI. Learners only see lessons assigned to them via `learnerId`. Multi-learner assignment creates **one independent lesson row per learner** — each gets its own notes and status. Lesson status uses `new` / `in_progress` / `completed` in the Supabase `lessons.status` column and updates automatically as videos start and finish.

**YouTube player.** Uses the IFrame API hosted on `youtube-nocookie.com` (`window.YTConfig.host` is set before injecting the script). `ytPlayer` is the global player; `ytAPIReady` gates initialization. The player progress loop (`updateProgress` → `checkClipBoundary`) drives clip-boundary enforcement: a single video can be sliced into clips with start/end seconds, and the player auto-advances or ends at clip boundaries.

**Pause = thought capture.** The product premise is that pausing a video opens a thought-capture modal; notes are timestamped to the video position and saved to both localStorage and Supabase. Web Speech API powers voice-to-text capture (see the `SPEECH` section).

**Landscape / cinema mode.** Driven by a JS `resize` listener that toggles `body.is-landscape` based on `window.innerWidth > window.innerHeight` (no CSS orientation media queries — this is intentional, see `tasks.md` Task 9). Cinema mode is a separate user-triggered `body.cinema-mode` class.

## Working conventions

- `tasks.md` is a historical task list that was handed to Claude Code; it documents intent and contains commit-message conventions, but the branch it references (`beta-prep`) is not necessarily the current working branch. Confirm the branch before pushing.
- `KNOWN_ISSUES.md` tracks browser-extension and platform quirks (e.g. Dark Reader overriding the cream theme). Check it before debugging a "broken styling" report.
- Because state is in localStorage, **bumping a storage key suffix (`_v1` → `_v2`) silently wipes user data** on next load. Don't change those key names without a migration path.
- The Supabase publishable key in source is intentional (it's the public anon-style key); do not treat it as a leaked secret.
