# Focus Player — Remaining MVP Tasks
# Claude Code: Read this file and complete each task in order.
# After each task: git add index.html && git commit -m "[message]" && git push origin beta-prep
# Do not stop between tasks unless you hit an error. Report errors and wait for input.
# File: ~/Documents/focus-player/index.html

---

## TASK 6 — Inline Note Editing

Add ability to edit saved notes inline in the notes panel.

1. Each note in the notes panel should have a small edit icon (✏️) that appears on hover/tap
2. Tapping the edit icon converts the note text to an editable text field inline — no modal
3. The text field should be pre-filled with the current note text
4. Show a small Save and Cancel button inline next to the field
5. Saving updates the note in localStorage and Supabase
6. Cancelling restores the original text with no changes
7. Works on both desktop and iPhone touch
8. Do not change the delete (×) button behavior

Commit message: "Feature: Inline note editing added to notes panel"

---

## TASK 7 — Watch & Learn Mode

Add a Watch & Learn mode that any curator profile can enter.

1. Add a "WATCH & LEARN" button visible to curator profiles in the profile bar
2. When activated:
   - Change the session label from "TOR'S SESSION" to "TOR — WATCH & LEARN"
   - Hide all curator tools: Build Lesson, My Lessons, Edit Lesson buttons
   - The profile is now in pure watch and capture mode — same as learner mode
   - Add a small persistent "EXIT WATCH & LEARN" button in the top bar so they can return to curator mode
3. Watch & Learn mode persists until EXIT is clicked — survives page interactions but resets on profile switch
4. Learner profiles do not see the Watch & Learn button — they are always in watch mode by default
5. All thought capture, notes, and Supabase saving works exactly as normal in this mode

Commit message: "Feature: Watch & Learn mode added for curator profiles"

---

## TASK 8 — Multiple Learners Per Lesson + Lesson Queue

Two related features — complete both before committing.

### Part A — Assign Lesson to Multiple Learners
1. In the lesson builder, change "Assign to Learner" from a single dropdown to a multi-select
2. Allow selecting multiple learner profiles for one lesson
3. When saved, create one lesson record per learner in Supabase — each learner gets their own independent copy
4. Each copy has its own notes and session data

### Part B — Learner Lesson Queue with Status
1. When a learner selects their profile, show their assigned lessons in a queue
2. Each lesson shows one of three statuses:
   - 🟢 NEW — assigned, never started
   - ⏳ IN PROGRESS — started but not completed  
   - ✅ DONE — all videos completed
3. Learners see ONLY lessons assigned to them — never other learners lessons or unassigned lessons
4. Status updates automatically:
   - NEW → IN PROGRESS when first video starts
   - IN PROGRESS → DONE when final video completes
5. Use the existing status column in the Supabase lessons table — values: 'new', 'in_progress', 'completed'
6. Curators still see all lessons in My Lessons panel as before

Commit message: "Feature: Multiple learners per lesson and learner queue with status indicators"

---

## TASK 9 — Landscape Cinematic Mode Final Fix

The landscape cinematic mode on iPhone needs a final fix. Video is zooming/cropping instead of fitting cleanly.

Correct behavior:
1. Video fills available height (100vh minus 56px transport bar) at 16:9 ratio
2. If video is narrower than screen width — black bars on left and right sides (letterbox)
3. Transport bar fixed at bottom — 56px height — showing only: rewind, play/pause, stop, forward buttons
4. Everything else hidden: profile bar, URL bar, lesson banner, notes panel
5. Background is pure black #000 everywhere including letterbox bars
6. No scrolling in any direction
7. Thought capture modal still appears on pause — centered on screen, fits within viewport
8. Rotating back to portrait restores full UI immediately

Implementation rules:
- Use only JavaScript resize event detection — no CSS orientation media queries
- When window.innerWidth > window.innerHeight → add class 'is-landscape' to body
- When window.innerHeight > window.innerWidth → remove class 'is-landscape' from body
- All landscape styles use body.is-landscape selector only
- Use object-fit: contain on the video element to prevent cropping

Commit message: "Fix: Landscape cinematic mode final — letterbox 16:9 fit"

---

## TASK 10 — Final Beta Prep Commit

1. Do a final review of index.html for any console errors, broken references, or leftover debug code
2. Remove any console.log debug statements added during development
3. Verify all 5 tasks above were committed successfully by running: git log --oneline -8
4. Do a final commit with message: "MVP beta-ready — Tasks 6-10 complete"
5. Push to beta-prep branch
6. Report back the full git log so the developer can verify all commits before Netlify deploy

Commit message: "MVP beta-ready — Tasks 6-10 complete"

---

## AFTER ALL TASKS COMPLETE

Report back:
- List of all commits made this session
- Any warnings or issues encountered
- Confirmation that beta-prep branch is up to date on GitHub
- Ready for manual Netlify deploy of ~/Documents/focus-player/index.html
