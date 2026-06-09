"""
Photo Directory Name Editor
---------------------------
Scans photo subdirectories, checks them against known valid patterns and 
records, and provides automated suggestions from parsed directory names
as well as a manual interactive window for correcting metadata in folder names.

Pipeline Execution Phase:
Stage 1.5 (Optional utility step). This script is run after 'photoDirRenamer.py' 
but before 'photoDirOrganizer.py' to catch, sanitize, and normalize any folder 
names containing typos, unknown places, or missing fields.

Key Features:
- Fallback Heuristic Parsing: Splits strings intelligently to identify and 
  separate the date, photographer, place, and event description segments.
- Context-Aware Validation UI: Flags specific naming issues in real-time 
  and guides the user by highlighting exactly which fields are invalid.
- Dynamic Reference File Updates: Automatically updates local text references 
  when a user inputs and approves a brand-new photographer or location name.

Dependencies:
- photoDir_renamer_utils: Required for date validation rules, configurations, 
  and local text reference management.

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

# --- PARSING LOGIC (Specific to name editing) ---

def heuristic_parse(dir_name, allowed_places):
    """
    Parses a directory name into its core metadata components.

    Attempts to isolate the date, photographer, place, and description segments
    by cross-referencing tokens against a list of recognized locations.

    Args:
        dir_name (str): The raw directory name to parse.
        allowed_places (set): A collection of known location names.

    Returns:
        tuple: A four-element tuple containing (date, photographer, place, description).
    """
    # 1. Look for a valid date prefix at the beginning of the folder name
    date_match = re.match(r"^(\d{4}_\d{2}_\d{2}(?:_[a-zA-Z])?)", dir_name)
    
    if not date_match:
        # Fallback: Split by hyphens if no standard date prefix is found
        parts = dir_name.split('-')
        d = parts[0] if len(parts) > 0 else ""
        ph = parts[1] if len(parts) > 1 else ""
        pl = parts[2] if len(parts) > 2 else ""
        su = "-".join(parts[3:]) if len(parts) > 3 else "peopleORdescription"
        return d, ph, pl, su

    date_part = date_match.group(1)
    remainder = dir_name[len(date_part):].lstrip('-_')
    tokens = re.split(r'[-_]', remainder)
    tokens = [t for t in tokens if t]

    # 2. Identify the location by checking tokens against known places
    place_part = ""
    found_place_idx = -1
    
    for i, token in enumerate(tokens):
        if token in allowed_places:
            place_part = token
            found_place_idx = i
            break
    
    # 3. Separate the photographer name from the trailing description
    if found_place_idx != -1:
        if found_place_idx == 0:
            photog_part = "" 
        else:
            photog_part = "-".join(tokens[:found_place_idx])
        suffix_tokens = tokens[found_place_idx+1:]
        suffix_part = "-".join(suffix_tokens) if suffix_tokens else "peopleORdescription"
    else:
        photog_part = tokens[0] if tokens else ""
        place_part = tokens[1] if len(tokens) > 1 else ""
        suffix_part = "-".join(tokens[2:]) if len(tokens) > 2 else "peopleORdescription"

    return date_part, photog_part, place_part, suffix_part

# --- GUI LOGIC ---

def create_smart_header(parent, text, error_text):
    """
    Creates a layout row grouping a field label with its validation error message.
    """
    frame = tk.Frame(parent)
    tk.Label(frame, text=text, fg=utils.TEXT_COLOR).pack(side="left")
    if error_text:
        tk.Label(frame, text=f": {error_text}", fg=utils.ERROR_COLOR).pack(side="left")
    return frame

def show_manual_fix_ui(root, current_data, error_map):
    """
    Displays an interactive form window to manually correct folder naming issues.

    Args:
        root (tk.Tk): The underlying Tkinter root window.
        current_data (tuple): Current parsed tokens (date, photog, place, desc).
        error_map (dict): Identified validation errors for each text field.

    Returns:
        tuple: (updated_metadata_tuple, stop_process_flag)
    """
    d, ph, pl, su = current_data
    
    # Clear out widgets from previous folder evaluations
    for widget in root.winfo_children():
        widget.destroy()

    root.title("Edit Folder Metadata")
    
    # DATE FIELD
    header_date = create_smart_header(root, "Date Info (YYYY_MM_DD...)", error_map.get('date'))
    header_date.grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w")
    entry_date = tk.Entry(root, width=50)
    entry_date.insert(0, d)
    entry_date.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

    # PHOTOGRAPHER FIELD
    header_photog = create_smart_header(root, "Photographer", error_map.get('photog'))
    header_photog.grid(row=2, column=0, padx=10, pady=(5, 2), sticky="w")
    entry_photog = tk.Entry(root, width=50)
    entry_photog.insert(0, ph)
    entry_photog.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="w")

    # PLACE FIELD
    header_place = create_smart_header(root, "Place", error_map.get('place'))
    header_place.grid(row=4, column=0, padx=10, pady=(5, 2), sticky="w")
    entry_place = tk.Entry(root, width=50)
    entry_place.insert(0, pl)
    entry_place.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="w")

    # DESCRIPTION FIELD
    header_desc = create_smart_header(root, "People OR Description", error_map.get('desc'))
    header_desc.grid(row=6, column=0, padx=10, pady=(5, 2), sticky="w")
    entry_desc = tk.Entry(root, width=50)
    entry_desc.insert(0, su)
    entry_desc.grid(row=7, column=0, padx=10, pady=(0, 10), sticky="w")

    # BUTTON ACTION HANDLERS
    result_data = {"val": None}
    stop_flag = {"val": False}
    wait_var = tk.BooleanVar(value=False)

    def on_rename():
        result_data["val"] = (
            entry_date.get().strip(),
            entry_photog.get().strip(),
            entry_place.get().strip(),
            entry_desc.get().strip()
        )
        wait_var.set(True)

    def on_skip():
        result_data["val"] = None
        wait_var.set(True)

    def on_end():
        stop_flag["val"] = True
        result_data["val"] = None
        wait_var.set(True)

    # BUTTON LAYOUT
    btn_frame = tk.Frame(root)
    btn_frame.grid(row=8, column=0, pady=20)
    
    tk.Button(btn_frame, text="Save Edits", command=on_rename, width=12).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Skip", command=on_skip, width=12).pack(side="left", padx=5)
    tk.Label(btn_frame, text="   |   ").pack(side="left")
    tk.Button(btn_frame, text="End Process", command=on_end, fg="red", width=12).pack(side="left", padx=5)

    # Center the window on the screen
    root.update_idletasks()
    w = max(root.winfo_reqwidth(), 550)
    h = max(root.winfo_reqheight(), 450)
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws // 2) - (w // 2)
    y = (hs // 2) - (h // 2)
    root.geometry(f'+{x}+{y}')
    
    # Force the window to pop up in front of other applications
    root.deiconify() 
    root.lift()
    root.attributes('-topmost', True) 
    root.after_idle(root.attributes, '-topmost', False)
    
    # Pause code execution until the user interacts with a button
    root.wait_variable(wait_var) 
    root.withdraw()
    return result_data["val"], stop_flag["val"]

# --- MAIN LOGIC ---

def audit_and_edit_names():
    """
    Scans photo subdirectories, flags missing or unapproved tokens, and coordinates 
    automatic corrections or manual user updates via the interface window.
    """
    root = tk.Tk()
    root.withdraw() 
    
    # Get the most recently accessed directory to maintain a consistent starting path
    start_dir = utils.get_start_dir()
    input_dir = filedialog.askdirectory(title="Select Directory to Audit/Edit", initialdir=start_dir)
    
    if not input_dir:
        print("No directory selected. Exiting.")
        root.destroy()
        sys.exit()

    # Save the selected directory path for future sessions or subsequent scripts
    utils.save_start_dir(input_dir)
    
    # Load allowed reference values from utility tracking logs
    allowed_photographers = utils.load_allowed_values(utils.PHOTOG_FILE)
    allowed_places = utils.load_allowed_values(utils.PLACES_FILE)
    
    print(f"Processing: {input_dir}")
    print(f"Loaded {len(allowed_photographers)} photographers and {len(allowed_places)} places.")
    print("-" * 50)

    log_renamed = []
    log_skipped = []
    log_added_photogs = []
    log_added_places = []
    
    user_terminated = False

    try:
        # Sort subdirectories alphabetically to ensure predictable processing order
        entries = sorted([e for e in os.scandir(input_dir) if e.is_dir()], key=lambda e: e.name)
    except OSError as e:
        print(f"Error reading directory: {e}")
        root.destroy()
        return

    for entry in entries:
        if user_terminated:
            break

        original_name = entry.name
        current_name = original_name
        
        # Specific structural rename substitution filter rule
        if "Fiona" in current_name:
            current_name = current_name.replace("Fiona", "Jack")
        
        date_p, photog_p, place_p, suffix_p = heuristic_parse(current_name, allowed_places)
        
        # Validate parsed components against allowed records
        is_date_valid = utils.is_valid_date_format(date_p)
        is_photog_valid = photog_p in allowed_photographers
        is_place_valid = place_p in allowed_places
        
        ideal_name = f"{date_p}-{photog_p}-{place_p}_{suffix_p}"
        
        error_map = {} 
        issues_log = []

        # Evaluate individual components to log specific context issues
        if not is_date_valid: 
            msg = "Invalid Date Format"
            error_map['date'] = msg
            issues_log.append(msg)
            
        if not photog_p:
            msg = "Missing Photographer"
            error_map['photog'] = msg
            issues_log.append(msg)
        elif not is_photog_valid:
            msg = f"Unknown Photographer '{photog_p}'"
            error_map['photog'] = msg
            issues_log.append(msg)
            
        if not is_place_valid:
            if place_p == "place":
                msg = "No place information entered"
            else:
                msg = f"Unknown Place '{place_p}'"
            error_map['place'] = msg
            issues_log.append(msg)

        if suffix_p == "peopleORdescription":
            msg = "No description entered"
            error_map['desc'] = msg
            issues_log.append(msg)
        
        # Skip if the folder is already perfectly named and has no issues
        if not issues_log and ideal_name == original_name:
            continue
            
        # Automatically fix simple syntax spacing/delimiter errors if values are valid
        if not issues_log and ideal_name != original_name:
            try:
                os.rename(os.path.join(input_dir, original_name), os.path.join(input_dir, ideal_name))
                msg = f"AUTO-FIX: '{original_name}' -> '{ideal_name}'"
                print(msg)
                log_renamed.append(msg)
            except OSError as e:
                print(f"ERROR renaming {original_name}: {e}")
            continue

        print(f"MANUAL EDIT REQUIRED: '{original_name}' -> Issue(s): {', '.join(issues_log)}")
        
        # Display the prompt window for folders containing missing or unapproved entries
        result, stop = show_manual_fix_ui(root, (date_p, photog_p, place_p, suffix_p), error_map)
        
        if stop:
            print("\n*** PROCESS STOPPED BY USER ***")
            user_terminated = True
            break
            
        if result:
            new_d, new_ph, new_pl, new_su = result
            
            # Apply default placeholders if the field was left empty
            if not new_ph or not new_ph.strip():
                new_ph = "notEntered"
            if not new_pl or new_pl == "place" or not new_pl.strip():
                new_pl = "place"
            if not new_su or new_su == "peopleORdescription" or not new_su.strip():
                new_su = "peopleORdescription"

            # Append newly approved values to tracking files
            if new_ph and new_ph != "notEntered" and new_ph.strip() and new_ph not in allowed_photographers:
                if utils.add_allowed_value(utils.PHOTOG_FILE, new_ph):
                    allowed_photographers.add(new_ph)
                    log_added_photogs.append(new_ph)
            
            if new_pl and new_pl != "place" and new_pl.strip() and new_pl not in allowed_places:
                if utils.add_allowed_value(utils.PLACES_FILE, new_pl):
                    allowed_places.add(new_pl)
                    log_added_places.append(new_pl)
            
            final_name = f"{new_d}-{new_ph}-{new_pl}_{new_su}"
            
            try:
                old_path = os.path.join(input_dir, original_name)
                new_path = os.path.join(input_dir, final_name)
                if old_path != new_path:
                    os.rename(old_path, new_path)
                    msg = f"MANUAL:   '{original_name}' -> '{final_name}'"
                    print(msg)
                    log_renamed.append(msg)
                else:
                    print("  -> No change made.")
            except OSError as e:
                print(f"  -> ERROR: {e}")
        else:
            print("  -> SKIPPED.")
            log_skipped.append(original_name)

    root.destroy()

    # --- PROCESS CONSOLE SUMMARY REPORT ---
    print("\n" + "="*60)
    print("                 SUMMARY REPORT")
    print("="*60)
    
    print(f"\n--- SUCCESSFUL RENAMES ({len(log_renamed)}) ---")
    if log_renamed:
        for item in log_renamed:
            print(f"  [+] {item}")
    else:
        print("  (None)")

    print(f"\n--- SKIPPED DIRECTORIES ({len(log_skipped)}) ---")
    if log_skipped:
        for item in log_skipped:
            print(f"  [-] {item}")
    else:
        print("  (None)")

    print(f"\n--- DATA FILE UPDATES ---")
    print(f"File: {utils.PHOTOG_FILE}")
    if log_added_photogs:
        for p in log_added_photogs:
            print(f"  [+] Added: {p}")
    else:
        print("  (No changes)")

    print(f"\nFile: {utils.PLACES_FILE}")
    if log_added_places:
        for p in log_added_places:
            print(f"  [+] Added: {p}")
    else:
        print("  (No changes)")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    audit_and_edit_names()
