# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Pylogfile is a Python logging library (PyPI: `pylogfile`) that is an alternative to the standard `logging` module for simple-to-intermediate scripts, aimed at scientific/engineering/data-analysis use cases. It adds structured metadata, an inline markdown syntax for colorizing terminal output, and efficient binary log file formats. It ships with a CLI tool, `lumber`, for viewing/searching/sorting saved log files.

## Development commands

Install in editable mode (this is how the repo is currently set up, see `build/__editable__.*`):

```
pip install -e .
```

Run tests (uses `unittest`, no other test runner is configured; ~14 files, 240+ cases covering `base.py` and `lumberjack.py`):

```
python -m unittest discover tests
```

Run a single test file / case:

```
python -m unittest tests.test_log_levels_roundtrip
python -m unittest tests.test_log_levels_roundtrip.TestLogLevelRoundTrip.test_round_trip_log_levels
```

Check line coverage (`coverage` isn't a project dependency, install it ad hoc — `base.py` sits at ~97%; `lumberjack.py`'s number will look artificially low, see the Testing section below for why):

```
pip install coverage
python -m coverage run --source=src/pylogfile -m unittest discover tests
python -m coverage report -m
```

Run an example script (useful for manually sanity-checking behavior/output formatting, since much of this library's value is in terminal appearance):

```
python examples/example1.py
python examples/example2_color_override.py
```

The `lumber` CLI entry point (`pylogfile.scripts.lumberjack:main`) is installed via `[project.scripts]` in `pyproject.toml`; run it against a saved log file:

```
lumber examples/test.plflog
```

Build docs (Sphinx, config at `docs/conf.py`, hosted on ReadTheDocs):

```
cd docs && make html
```

## Architecture

Almost all library logic lives in a single module, `src/pylogfile/base.py`. `src/pylogfile/__init__.py` re-exports `base.py`'s public API (via `base.__all__`) and sets `__version__`, so both `import pylogfile; pylogfile.LogPile` and `from pylogfile.base import *` work — `base.py`'s `__all__` is the one source of truth for what's public; don't add a new top-level class/function without adding it there too, or it won't reach `import pylogfile`. The CLI lives separately in `src/pylogfile/scripts/lumberjack.py`.

Core pieces in `base.py`:

- **`LogEntry`**: a single log record (`level`, `message`, `detail`, `timestamp`). Knows how to serialize to/from dict and render itself as a formatted, colorized string (`.str()`).
- **`LogPile`**: the main user-facing object. Holds a thread-safe list of `LogEntry` (protected by `log_mutex`/`run_mutex`, which become no-op `DummyMutex` instances if `use_mutex=False`, since real `Lock`s aren't picklable). Provides level-named logging methods (`.info()`, `.warning()`, `.error()`, etc.), terminal auto-printing above a configurable `terminal_level`, and save/load for both the binary `.plflog` format and JSON (see below — the two now carry equivalent data). There is no autosave functionality — it was removed as dead/unimplemented API surface (the `#TODO: Autosave` stub, `autosave_*` attributes, and `begin_autosave()` no-op are all gone).
- **`LogLevelDefinition`** / **`get_default_levels()`**: log levels are not hardcoded strings — a `LogPile` carries a `log_levels` list of `LogLevelDefinition` (int code, name, and per-level color overrides for each of the 5 markdown color slots). Custom level lists can be passed into `LogPile(level_list=...)` and round-trip through both the v1 `.plflog` format and JSON. This is why `str_to_level`/`level_to_str`/`find_level_in_list` all take a `level_list` argument rather than assuming the module-level constants (`NOTSET`, `LOWDEBUG`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`); both `str_to_level`/`level_to_str` return `None` (not the string "type" they're annotated as) when the level isn't found — callers must check for that. `LogPile.add_level(lvl_int, lvl_name, ...)` registers a level and binds a matching convenience method (e.g. `add_level(25, "NOTICE")` → `pile.notice(msg)`) onto that *instance* only — it's not visible to IDE autocomplete/type checkers, and other `LogPile` instances won't have it.
- **`LogFormat`**: cosmetic/display settings (color palette, whether to show `detail`, newline stripping, etc.) shared by `LogEntry.str()` and `LogPile`. Not persisted by either `save_plflog()` or `save_json()` — only `log_levels` (names/colors) round-trip, not the active `LogFormat`.
- **Markdown engine** (`markdown()`, `mdprint()`): pylogfile has its own inline markdown syntax for coloring terminal text (`>`, `<`, `>:n`, `>>`, lock/unlock via `@:LOCK`/`@:UNLOCK`, backslash-escaping). See the docstring on `markdown()` in `base.py` for the full escape-sequence spec before touching this parser — it's a manual index-walking implementation, not regex-based.

### File formats (`.plflog` and JSON)

There are two on-disk HDF5 (h5py) `.plflog` layouts, auto-detected on load via `_detect_pylogfile_format()`:

- **v0 / "legacy"** (`_save_v0_plflog` / `_load_v0_plflog`): flat datasets under `/logs/` (`message`, `detail`, `timestamp`, `level` as strings). Cannot round-trip custom log levels — always resolves against `get_default_levels()`.
- **v1 / "compressed"** (`_save_v1_plflog` / `_load_v1_plflog`, default for `save_plflog()`): identified by `/_file_info_` attrs (`file_standard="pylogfile.logpile"`, `encoding="compressed"`). Uses dictionary-encoded string tables (`message_table`/`detail_table` + integer `*_id` columns) plus a `/log_levels` group so custom `LogLevelDefinition`s round-trip. Timestamps are stored as int64 epoch-nanoseconds (`_to_epoch_ns` / `_epoch_ns_to_datetime`).

`save_json()`/`load_json()` carry the *same content* as v1 `.plflog` (every log entry, plus the full `log_levels` list with colors), just as a plain JSON dict instead of HDF5 — see `{"file_info": {...}, "log_levels": [...], "logs": [...]}` in `save_json()`. `_level_definition_to_dict()`/`_level_definition_from_dict()` are the shared (de)serializers for the `log_levels` entries, used only by the JSON path (the HDF5 v1 path serializes level defs into HDF5 datasets directly, separately). `load_json()` validates `file_info.file_standard`/`encoding` the same strict way `_load_v1_plflog()` validates its HDF5 attrs, and raises `ValueError` on anything that isn't a `save_json()`-produced file — there's no support for the old bare `{"logs": [...]}` schema.

There used to be deprecated `save_hdf()`/`load_hdf()` wrapper methods forwarding to `save_plflog()`/`load_plflog()`; they've been removed entirely (the format itself is unaffected — `.plflog` files are still HDF5 under the hood — only those legacy method *names* are gone). When adding a new on-disk `.plflog` format revision, follow the existing pattern: bump `format_version` in `_file_info_`, add a new `_save_vX_plflog`/`_load_vX_plflog` pair, and extend `_detect_pylogfile_format()`.

### Lumberjack CLI

`src/pylogfile/scripts/lumberjack.py` is a standalone argparse + interactive REPL script for browsing `.plflog` files (`SHOW`, `INFO`, and other commands with flags like `--index`, `--contains`, `--num`, `--min`/`--max`). Its help text is data-driven from `src/pylogfile/scripts/assets/lumberjack_help.json` (loaded via `importlib.resources`), rather than hardcoded argparse help strings — update that JSON when adding/changing CLI commands.

**Import-time side effects, no `__main__` guard**: `args = parser.parse_args()` and the `help_data` JSON load both run at *module import time*, not inside `main()` or behind `if __name__ == "__main__":`. Two consequences: (1) importing the module at all requires a valid `sys.argv` already in place (a bare positional filename, or argparse raises `SystemExit`); (2) `main()` must be called explicitly — `python -m pylogfile.scripts.lumberjack file.plflog` will parse args but never enter the REPL, since there's nothing at the bottom of the file to invoke `main()`. Only the installed `lumber` console script (`[project.scripts]` in `pyproject.toml`) does that. Because of this, `main()` can't be safely re-invoked multiple times in one process with different `sys.argv`/flags (the parsed `args` global won't change) — `tests/test_lumberjack_cli.py` sidesteps all of this by driving the real `lumber` console script as a subprocess (stdin-fed REPL commands, exactly like a human typing), which is also why `lumberjack.py` shows low coverage.py numbers: those subprocess runs are invisible to a coverage tracer running in the parent test process. `tests/test_lumberjack_utils.py` covers the pure helper functions (`str_to_bool`, `parseIdx`, etc.) in-process instead, which coverage.py *does* see.

## Notes

- Indentation in `base.py` and `lumberjack.py` is tabs, not spaces — match the surrounding file.
- `examples/*.plflog`/`*.json` files are git-ignored (see `.gitignore`: `*.plflog`, `*.json`) and are regenerated by running the example scripts. `.hdf` is a dead naming convention — nothing in the library still writes/reads `.hdf`-labeled output (the `save_hdf`/`load_hdf` method names are gone; `.plflog` is HDF5-based internally regardless of what the file is named).
- `words[N]` in `lumberjack.py`'s REPL command parsing is always a `StringIdx` (needs `.str` before string methods like `.upper()`), never a plain `str` — a missing `.str` crashed `MAX-LEVEL` outright until the comprehensive test pass caught it. That same pass also found `MIN-LEVEL`/`MAX-LEVEL`/`NUM-PRINT` were silently no-ops (they computed a value into a bare local variable instead of `settings.min_level`/`max_level`/`num_print`, which is what `SHOW`/`STATE` actually read) — now fixed, and locked in by `tests/test_lumberjack_cli.py`'s `TestReplLevelCommands`/`test_num_print_then_show_respects_new_limit`. `load_plflog(filename, clear_previous=...)` had the same class of bug — the parameter was dropped when dispatching to `_load_v0_plflog`/`_load_v1_plflog`, so `clear_previous=False` was silently ignored; also fixed, see `test_plflog_formats.py`'s `test_clear_previous_false_appends`.
