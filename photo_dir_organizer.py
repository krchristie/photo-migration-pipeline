"""
Photo Directory Organizer
-------------------------
Sorts standardized photo subdirectories into structured, nested calendar-month
folders within a target parent calendar-year directory.

Pipeline Execution Phase:
Stage 2. This script is executed immediately after 'photoDirRenamer.py'. It 
scans the directories generated in Stage 1 and groups them chronologically by 
month to establish a maintainable, multi-tiered file system.

Key Features:
- Regular Expression Parsing: Extracts leading 'YYYY_MM' components from folder
  names to determine correct destination paths dynamically.
- Structural Sanity Checking: Validates that the year prefix of each sub-folder
  matches the parent directory name to prevent accidental cross-year nesting.
- Automated Folder Hierarchy Management: Detects existing month directories 
  or creates missing destination folders safely.

Dependencies:
- photoDir_renamer_utils: Utilized for cross-suite persistent path configuration.

Author:        Karen R. Christie
Original Date: January 2026
Doc Updated:   June 2026 (Refactored for Technical Style)
"""

import os
import sys
import shutil
import re
import tkinter as tk
from tkinter import filedialog
import photo_dir_utils as utils

def run_organizer():
    """
    Sorts standardized photo directories into monthly subfolders.

    Prompts the user to select a parent year directory via an interactive UI, 
    scans for valid subdirectories matching the chronological template, 
    validates alignment, creates destination month folders, and moves 
    the subdirectories into their respective targets.

    Side Effects:
        - Creates new subdirectories named 'YYYY_MM' on disk if missing.
        - Relocates physical directories using file system level moves.
        - Generates a console-based operational execution summary.

    Raises:
        OSError: Handled internally if directory enumerations or structural 
                 creation requests fail due to permissions or missing paths.
    """
    # Initialize Tkinter root window and hide it from view
    root = tk.Tk()
    root.withdraw()

    # Get the most recently accessed directory to maintain a consistent starting path
    start_dir = utils.get_start_dir()
    input_dir = filedialog.askdirectory(title="Select Year Directory to Organize", initialdir=start_dir)

    if not input_dir:
        print("No directory selected. Exiting.")
        sys.exit()

# Save the selected directory path for future sessions or subsequent scripts
    utils.save_start_dir(input_dir)

    year_name = os.path.basename(input_dir)
    print(f"Processing Year Directory: {input_dir}")
    print("-" * 50)

    # Issue an explicit warning if the targeted parent directory deviates from a 4-digit token
    if not re.match(r"^\d{4}$", year_name):
        print(f"WARNING: The selected directory '{year_name}' does not look like a Year (YYYY).")

    moved_count = 0
    skipped_count = 0
    created_dirs = set()

    try:
        # Sort subdirectories alphabetically to ensure predictable processing order
        entries = sorted([e for e in os.scandir(input_dir) if e.is_dir()], key=lambda e: e.name)
    except OSError as e:
        print(f"Error reading directory: {e}")
        sys.exit()

    for entry in entries:
        dir_name = entry.name
        
        # Regex Component Breakdown:
        # ^(\d{4})      -> Capture Group 1: Calendar Year (Anchor token at start of string)
        # _(\d{2})      -> Capture Group 2: Calendar Month
        # _\d{2}        -> Day digits (matched explicitly but ignored in downstream logic)
        # (?:_[a-z])?   -> Optional lowercase single-letter suffix (e.g., _a, _b)
        # .* -> Matches remaining trailing alphanumeric and metadata characters
        match = re.match(r"^(\d{4})_(\d{2})_\d{2}(?:_[a-z])?.*", dir_name)

        if match:
            yyyy = match.group(1)
            mm = match.group(2)
            
            # Sanity Check: Verify the subdirectory year matches the parent folder name 
            # to prevent cross-year nesting.
            if yyyy != year_name and re.match(r"^\d{4}$", year_name):
                print(f"SKIP: '{dir_name}' (Year {yyyy} does not match parent {year_name})")
                skipped_count += 1
                continue

            # Construct the destination path using a standard YYYY_MM format
            target_month_dir_name = f"{yyyy}_{mm}"
            target_month_path = os.path.join(input_dir, target_month_dir_name)

            # Create month directory if it does not already exist
            if target_month_dir_name not in created_dirs:
                if not os.path.exists(target_month_path):
                    try:
                        os.mkdir(target_month_path)
                        print(f"Created Directory: {target_month_dir_name}")
                        created_dirs.add(target_month_dir_name)
                    except OSError as e:
                        print(f"ERROR creating directory {target_month_dir_name}: {e}")
                        skipped_count += 1
                        continue
                else:
                    created_dirs.add(target_month_dir_name)

            src_path = os.path.join(input_dir, dir_name)
            dst_path = os.path.join(target_month_path, dir_name)

            try:
                # Skip if the source directory is already the target month directory
                if src_path == target_month_path:
                    continue

                shutil.move(src_path, dst_path)
                print(f"Moved: '{dir_name}' -> '{target_month_dir_name}/'")
                moved_count += 1
            except Exception as e:
                print(f"ERROR moving '{dir_name}': {e}")
                skipped_count += 1

        else:
            # Skip reporting on existing or newly created month directories
            if re.match(r"^\d{4}_\d{2}$", dir_name):
                continue
                
            print(f"SKIP: '{dir_name}' (Does not match YYYY_MM_DD pattern)")
            skipped_count += 1

    print("\n" + "="*50)
    print("             SUMMARY REPORT")
    print("="*50)
    print(f"Month Directories Active: {len(created_dirs)}")
    print(f"Subdirectories Moved:     {moved_count}")
    print(f"Subdirectories Skipped:   {skipped_count}")
    print("="*50)

if __name__ == "__main__":
    run_organizer()
