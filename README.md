# trav-cfd-py-fluent

State-dependent context extractor for Ansys PyFluent.

This toolkit starts real Fluent sessions, loads your existing dummy project files (`.cas` and `.wft`), and exports static artifacts for local IDE/AI consumption:

- strict-ish `.pyi` stubs for active solver API branches
- minimized structured markdown for active meshing workflow tasks/commands
- a thin, documented session wrapper with enum-driven options

## Expected Input Layout

Base directory should contain:

- `02_Mesh/<workflow_name>.wft`
- `03_PrePost/<case_name>.cas`

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\generate_stubs.py --base-dir "S:\SIMULATIONSDATEN\SIMULATIONS\AKW\imma\trav-cfd-py-fluent"
python scripts\generate_md_refs.py --base-dir "S:\SIMULATIONSDATEN\SIMULATIONS\AKW\imma\trav-cfd-py-fluent"
```

Outputs:

- `generated/stubs/solver_session.pyi`
- `generated/docs/meshing_api_context.md`

## Notes

- Extraction is state dependent: scripts load your real files first, then introspect.
- Loading method names can differ between Fluent versions. Each script tries several known APIs and reports all failure details if none work.
- Unit tests do not require Fluent; they validate renderer and traversal utilities only.

