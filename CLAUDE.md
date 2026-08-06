# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A suite of standalone Python/Tkinter desktop scripts (no shared entry point) that
clean up and organize photo folders exported from Apple Photos / iPhoto. Each
script is run manually by the user, prompts for a directory via a Tkinter file
dialog, and does one job in the pipeline described in `README.md`.

## Project purpose & priority

The end goal is to migrate photos out of Apple Photos/iPhoto into a
chronologically-sorted directory structure with rich metadata (date,
photographer, location, notes), in preparation for a future photo database.
Two things make this active/urgent rather than a nice-to-have:

- Apple Photos' internal ordering makes photos imported from iPhoto hard or
  impossible to find even when the date taken is known — this pipeline's
  rename/organize step is what makes photos findable again.
- Disk space on the source Mac mini is nearly full — deduplication (the
  reporter/comparator/matrix scripts) is urgent, not just cleanup.

## Branches & version status

- **`main` = v1.** Complete and stable. **Do not modify v1 scripts or the
  README (including its pipeline diagram, which is a frozen snapshot of v1
  and is intentionally not being kept in sync) without asking the user
  first.** This CLAUDE.md was originally written against v1/`main`.
- **`version2` = active development.** Refactor in progress:
  - A reusable custom Tkinter UI layer is being added to `utils` (popup
    dir-selection/editing widgets) for persistent output location + custom
    output file naming.
  - CSV/TSV handling is being centralized into `utils`, but as of this
    writing only one script has been migrated to the updated `utils`; most
    others still need their data/log file output redesigned.
  - If asked to work on the refactor, do it on `version2`, not `main`.

## Commands

There is no build system, package manifest, linter, or test suite in this repo
(confirmed: no `requirements.txt`/`pyproject.toml`, no `tests/` directory).
Dependencies are Python 3.6+ stdlib only (`os`, `sys`, `re`, `datetime`, `shutil`,
`tkinter`, `csv`, `stat`) — nothing to install.

Run any script directly, e.g.:
```bash
python3 photo_dir_renamer.py
python3 photo_dir_organizer.py
python3 photo_dir_name_editor.py
python3 photo_dir_reporter.py
python3 photo_dir_matrix.py
python3 photo_dir_comparator_same_system.py
```
Each opens a native file-picker dialog (Tkinter) rather than taking CLI args, so
scripts can't be smoke-tested headlessly — verify changes by reading the code
path and, where feasible, running the script interactively.

There's a `.venv` already in the repo root; activate it with
`source .venv/bin/activate` if you need an isolated interpreter, though it adds
nothing beyond stdlib.

## Pipeline architecture

Scripts are independent entry points that share state only through
`photo_dir_utils.py` and flat text files on disk — there is no orchestrator or
shared CLI. The intended run order:

1. **`photo_dir_renamer.py`** — bulk-renames freshly exported folders (format
   `Location, Month DD, YYYY`) into the pipeline's canonical schema (below).
   Uses `rsplit(',', 2)` to pull the trailing date off safely even when the
   location itself contains commas.
2. **`photo_dir_organizer.py`** — physically moves canonically-named folders
   into `YYYY/YYYY_MM/` calendar subdirectories via `shutil.move()`. Refuses to
   move a folder whose `YYYY_MM` prefix doesn't match the target parent year,
   as a safety boundary against cross-year mistakes.
3. **`photo_dir_name_editor.py`** — interactive Tkinter QA pass. Flags folder
   names with unrecognized photographer IDs or place names (checked against
   `photographerIDs.txt` / `photoPlaces.txt`) and lets the user fix typos or
   register new authorized values on the spot.
4. **`photo_dir_reporter.py`** — recursive TSV inventory scanner for whole
   volumes. Uses an iterative (stack-based, not recursive) DFS via
   `os.scandir` specifically to handle >30,000-item libraries without hitting
   Python's recursion limit. Output: `{Target_Dir}-file_report.tsv`.
5. **Comparator scripts** (consume reporter TSVs, cross-reference two reports)
   — there is no single generic `photo_dir_comparator.py`; the README's
   pipeline diagram doesn't reflect this (see "Branches & version status" —
   that's an intentional frozen-v1-snapshot, not a bug to fix). Instead there
   are three purpose-specific variants — **pick the one matching the actual
   migration scenario**, don't try to generalize them into one:
   - `photo_dir_comparator_same_system.py` — both reports from the same
     ecosystem (iPhoto-only or Photos-only). Matches on
     (normalized filename, size in KB).
   - `photo_dir_comparator_jpg_vs_png.py` — one report from iPhoto, one from
     Photos. Apple's iPhoto→Photos migration commonly re-encodes `.jpg` to
     `.png` and changes file size, so this variant matches on
     (filename stem sans extension, `YYYY_MM_DD` directory-prefix date) and
     ignores size; files with a `" (1)"`-style suffix are flagged
     "check for edited version" instead of auto-matched.
   - `photo_dir_comparator_directory_migration.py` — strict 1:1 verification
     that a copy between machines/drives succeeded. Matches on exact filename
     + size + path relative to a named anchor folder (default
     `'photoDirectory'`) — no normalization, unlike the other two.
