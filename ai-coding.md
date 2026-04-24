# AI Coding Standards for PyFluent Automation

## 1. Zero Hallucination Policy
- You are a specialist in Ansys PyFluent automation.
- You are strictly forbidden from guessing PyFluent commands or using "hallucinated" TUI paths.
- All code must be based on the provided context in `generated/stubs/` (.pyi files) and `generated/docs/` (.md files).

## 2. Mandatory Wrapper Usage
- Always use the `FluentSessionWrapper` located in `src/fluent_wrapper/session.py` to launch and manage sessions.
- **Example Launch:**
  ```python
  from fluent_wrapper.session import FluentSessionWrapper, FluentLaunchConfig, LaunchMode
  wrapper = FluentSessionWrapper()
  session = wrapper.launch(FluentLaunchConfig(mode=LaunchMode.SOLVER))