# trav-cfd-py-fluent

**Zero-Hallucination Context Extractor for Ansys PyFluent.**

This toolkit provides a high-fidelity bridge between a live Ansys Fluent session and your AI coding assistant (e.g., GitHub Copilot). By loading real `.cas` and `.wft` files, it extracts the exact, state-dependent API tree available for your specific physics setup.

## Key Features

* **Split Introspection Engines:** Dedicated crawlers for Solver (fault-tolerant for inactive models) and Meshing (targeted for `TaskObject` workflows).
* **Live Inspector:** A persistent session mode that allows you to tweak settings in the Fluent GUI and instantly refresh your Python stubs without restarting the session.
* **Dynamic Stub Generation:** Stubs are automatically named based on selected branches (e.g., `setup_models.pyi`) to prevent accidental overwrites.
* **AI Guardrails:** Includes a standardized `ai-coding.md` to instruct Copilot on how to use the extracted context without hallucinating commands.

## Expected Input Layout

Base directory should contain:
- `02_Mesh/<workflow_name>.wft`
- `03_PrePost/<case_name>.cas`

## Quick Start (Static Extraction)

```powershell
# 1. Setup environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Generate Meshing Context (Markdown)
python scripts\generate_md_refs.py

# 3. Generate Solver Context (Interactive Menu)
python scripts\generate_stubs.py
```

## The "Live Inspector" Workflow (Recommended)

To keep your AI context in sync while you iterate in the Fluent GUI:

1.  **Open the PyCharm Python Console.**
2.  **Initialize the Session:**
    ```python
    from scripts.live_inspector import *
    start_fluent(r"S:\Path\To\Your\Project\03_PrePost\case.cas")
    ```
3.  **Tweak & Sync:** After changing any model or boundary condition in the Fluent GUI, run:
    ```python
    refresh("1,2") # Re-scans Models (1) and BCs (2)
    ```
    New stubs are instantly written to `generated/stubs/`.

## AI-Assisted Coding

1.  Copy `ai-coding.md` and the `generated/` folder into your active engineering project.
2.  Open the relevant `.pyi` or `.md` files in your IDE.
3.  Prompt Copilot using the files as strict references:
    > *"Referencing #file:setup_models.pyi, write a script using the FluentSessionWrapper to enable the k-omega viscous model."*

## Technical Notes

* **Version Compatibility:** Uses a mapped `UIMode` string ("gui" or "hidden_gui") to support modern `ansys-fluent-core` versions.
* **Network:** Automatically sets `NO_PROXY` for local gRPC communication to bypass enterprise network restrictions.
* **Fault Tolerance:** The Solver crawler uses aggressive error suppression to gracefully skip "Inactive Object" errors common in the Fluent datamodel.