# Code Review Findings: Repo-Artist

## 1. Executive Summary

The **Repo-Artist** project is a well-structured tool that effectively leverages AI (Google Gemini) to generate architectural diagrams and hero images for software repositories. It supports both a CLI and a Web interface, making it versatile for different workflows. The code is generally clean, readable, and follows Python conventions.

However, there are opportunities for improvement in areas such as **configuration management**, **error handling (especially around LLM responses)**, **security**, and **extensibility**.

---

## 2. Detailed Findings

### 2.1. Core Logic (`repo_artist/core.py`)

*   **Hardcoded Configuration:**
    *   **File Filtering:** The `ignore_dirs`, `important_extensions`, and `important_files` sets are hardcoded in `get_code_context`. This limits flexibility for users who might use different languages or frameworks not covered by these defaults.
    *   **Traversal Depth:** `os.walk` is manually limited to a depth of `3`. This might be too shallow for complex monorepos or enterprise projects.
    *   **Recommendation:** Move these configurations to a separate config file (e.g., `repo_artist.toml` or `pyproject.toml`) or allow them to be overridden via CLI arguments.

*   **LLM Interaction & Robustness:**
    *   **JSON Parsing:** The `analyze_architecture` function relies on `json.loads` to parse the LLM's response. While there is basic logic to strip Markdown code fences, LLMs can be unpredictable (e.g., adding preamble text).
    *   **Retry Logic:** If the JSON parsing fails, the function simply returns `None`. Implementing a retry mechanism (possibly with a "correction" prompt asking the model to fix the JSON) would significantly improve reliability.
    *   **Rate Limiting:** There is no explicit handling for API rate limits. For large batch operations, this could lead to failures.

*   **Image Generation:**
    *   **Pollinations.ai:** The resolution is hardcoded to `1280x720`. Users might want different aspect ratios or resolutions.
    *   **Prompt Engineering:** The prompt generation in `build_hero_prompt` is static. Allowing users to supply a custom "style guide" or prompt template would enhance the creative output.

*   **README Updates:**
    *   **Regex Fragility:** `update_readme_content` uses regex to find existing images. It assumes the filename structure matches what it expects. If a user manually renames the file, the tool might duplicate the image entry.
    *   **Insertion Point:** The logic to insert the image at index 2 (or after the first header) is a reasonable heuristic but might break specific README layouts.

### 2.2. CLI (`scripts/cli.py`)

*   **CI Setup:**
    *   **Hardcoded Template:** The GitHub Actions workflow in `cmd_setup_ci` is a hardcoded Python string. This makes it difficult to read, edit, and lint.
    *   **Recommendation:** Move the workflow content to a template file (e.g., `templates/generate_art.yml`) and read it at runtime.

*   **User Experience:**
    *   **Security:** When prompting for `GEMINI_API_KEY`, the input is echoed to the screen. Using `getpass` would be more secure.

### 2.3. Smart Push (`smart_push.py`)

*   **Security Risk:**
    *   **Shell Injection:** The script uses `subprocess.call(f"git push {args}", shell=True)`. While `sys.argv` comes from the local user, using `shell=True` is generally discouraged due to command injection risks. It is safer to pass the command as a list: `subprocess.call(["git", "push"] + args)`.

*   **Heuristics:**
    *   **Change Detection:** The threshold for "significant changes" (>3 files or >50 lines) is arbitrary and hardcoded. This should be configurable to suit different team workflows.
    *   **Commit History:** The script creates empty commits with `[GEN_ART]` to trigger CI. This pollutes the git history. A better approach might be using `git commit --amend` (if safe) or using a different trigger mechanism like repository dispatch.

### 2.4. Web Backend (`web/backend/`)

*   **Performance:**
    *   **Cloning:** `web/backend/api.py` clones the entire repository (even with `depth=1`) to a temporary directory just to analyze the file structure. For large repositories, this could be slow and bandwidth-intensive.
    *   **Recommendation:** If possible, use the GitHub API (or other provider APIs) to fetch the file tree without cloning the full content.

*   **Error Handling:**
    *   **General:** The API endpoints generally lack granular error handling. For instance, if `git clone` fails, it raises a generic 400 or 500 error. More specific error messages would help the frontend provide better user feedback.

### 2.5. Tests

*   **Coverage:**
    *   Tests in `tests/test_repo_artist.py` cover basic utility functions but lack deep integration tests for the `analyze_architecture` flow.
    *   There are no tests for the `smart_push.py` script logic (e.g., mocking git commands).

## 3. General Recommendations

1.  **Introduce a Configuration File:** Centralize all hardcoded values (thresholds, ignore lists, model names) into a configuration file.
2.  **Secure Subprocess Calls:** Audit all `subprocess` usage to remove `shell=True` where possible.
3.  **Improve LLM Robustness:** Add retries and better JSON sanitization for the Gemini API responses.
4.  **Template Management:** Extract long string templates (like the CI workflow) into external files.
5.  **Logging:** Replace `print` statements in the core logic with a proper `logging` setup to allow for better debugging and log level control (e.g., `DEBUG`, `INFO`).
