## Agent instructions

The agent is senior.

### Preferred stack

- Use this default stack for personal app development: `Streamlit + Plotly + SQLite`.
- Use Streamlit for UI and workflows, Plotly for interactive charts, and SQLite for month-by-month local persistence.
- Keep stack choices simple unless requirements explicitly justify additional services.

### Typical agent best practices for Streamlit app development

- Build with an app-first mindset: keep `streamlit run` as the primary execution path.
- Prefer simple, readable architecture: split UI, data access, and business logic into separate modules.
- Keep `app.py` (or main entrypoint) thin: orchestrate layout and calls to helper functions only.
- Use `st.session_state` deliberately for cross-interaction state; initialize keys defensively.
- Avoid unnecessary recomputation: cache expensive and stable operations with `st.cache_data` and long-lived resources with `st.cache_resource`.
- Make data loading robust: validate schemas, handle missing values, and surface user-friendly errors.
- Treat widgets as API inputs: sanitize and validate all user-provided values before use.
- Keep reruns predictable: avoid hidden side effects and write idempotent functions.
- Design for responsiveness: minimize blocking calls and show progress indicators for long operations.
- Use forms (`st.form`) when grouped inputs should submit together.
- Keep secrets out of source code: use Streamlit secrets management and environment variables.
- Add structured logging for debugging and production observability.
- Include basic tests for pure logic and utility functions outside the Streamlit UI layer.
- Pin dependencies and document setup/run commands in `README.md`.
- Optimize UX for both desktop and mobile widths; keep layouts simple and scannable.
- Use clear naming, concise docstrings, and small functions to maintain maintainability.
- Fail gracefully: catch expected exceptions, show actionable messages, and preserve user context when possible.
