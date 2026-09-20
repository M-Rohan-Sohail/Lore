import re

with open("/home/rohan/.gemini/antigravity-ide/brain/b4ea8319-3ff9-449e-acaf-45a4400bd4b0/task.md", "r") as f:
    content = f.read()

# Replace the messy list with a clean one
clean_list = """# Tasks for CP-17

- `[x]` **Implement IDOR test suite (`test_idor_suite.py`)**
    - `[x]` Consolidate inventory of all data-accessing endpoints from CP-6–CP-15
    - `[x]` Implement `u1` calling endpoints on `u2`'s data
    - `[x]` Verify that brute-force enumeration fails for card URLs
- `[x]` **Full execution of test suite**
    - `[x]` Run `pytest app/tests/test_idor_suite.py` and ensure all test cases pass
- `[x]` **Commit to Git**
    - `[x]` Push current project updates to `backend` branch in `M-Rohan-Sohail/Lore`
"""

with open("/home/rohan/.gemini/antigravity-ide/brain/b4ea8319-3ff9-449e-acaf-45a4400bd4b0/task.md", "w") as f:
    f.write(clean_list)