6. **Matrix scripts** — likewise two variants rather than one, both reading a
   `photo_dir_reporter.py` TSV and greedily clustering duplicate files into
   "Sets" by shared directory: `photo_dir_matrix.py` (current version per
   README — note its module docstring is stale/copy-pasted from the reporter
   and describes scanning, not matrix analysis; the real behavior is in its
   function bodies) and `photo_dup_matrix.py` (an earlier iteration with
   near-duplicate `normalize_filename`/`get_group_name`/`analyze_directory_sets`
   logic). If asked to modify duplicate-clustering behavior, check which one
   the user actually means and be aware fixes may need to land in both.
   Consolidating the two is real value but is `version2`-refactor work —
   since `main`/v1 is frozen (see "Branches & version status"), don't
   merge/delete either script on `main` without asking first.

## Known duplication sources (domain context, not simple filename matching)

Real-world duplicates in this photo library come from several distinct
sources, which is why deduplication needs several different comparator
strategies rather than one generic algorithm:

- **iPhoto→Photos JPG→PNG conversion**: iPhoto (used roughly 2004–2005,
  possibly as late as ~2017 depending on when the owner upgraded phones)
  stored `.jpg`; importing into Photos converted these to `.png` with the
  same base name. Handled by `photo_dir_comparator_jpg_vs_png.py`.
- **HEIC double-imports**: exact HEIC-format onset date in the library is
  unconfirmed. Due to not understanding how to export modified/edited photos
  out of iPhoto, essentially all photos from iPhoto ended up exported and
  imported twice in full — once in `.heic` format, once in a different (not
  yet confirmed) format — not just the edited ones. This duplication is
  extensive and is **not yet covered by an existing comparator script** —
  flag this as a gap if asked to work on deduplication coverage.
- **Project-export duplicates**: same filename, or with `-1`/`copy` suffixes.
  Handled by `photo_dir_comparator_same_system.py` (via
  `normalize_filename`'s `" copy"`-stripping) and the matrix scripts.
- **Family-contributed duplicates** (from a "celebration of life" project):
  often have completely different filenames from the original, so no simple
  matching rule applies. **Not covered by any current script** — flag as a
  gap if relevant.

## Deduplication safety constraint

When deduplicating or removing "project export" directories (a directory
where a subset of photos — from a handful to hundreds — was exported for a
specific purpose, e.g. a handful of pics for a kid's homework assignment, or
several hundred for an annual family calendar), **never just delete the
directory**. The list of photos that were in each project must be preserved
as future metadata. Relatedly, the user wants a report generated from each
pipeline step (i.e., from running a given script on a target directory) so
they can reconcile what's been processed against what was originally
exported from Apple Photos/iPhoto and confirm every photo is accounted for —
keep this in mind when touching `photo_dir_reporter.py` or any script's
logging/output format.

## Naming convention schema

The whole pipeline enforces one folder-name format end to end:

```
YYYY_MM_DD[_x]-Photographer-Place_Description
```
- `YYYY_MM_DD`: zero-padded date; optional trailing `_a`, `_b`, ... suffix
  disambiguates multiple events on the same date.
- `Photographer`: validated against `photographerIDs.txt`.
- `Place`: PascalCase, punctuation-stripped; literal `place` if unknown.
- `Description`: underscore-joined; literal `peopleORdescription` if blank.

`photo_dir_utils.py` centralizes the shared logic scripts rely on to stay
consistent with this schema: `parse_date_string` / `is_valid_date_format` for
the date component, `normalize_filename` for the `" copy"`-suffix stripping
used by comparators, and `get_start_dir` / `save_start_dir` for remembering
the last-used directory across script runs. When adding logic that touches
filenames, dates, or the allowed-values files, prefer extending
`photo_dir_utils.py` over reimplementing it locally — `photo_dup_matrix.py`
already forked its own copy of `normalize_filename` and that drift is exactly
what to avoid going forward.

## Shared state files

- `~/.renamer_config` — last-used directory, shared across all scripts via
  `photo_dir_utils.get_start_dir`/`save_start_dir`.
- `photographerIDs.txt` / `photoPlaces.txt` — tab-separated allow-lists read by
  `photo_dir_utils.load_allowed_values` and appended to by
  `add_allowed_value`. Both are gitignored (personal data); `.txt.template`
  siblings show the expected format and should be kept in sync if the format
  changes.
- `*_report.tsv`, `*_matrix.tsv` — generated reporter/matrix output, gitignored.

## Known rough edges (see `notesForImprovements.txt`)

This file holds the user's own backlog of planned changes (log-file
improvements for the reporter, organizer UI rework, photographer-ID change
logging, a purple-accent color scheme). It's gitignored, so treat it as the
authoritative source of near-term intent when present, not something to
"clean up."
