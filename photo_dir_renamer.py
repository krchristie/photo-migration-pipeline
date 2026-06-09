"""
Photo Directory Renamer 
------------------------
Standardizes photo subdirectory names into a uniform format that sorts 
chronologically by date and groups metadata in a predictable order:
- Photographer (or camera owner); "unk" when not known
- Location information; uses a placeholder when not exported from Photos
- A placeholder for people or event descriptions

Format: yyyy_mm_dd-Photographer-Place_peopleORdescription

Pipeline Execution Phase:
Stage 1. This script is run immediately after a batch export
from Apple Photos or iPhotos using the "Moments" feature to preserve the 
original folder names containing time and location metadata.

Key Features:
- Right-to-Left Parsing: Splits names from the right to isolate trailing date 
  components, allowing complex location names containing commas to be 
  handled safely.
- Custom Photographer UI: Displays a window for the user to select or type a 
  photographer name, pulling from shared constants in the utility module.
- Name Normalization: Uses regular expressions to convert location text into 
  clean Alphanumeric/PascalCase strings.

Dependencies:
- photoDir_renamer_utils: Used for shared constants and date parsing logic.

Author:        Karen R. Christie
Original Date: January 2026
Doc Updated:   June 2026
"""

import os
import sys
import re
import tkinter as tk
from tkinter import filedialog
import photo_dir_utils as utils

def ask_photographer_custom(root: tk.Tk):
    """
    Displays a custom dialog window for photographer input.
    
    Replaces standard simpledialog popups to apply text and background 
    colors managed by the shared utility module.

    Side Effects:
        Briefly shows the main window to display the form, then hides it upon completion.

    Args:
        root: The active Tkinter application root window object.

    Returns:
        The string entered by the user, or None if the action was cancelled.
    """
    root.deiconify()
    root.title("Input")
    
    for widget in root.winfo_children():
        widget.destroy()

    # Center the window on the screen
    w, h = 450, 160
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws // 2) - (w // 2)
    y = (hs // 2) - (h // 2)
    root.geometry(f'{w}x{h}+{x}+{y}')

    # Set up the text prompt using the theme text color from utils
    lbl = tk.Label(root, 
                   text="What photographer name or initials should be used?", 
                   fg=utils.TEXT_COLOR,
                   font=("Arial", 10, "bold"))
    lbl.pack(pady=(25, 10))

    entry = tk.Entry(root, width=40)
    entry.pack(pady=5)
    entry.focus_set()

    result = {"val": None}
    wait_var = tk.BooleanVar(value=False)

    def on_submit(event=None):
        result["val"] = entry.get()
        wait_var.set(True)

    def on_cancel():
        result["val"] = None
        wait_var.set(True)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=15)
    
    tk.Button(btn_frame, text="OK", command=on_submit, width=10).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side="left", padx=10)

    root.bind('<Return>', on_submit)
    root.protocol("WM_DELETE_WINDOW", on_cancel)

    root.wait_variable(wait_var)
    root.withdraw()
    
    return result["val"]

def run_renamer():
    """
    Orchestrates the directory renaming pipeline.
    
    Prompts the user for an input folder and photographer name, parses dates 
    and places from existing subdirectories, normalizes the text formatting, 
    and renames the folders on disk.
    """
    root = tk.Tk()
    root.withdraw()

    start_dir = utils.get_start_dir()
    input_dir = filedialog.askdirectory(title="Select the Input Directory", initialdir=start_dir)
    
    if not input_dir:
        print("No directory selected. Exiting.")
        sys.exit()

    utils.save_start_dir(input_dir)

    photographer = ask_photographer_custom(root)
    if photographer is None:
        print("No photographer name entered. Exiting.")
        sys.exit()

    photographer = photographer.strip()
    if not photographer:
        print("Warning: Photographer name is blank. Defaulting to 'notEntered'.")
        photographer = "notEntered"

    print(f"Processing directory: {input_dir}")
    print(f"Photographer: {photographer}")
    print("-" * 40)

    for entry in os.scandir(input_dir):
        if entry.is_dir():
            old_dir_name = entry.name
            place = ""
            formatted_date = ""

            # Date information is consistently at the end of the string. By splitting 
            # from the right, we preserve location names that may contain commas.
            parts = old_dir_name.rsplit(',', 2)

            if len(parts) < 2:
                print(f"SKIP: '{old_dir_name}' does not contain enough commas to be a valid date.")
                continue

            # Reconstruct trailing "Month Day, Year" segment for processing
            date_candidate = parts[-2] + "," + parts[-1]
            parsed_date = utils.parse_date_string(date_candidate)

            if parsed_date:
                formatted_date = parsed_date
                
                # If 3 parts exist, the leftmost part represents the Place
                if len(parts) == 3:
                    raw_place = parts[0]
                    
                    # Convert raw delimiters to spaces to ensure clean capitalization boundaries
                    temp_place = re.sub(r'[._-]', ' ', raw_place)
                    temp_place = temp_place.title()
                    
                    # Strip symbols and whitespaces to generate strict PascalCase strings
                    place = re.sub(r'[^a-zA-Z0-9]', '', temp_place)
                else:
                    place = None
            else:
                print(f"SKIP: extracted end string '{date_candidate}' is not a valid date.")
                continue

            suffix = "_peopleORdescription"

            if place:
                new_dir_name = f"{formatted_date}-{photographer}-{place}{suffix}"
            else:
                new_dir_name = f"{formatted_date}-{photographer}-place{suffix}"

            old_path = os.path.join(input_dir, old_dir_name)
            new_path = os.path.join(input_dir, new_dir_name)

            try:
                # Only call rename if the generated name is different from the current name
                if old_path != new_path:
                    os.rename(old_path, new_path)
                    print(f"Renamed: '{old_dir_name}'  -->  '{new_dir_name}'")
                else:
                    print(f"Skipped: '{old_dir_name}' (Already correctly named)")
            except OSError as e:
                print(f"ERROR: Could not rename '{old_dir_name}'. Reason: {e}")

if __name__ == "__main__":
    run_renamer()
