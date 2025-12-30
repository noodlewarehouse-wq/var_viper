# Var Viper - User Guide 🐍

## Introduction
**Var Viper** is a lightweight, standalone variable explorer for Python. It allows you to visually inspect your Python variables (DataFrames, Arrays, Lists, Dictionaries, and more) in a clean, interactive browser window without requiring complex IDE setups or admin rights.

It is designed to mimic the "Spyder" or "MATLAB" variable explorer experience.

## What is included?
Your folder should contain the following files:
1.  **`var_viper.py`**: The main tool (Viewer & Launcher).
2.  **`var_viper_test_suite.py`**: A demo script to test features.

---

## Installation & Setup (VS Code)
While Var Viper works with any editor, setting it up as a native shortcut in VS Code provides the best experience.

### Step 1: Permanent Storage
Move the `var_viper.py` file to a stable location on your computer where you won't accidentally delete it.
*   *Example:* `C:\Users\YourName\Tools\var_viper.py`

### Step 2: Create a Global Task
This tells VS Code how to run the tool using your currently active Python environment (including venvs).

1.  In VS Code, press `Ctrl + Shift + P` (Command Palette).
2.  Type **"Tasks: Open User Tasks"** and select it.
3.  Paste the following configuration inside the `tasks: []` brackets:

    ```json
    {
        "label": "Var Viper",
        "type": "shell",
        "command": "${command:python.interpreterPath}",
        "args": [
            "-i",  // Interactive mode: Keep session alive
            "C:/Users/YourName/Tools/var_viper.py", 
            "${file}"
        ],
        "group": "test",
        "presentation": {
            "reveal": "always",
            "panel": "shared",
            "focus": true,
            "clear": true  // Optional: Clears terminal before running again
        },
        "isBackground": true,  // Tricks VS Code into thinking it's a service
        "runOptions": {
            "instanceLimit": 1,
            "instancePolicy": "terminateOldest"
        }
    }
    ```
    *Important: Update the path in the code above to match where you saved the file in Step 1.*

### Step 3: Create a Keyboard Shortcut
This allows you to run the tool instantly with one key press.

1.  Press `Ctrl + Shift + P` again.
2.  Type **"Preferences: Open Keyboard Shortcuts (JSON)"** and select it.
3.  Paste the following inside the square brackets `[ ... ]`:

    ```json
    {
        "key": "ctrl+alt+v",
        "command": "workbench.action.tasks.runTask",
        "args": "Var Viper"
    }
    ```
4.  Save the file.

**You are now set up!** Just press **`Ctrl + Alt + V`** while viewing any Python script to inspect its variables.

---

## Manual Usage (Library Mode)
If you do not want to use the automatic launcher, or if you wish to inspect variables at a **specific point** in your code (e.g. inside a loop or at a breakpoint), you can import Var Viper manually.

1.  Ensure `var_viper.py` is accessible to your script (either in the same folder, or added to your `PYTHONPATH`).
2.  Add the following lines to your Python script:

    ```python
    import var_viper
    
    # ... your code ...
    
    # Trigger the viewer at this specific point
    var_viper.show(locals())
    ```
3.  Run your script normally using Python.

---

## Using Other Editors
Var Viper is editor-agnostic. If you use PyCharm, Sublime Text, or just the Command Prompt, you can still use it easily.

*   **Command Line:** Simply run `python path/to/var_viper.py your_script.py`.
*   **PyCharm/Other IDEs:** Configure your "External Tools" or "Run Configuration" to execute `python` with the arguments `path/to/var_viper.py $FilePath`.

---

## Features Overview

### 1. The Sidebar
*   **Smart Previews:** The sidebar lists every variable in your script.
    *   **Lists/Arrays:** Shows the Size, Min, and Max values.
    *   **Scalars:** Shows the actual number or string value.
    *   **DataFrames:** Shows the shape (Rows x Columns).
*   **Resizable:** You can drag the border between the sidebar and the main view to adjust the width.

### 2. The Viewer (Main Area)
*   **DataFrames & Arrays:** Displayed as interactive tables.
    *   **Heatmap Colouring:** Numerical columns are automatically coloured from **Blue (Low)** to **Red (High)** to spot trends instantly.
    *   **Sticky Headers:** Column headers stay fixed at the top while you scroll.
    *   **Resizable Columns:** Click and drag the edge of any column header to change its width.
*   **Dictionaries & Lists:** Displayed as a clickable "Tree View". Click the arrows (▶) to drill down into nested data.
*   **Multi-Dimensional Arrays:** Arrays with 3 or more dimensions (e.g., Image data) are broken down into clickable 2D slices.

### 3. The Theme
Var Viper uses a "Monokai" inspired dark theme designed to be easy on the eyes for long debugging sessions.

---

## Troubleshooting

**Q: My script crashed, but the viewer didn't open.**
A: Var Viper tries to catch errors, but if the crash is severe (like a Syntax Error), it might fail before it starts. Fix the syntax error and try again.

**Q: I don't see my variable in the list.**
A: Ensure the variable is created *before* the script finishes. Also, Var Viper hides "internal" variables (those starting with `_`) and imported modules to keep the view clean.

**Q: The browser window is empty.**
A: This is rare. Refresh the page. If that fails, ensure your browser allows JavaScript (it is required for the interactive features).

---

## Authors & Credits

**Chris Pearce**
*Concept, Design, Testing & Feature Specification*

**GitHub Copilot**
*Implementation & Code Generation*

**Date:** 19th December 2025
