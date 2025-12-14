# gui/ — GUI package for gedcom-to-visualmap

This README describes the current structure and best practices for the `gui/` package after recent refactors that extract many classes into their own modules and adopt lazy imports to avoid circular dependencies.

Contents (key files)
- `gedcomVisualGUI.py` — package exports / top-level wiring (keeps safe fallbacks).
- `visual_map_frame.py` — main application frame.
- `visual_map_panel.py` — main panel (uses lazy imports and TYPE_CHECKING for types).
- `visual_gedcom_ids.py` — extracted VisualGedcomIds (IDs & colour constants).
- `people_list_ctrl.py` — extracted PeopleListCtrl list control.
- `people_list_ctrl_panel.py` — wrapper panel that hosts the people list and info box.
- `person_dialog.py` — PersonDialog (moved out of gedcomDialogs).
- `family_panel.py` — FamilyPanel (moved out of gedcomDialogs).
- `find_dialog.py`, `html_dialog.py`, `about_dialog.py`, `help_dialog.py`, `config_dialog.py` — dialog modules moved out of `gedcomDialogs.py`.
- `background_actions.py` — background worker thread (lazy-imports heavy helpers at runtime).
- `gedcomDialogs.py` — aggregator that imports the small dialog modules with package-aware fallbacks.

Design decisions and guidelines
- Avoid heavy cross-module imports at module scope. Use lazy (runtime) imports inside functions/methods where needed.
- Use `typing.TYPE_CHECKING` or forward-reference strings for type-only annotations to avoid runtime evaluation that creates cycles.
- Keep small, independent helpers imported at module level. Large or cross-referencing components should be imported lazily.
- Use try/except fallback imports in aggregator files (e.g. `gedcomDialogs.py`) during refactor to keep the package importable.
- Guard event binding when the event ID may be None (binding `None` raises AssertionError).

How to run / quick checks (macOS)
- Run the application:
  - python ./gedcom-to-map/gv.py
- Quick compile/syntax check for one file:
  - python -m py_compile gui/visual_map_panel.py
- Compile all project files (repo root):
  - python -m py_compile $(git ls-files 'gedcom-to-map/**/*.py')
- Import test for a module:
  - python - <<'PY'
    import importlib, traceback
    try:
        importlib.import_module('gui.visual_map_panel')
        print('visual_map_panel import OK')
    except Exception:
        traceback.print_exc()
    PY

Common problems & fixes
- ImportError: partially initialized module (circular import)
  - Move the import into the function/method that needs it (lazy import). Remove mutual top-level imports.
- AssertionError when binding event
  - Ensure the event type/binder is not `None` before calling `Bind(...)`.
- "Variable not allowed in type expression"
  - Use `TYPE_CHECKING`, forward-reference strings (e.g. `Optional["gvOptions"]`) or `Any` for quick fix.
- ModuleNotFoundError for moved files
  - Use package-relative imports (`from .module import X`) and run from project root or ensure PYTHONPATH includes the package root.

Adding new dialogs / panels
1. Create `gui/new_widget.py` with a single class.
2. Add a package-aware import fallback in `gedcomDialogs.py`:
   - try: from .new_widget import NewWidget except Exception: NewWidget = None
3. Import the new widget lazily in callers when showing UI to avoid cycles.

Developer tooling
- Linting / import analysis:
  - pip install ruff
  - ruff check .
- Find remaining top-level imports that may cause cycles:
  - git grep -n "from .*gedcomvisual" || true
  - git grep -n "from .*gedcomVisualGUI" || true

Notes
- During this refactor the code uses defensive try/except imports to tolerate a partially-refactored state. When stable, prefer strict package-relative imports and remove unnecessary fallbacks.
- Keep GUI updates on the main thread; background threads must post events (wx.PostEvent) rather than manipulating widgets directly.

If you want, I can:
- scan the repository for remaining top-level circular imports and produce a patch that converts them to lazy imports, or
- add a short developer checklist to this README for onboarding.