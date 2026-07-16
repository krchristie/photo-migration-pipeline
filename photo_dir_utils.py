"""
Photo Directory Subsystem Utilities
----------------------------------
Provides shared configuration, file string normalization, directory persistence, 
and date validation utilities utilized across the photo migration pipeline.

================================================================================
"""

import os
import sys
import re
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, ttk

# --- CONFIGURATION CONSTANTS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SCAN_CONFIG_FILE = os.path.join(SCRIPT_DIR, "photo_scan_config.txt")
SAVE_CONFIG_FILE = os.path.join(SCRIPT_DIR, "report_save_config.txt")
PHOTOG_FILE = os.path.join(SCRIPT_DIR, "photographerIDs.txt")
PLACES_FILE = os.path.join(SCRIPT_DIR, "photoPlaces.txt")     

# --- PHOTOGRAPHER DATABASE FALLBACKS ---
DEFAULT_PHOTOG_ID = "unk"
DEFAULT_PHOTOG_NAME = "Unknown Photographer"

# --- FILE NAME OPERATIONS ---

def normalize_filename(filename):
    """
    Removes the trailing ' copy' suffix from a filename stem.

    Enables uniform file-to-file matching by stripping duplication tags added 
    by file system exports.

    Args:
        filename (str): The raw file name to normalize.

    Returns:
        str: The modified filename string without duplicate tags.
    """
    if not filename:
        return ""
    base, ext = os.path.splitext(filename)
    
    # Remove standard export duplication flag
    normalized_base = base.replace(' copy', '')
    return normalized_base + ext

# --- DIRECTORY CONFIG OPERATIONS ---

def get_start_dir(config_file):
    """
    Reads the specified configuration file to retrieve the most recently 
    accessed directory path.

    Args:
        config_file (str): The configuration file path to check.

    Returns:
        str: The absolute path to the directory if valid, otherwise the 
             user's home directory.
    """
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                last_path = f.read().strip()
                if os.path.isdir(last_path):
                    return last_path
        except Exception:
            pass
    return os.path.expanduser("~")

def save_start_dir(config_file, path):
    """
    Saves the target working directory path to its designated configuration file.

    Maintains pipeline continuity across successive scripts by logging 
    the active location.

    Args:
        config_file (str): The specific tracking text file to write into.
        path (str): The directory path to write to disk.
    """
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(path)
    except Exception as e:
        print(f"Warning: Could not save last used directory to {config_file}. {e}")

# --- DATA FILE OPERATIONS ---

def load_allowed_values(filename):
    """
    Loads approved metadata tokens from the first column of a tab-separated file.

    Args:
        filename (str): The text database file to parse.

    Returns:
        set: A collection of unique, approved metadata lookup values.
    """
    allowed = set()
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    parts = line.strip().split('\t')
                    if parts and parts[0]:
                        allowed.add(parts[0])
        except Exception as e:
            print(f"Warning: Could not read {filename}. {e}")
    return allowed

def load_photographer_details(filename):
    """
    Parses the 3-column photographer database file to extract registered IDs 
    and identify the explicitly designated default profile.

    Args:
        filename (str): The photographer tracking text database file path.

    Returns:
        tuple: (list of unique, sorted "ID (Name)" strings with default at index 0, 
                string of the default profile formatted as "ID (Name)",
                dict of all parsed {ID: Name} profiles)
    """
    photog_options = []
    raw_profiles = {}
    default_display = ""
    
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    parts = line.strip().split('\t')
                    if parts and parts[0]:
                        pid = parts[0].strip()
                        name = parts[1].strip() if len(parts) >= 2 else pid
                        
                        raw_profiles[pid] = name
                        display_str = f"{pid} ({name})"
                        photog_options.append(display_str)
                        
                        if len(parts) >= 3 and parts[2].strip().lower() == "default":
                            default_display = display_str
        except Exception as e:
            print(f"Warning: Could not read {filename} for layout generation. {e}")
            
    if not photog_options:
        raw_profiles[DEFAULT_PHOTOG_ID] = DEFAULT_PHOTOG_NAME
        display_str = f"{DEFAULT_PHOTOG_ID} ({DEFAULT_PHOTOG_NAME})"
        photog_options.append(display_str)
        default_display = display_str
    elif not default_display:
        default_display = photog_options[0]
        
    sorted_options = sorted(list(set(photog_options)))
    if default_display in sorted_options:
        sorted_options.remove(default_display)
        
    return [default_display] + sorted_options, default_display, raw_profiles

def initialize_template_files():
    """
    Checks for the existence of required configuration and tracking files.
    Generates clean template baselines if they are missing from the script folder.
    """
    if not os.path.exists(PHOTOG_FILE):
        try:
            with open(PHOTOG_FILE, 'w', encoding='utf-8') as f:
                f.write("# Photographer ID Database\n")
                f.write("# Format: ID<tab>Full Name<tab>Role\n")
                f.write("# Note: Use 'default' in column 3 to set the GUI default selection.\n")
                f.write(f"{DEFAULT_PHOTOG_ID}\t{DEFAULT_PHOTOG_NAME}\tdefault\n")
            print(f"  [Init] Generated baseline photographer template at: {PHOTOG_FILE}")
        except Exception as e:
            print(f"Warning: Could not initialize template {PHOTOG_FILE}. {e}")

    if not os.path.exists(PLACES_FILE):
        try:
            with open(PLACES_FILE, 'w', encoding='utf-8') as f:
                f.write("# Approved Locations Database\n")
                f.write("# Format: Token Name<tab>Optional Notes\n")
                f.write("Home\tDefault primary residence\n")
            print(f"  [Init] Generated baseline places template at: {PLACES_FILE}")
        except Exception as e:
            print(f"Warning: Could not initialize template {PLACES_FILE}. {e}")

    if not os.path.exists(SCAN_CONFIG_FILE):
        try:
            with open(SCAN_CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(os.path.expanduser("~"))
            print(f"  [Init] Generated baseline scan path configuration at: {SCAN_CONFIG_FILE}")
        except Exception as e:
            print(f"Warning: Could not initialize template {SCAN_CONFIG_FILE}. {e}")

    if not os.path.exists(SAVE_CONFIG_FILE):
        try:
            with open(SAVE_CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(os.path.expanduser("~"))
            print(f"  [Init] Generated baseline save path configuration at: {SAVE_CONFIG_FILE}")
        except Exception as e:
            print(f"Warning: Could not initialize template {SAVE_CONFIG_FILE}. {e}")

def add_allowed_value(filename, new_value):
    """
    Appends a newly verified metadata value to a local text database log.

    Args:
        filename (str): The target text database file.
        new_value (str): The text token to add.

    Returns:
        bool: True if the file update succeeded, False if rejected or failed.
    """
    if not new_value or not new_value.strip():
        return False
        
    try:
        content = ""
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read().rstrip()
        
        with open(filename, 'w', encoding='utf-8') as f:
            if content:
                f.write(content + "\n" + new_value.strip() + "\n")
            else:
                f.write(new_value.strip() + "\n")
        return True
    except Exception as e:
        print(f"  [Error] Could not update {filename}. {e}")
        return False

def save_photographer_database(filename, profiles, default_id):
    """
    Overwrites the photographer database file, assigning the 'default' tag
    to the specified default_id and clearing it from all others.

    Args:
        filename (str): Path to the photographer tracking file.
        profiles (dict): Dictionary mapping ID strings to Full Name strings.
        default_id (str): The ID that should receive the 'default' marker.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Photographer ID Database\n")
            f.write("# Format: ID<tab>Full Name<tab>Role\n")
            f.write("# Note: Use 'default' in column 3 to set the GUI default selection.\n")
            
            for pid, name in sorted(profiles.items()):
                role = "default" if pid == default_id else ""
                f.write(f"{pid}\t{name}\t{role}\n")
    except Exception as e:
        print(f"Warning: Could not update photographer database default state. {e}")

def write_tsv_report(save_dir, file_base, headers, rows):
    """
    Writes a tab-separated values (TSV) file ledger recording processing metrics.
    Automatically appends the standard '_ledger.tsv' suffix.
    """
    output_path = os.path.join(save_dir, f"{file_base}_ledger.tsv")
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\t'.join(headers) + '\n')
            for row in rows:
                clean_row = [str(item) if item is not None else "" for item in row]
                f.write('\t'.join(clean_row) + '\n')
        print(f"  [Success] TSV ledger successfully generated at: {output_path}")
    except Exception as e:
        print(f"  [Error] Failed to write TSV ledger to {output_path}. Reason: {e}", file=sys.stderr)

def write_execution_log(save_dir, file_base, metadata, summary_lines, photog_data=None):
    """
    Generates a structured sidecar log file tracking execution state and results.
    Automatically appends the standard '_exec.log' suffix.
    """
    log_path = os.path.join(save_dir, f"{file_base}_exec.log")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        with open(log_path, 'w', encoding='utf-8') as f:
            # 1. Pipeline Execution Metadata Block
            f.write("=== PIPELINE EXECUTION METADATA ===\n")
            for key, val in metadata.items():
                f.write(f"{key.upper()}: {val}\n")
            
            # 2. Photographer Info Block (Cases 1-4)
            if photog_data and photog_data.get("photog_display"):
                f.write("\n=== PHOTOGRAPHER INFO ===\n")
                display = photog_data["photog_display"]
                is_new = photog_data.get("photog_is_new", False)
                is_default = photog_data.get("photog_is_default", False)
                
                if is_new:
                    f.write(f"Photographer added: {display}\n")
                else:
                    f.write(f"Photographer selected: {display}\n")
                
                if is_default:
                    f.write("Selected as new default\n")
                else:
                    f.write("Existing default unchanged\n")

            # 3. Run Summary Block
            f.write("\n=== RUN SUMMARY ===\n")
            for line in summary_lines:
                f.write(f"{line}\n")
        print(f"  [Success] Sidecar execution log successfully generated at: {log_path}")
    except Exception as e:
        print(f"  [Error] Failed to write sidecar log to {log_path}. Reason: {e}", file=sys.stderr)

# --- DATE PARSING UTILITIES ---

def parse_date_string(date_text):
    """
    Converts a long textual date string into an standardized numeric format.

    Example: Converts 'October 02, 2005' to '2005_10_02'.

    Args:
        date_text (str): The raw text date metadata.

    Returns:
        str: The formatted 'YYYY_MM_DD' expression, or None if parsing fails.
    """
    clean_text = re.sub(r'\s+', ' ', date_text).strip()
    try:
        dt_object = datetime.strptime(clean_text, "%B %d, %Y")
        return dt_object.strftime("%Y_%m_%d")
    except ValueError:
        return None

def is_valid_date_format(date_str):
    """
    Validates if a target string conforms to core pipeline naming schema rules.

    Checks for strict adherence to either 'YYYY_MM_DD' or 'YYYY_MM_DD_X' patterns.

    Args:
        date_str (str): The parsed directory date token to evaluate.

    Returns:
        bool: True if structural syntax validation checks pass, False otherwise.
    """
    pattern = r"^\d{4}_\d{2}_\d{2}(?:_[a-zA-Z])?$"
    return bool(re.match(pattern, date_str))

# --- UNIFIED CENTRAL INTERFACE BUILDER ---

def prompt_report_configuration(start_scan_dir, start_save_dir, show_photographer=False):
    """
    Displays a configuration GUI window to customize directory tracking states 
    and systematically assemble naming parameters for reports.
    
    Args:
        start_scan_dir (str): Initial scan folder path context to seed into fields.
        start_save_dir (str): Initial report save location path context to seed.
        show_photographer (bool): Toggles inclusion of Section 3 (Photographer IDs).
        
    Returns:
        dict: Gathered pipeline configuration mappings, or None if cancelled.
    """
    caller_file = os.path.basename(sys.argv[0])
    script_token = caller_file.replace("photo_dir_", "").replace(".py", "")
    
    friendly_name = script_token.capitalize()
    window_title = f"Directory {friendly_name} Configuration Options"

    # Capture the raw profiles map along with the layout list options
    photog_options, default_photog, loaded_profiles = load_photographer_details(PHOTOG_FILE)

    root = tk.Tk()
    root.title(window_title)

    result_data = None

    def draw_separator(parent):
        f = tk.Frame(parent, height=2, bg="#9600FF") 
        f.pack(fill="x", padx=15, pady=10)

    # Title Banner Frame
    header_frame = tk.Frame(root)
    header_frame.pack(fill="x", padx=15, pady=(15, 5))
    lbl_title = tk.Label(header_frame, text=window_title, font=("Arial", 14, "bold"), fg="#9600FF")
    lbl_title.pack(side="left")
    draw_separator(root)

    # Path Input Layout
    grid_container = tk.Frame(root)
    grid_container.pack(fill="x", padx=20, pady=5)
    grid_container.columnconfigure(1, weight=1)

    row_idx = 0

    lbl_scan = tk.Label(grid_container, text="SELECT Scan Directory:", font=("Arial", 12, "bold"), fg="#9600FF")
    lbl_scan.grid(row=row_idx, column=0, sticky="w", pady=6, padx=(0, 10))
    
    ent_scan = tk.Entry(grid_container, font=("Arial", 12))
    ent_scan.insert(0, start_scan_dir)
    ent_scan.grid(row=row_idx, column=1, sticky="ew", pady=6, padx=5)
    
    def browse_scan():
        chosen = filedialog.askdirectory(initialdir=ent_scan.get())
        if chosen:
            ent_scan.delete(0, tk.END)
            ent_scan.insert(0, chosen)
            
    btn_scan = tk.Button(grid_container, text="Browse...", command=browse_scan)
    btn_scan.grid(row=row_idx, column=2, sticky="e", pady=6)
    row_idx += 1

    # Photographer Configuration Row Elements
    var_photog = tk.StringVar(value=default_photog)
    var_make_default = tk.BooleanVar(value=False)
    ent_override = None
    
    if show_photographer:
        draw_separator(root)
        
        # Row 1: Selection Dropdown and Text Entry fields
        photog_frame = tk.Frame(root)
        photog_frame.pack(fill="x", padx=20, pady=5)
        
        lbl_p = tk.Label(photog_frame, text="CHOOSE Photographer ID:", font=("Arial", 12, "bold"), fg="#9600FF")
        lbl_p.pack(side="left", padx=(0, 10))

        # Establish base widget theme maps using the Clam engine framework
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Purple.TCombobox",
            arrowsize=18,
            arrowcolor="#9600FF",
            foreground="black",
            background="white",
            fieldbackground="white"
        )
        
        style.map(
            "Purple.TCombobox",
            selectbackground=[("!disabled", "white")],
            selectforeground=[("!disabled", "black")],
            foreground=[("!disabled", "black")],
            fieldbackground=[("!disabled", "white")]
        )
        
        # Configure matching visual options for the underlying drop-down Listbox pop-up
        root.option_add("*TCombobox*Listbox.background", "#D4ABED")
        root.option_add("*TCombobox*Listbox.foreground", "black")
        root.option_add("*TCombobox*Listbox.selectBackground", "#9600FF")
        root.option_add("*TCombobox*Listbox.selectForeground", "white")
        root.option_add("*TCombobox*Listbox.font", ("Arial", 12, "bold"))
        
        opt_p = ttk.Combobox(
            photog_frame, 
            textvariable=var_photog, 
            values=photog_options, 
            state="readonly",
            font=("Arial", 12),
            style="Purple.TCombobox",
            width=32
        )
        opt_p.pack(side="left", padx=(0, 15))

        # Dynamic state highlighter: Shifts widget color maps ONLY after an active selection is made
        def apply_selection_highlight(event):
            style.configure(
                "Purple.TCombobox",
                foreground="white",
                background="white",
                fieldbackground="#9600FF"
            )
            style.map(
                "Purple.TCombobox",
                selectbackground=[("!disabled", "#9600FF")],
                selectforeground=[("!disabled", "white")],
                foreground=[("!disabled", "white")],
                fieldbackground=[("!disabled", "#9600FF")]
            )
            opt_p.config(font=("Arial", 12, "bold"))
            update_default_checkbox_state()

        opt_p.bind("<<ComboboxSelected>>", apply_selection_highlight)
        
        lbl_ov = tk.Label(photog_frame, text="OR:   Enter New as: ID (First Last):", font=("Arial", 12, "bold"), fg="#9600FF")
        lbl_ov.pack(side="left", padx=(0, 5))
        
        ent_override = tk.Entry(photog_frame, font=("Arial", 12), width=30)
        ent_override.pack(side="left", fill="x", expand=True)

        # Row 2: Default Toggle Option Checkbox Row
        default_toggle_frame = tk.Frame(root)
        default_toggle_frame.pack(fill="x", padx=20, pady=(5, 5))
        
        chk_default = tk.Checkbutton(
            default_toggle_frame, 
            text="Make this photographer default?", 
            variable=var_make_default,
            font=("Arial", 12, "bold"),
            fg="#9600FF",
            activeforeground="#9600FF"
        )
        chk_default.pack(side="left")

        # Dynamic disabling rule for the "Make default" checkbox (Case 1)
        def update_default_checkbox_state(*args):
            override_val = ent_override.get().strip() if ent_override else ""
            dropdown_val = var_photog.get()
            if not override_val and dropdown_val == default_photog:
                chk_default.config(state="disabled")
                var_make_default.set(False)
            else:
                chk_default.config(state="normal")

        # Trace modifications to the inputs to evaluate checkbox availability instantly
        var_photog.trace_add("write", update_default_checkbox_state)
        if ent_override:
            ent_override.bind("<KeyRelease>", update_default_checkbox_state)
        
        # Seed initial state
        update_default_checkbox_state()

    draw_separator(root)

    # Core Metadata Reporting Parameters Frame
    report_container = tk.Frame(root)
    report_container.pack(fill="x", padx=20, pady=5)
    report_container.columnconfigure(1, weight=1)
    rep_row = 0

    lbl_save = tk.Label(report_container, text="SELECT Report Save Location:", font=("Arial", 12, "bold"), fg="#9600FF")
    lbl_save.grid(row=rep_row, column=0, sticky="w", pady=6, padx=(0, 10))
    
    ent_save = tk.Entry(report_container, font=("Arial", 12))
    ent_save.insert(0, start_save_dir)
    ent_save.grid(row=rep_row, column=1, sticky="ew", pady=6, padx=5)
    
    def browse_save():
        chosen = filedialog.askdirectory(initialdir=ent_save.get())
        if chosen:
            ent_save.delete(0, tk.END)
            ent_save.insert(0, chosen)
            
    btn_save = tk.Button(report_container, text="Browse...", command=browse_save)
    btn_save.grid(row=rep_row, column=2, sticky="e", pady=6)
    rep_row += 1

    lbl_host = tk.Label(report_container, text="Host Machine:", font=("Arial", 12, "bold"), fg="#9600FF")
    lbl_host.grid(row=rep_row, column=0, sticky="w", pady=6)
    ent_host = tk.Entry(report_container, font=("Arial", 12))
    ent_host.grid(row=rep_row, column=1, columnspan=2, sticky="ew", pady=6, padx=5)
    rep_row += 1

    lbl_repo = tk.Label(report_container, text="Repository Name:", font=("Arial", 12, "bold"), fg="#9600FF")
    lbl_repo.grid(row=rep_row, column=0, sticky="w", pady=6)
    ent_repo = tk.Entry(report_container, font=("Arial", 12))
    ent_repo.grid(row=rep_row, column=1, columnspan=2, sticky="ew", pady=6, padx=5)
    rep_row += 1

    lbl_comp = tk.Label(report_container, text="Report Directory Component:", font=("Arial", 12, "bold"), fg="#9600FF")
    lbl_comp.grid(row=rep_row, column=0, sticky="w", pady=6)
    ent_comp = tk.Entry(report_container, font=("Arial", 12))
    ent_comp.insert(0, "all")
    ent_comp.grid(row=rep_row, column=1, columnspan=2, sticky="ew", pady=6, padx=5)
    rep_row += 1

    lbl_script = tk.Label(report_container, text="Script Name:", font=("Arial", 12, "bold"), fg="#9600FF")
    lbl_script.grid(row=rep_row, column=0, sticky="w", pady=6)
    ent_script = tk.Entry(report_container, font=("Arial", 12))
    ent_script.insert(0, script_token)
    ent_script.grid(row=rep_row, column=1, columnspan=2, sticky="ew", pady=6, padx=5)
    rep_row += 1

    lbl_date = tk.Label(report_container, text="Report Date (yyyy-mm-dd):", font=("Arial", 12, "bold"), fg="#9600FF")
    lbl_date.grid(row=rep_row, column=0, sticky="w", pady=6)
    ent_date = tk.Entry(report_container, font=("Arial", 12))
    ent_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
    ent_date.grid(row=rep_row, column=1, columnspan=2, sticky="ew", pady=6, padx=5)

    lbl_error = tk.Label(root, text="", font=("Arial", 12, "bold"), fg="red")
    lbl_error.pack(side="bottom", pady=(0, 5))

    def handle_submit():
        nonlocal result_data
        
        lbl_host.config(fg="#9600FF")
        lbl_repo.config(fg="#9600FF")
        lbl_error.config(text="")

        val_host = ent_host.get().strip()
        val_repo = ent_repo.get().strip()
        val_comp = ent_comp.get().strip()
        val_script = ent_script.get().strip()
        val_date = ent_date.get().strip()

        has_errors = False
        if not val_host:
            lbl_host.config(fg="red")
            has_errors = True
        if not val_repo:
            lbl_repo.config(fg="red")
            has_errors = True
            
        if has_errors:
            lbl_error.config(text="Error: 'Host Machine' and 'Repository Name' are mandatory fields.")
            return

        final_photog = ""
        photog_display = ""
        photog_is_new = False
        photog_is_default = False

        if show_photographer:
            raw_override = ent_override.get().strip() if ent_override else ""
            
            if raw_override:
                # Cases 3 and 4: New photographer text box entry
                photog_is_new = True
                match = re.match(r"^([^\s(]+)\s*\(([^)]+)\)", raw_override)
                if match:
                    new_id = match.group(1).strip()
                    new_name = match.group(2).strip()
                    final_photog = new_id
                    photog_display = f"{new_id} ({new_name})"
                    
                    if var_make_default.get():
                        photog_is_default = True
                        loaded_profiles[new_id] = new_name
                        save_photographer_database(PHOTOG_FILE, loaded_profiles, new_id)
                    else:
                        photog_is_default = False
                        add_allowed_value(PHOTOG_FILE, f"{new_id}\t{new_name}\t")
                        print(f"  [Database Update] Appended '{new_id}' ({new_name}) to {PHOTOG_FILE}")
                else:
                    final_photog = raw_override.split()[0]
                    photog_display = f"{final_photog} (Unknown)"
                    photog_is_default = var_make_default.get()
            else:
                # Cases 1 and 2: Maintained or modified dropdown entry
                raw_selection = var_photog.get()
                photog_is_new = False
                
                if raw_selection:
                    final_photog = raw_selection.split()[0]
                    photog_display = raw_selection
                    
                    # If selection is changed from default and user wants to make it the new default
                    if raw_selection != default_photog and var_make_default.get():
                        photog_is_default = True
                        save_photographer_database(PHOTOG_FILE, loaded_profiles, final_photog)
                    else:
                        photog_is_default = False
                else:
                    final_photog = "unk"
                    photog_display = f"{DEFAULT_PHOTOG_ID} ({DEFAULT_PHOTOG_NAME})"
                    photog_is_default = False

        constructed_base = f"{val_host}_{val_repo}_{val_comp}_{val_script}_{val_date}"

        result_data = {
            "scan_dir": ent_scan.get().strip(),
            "save_dir": ent_save.get().strip(),
            "photographer": final_photog,
            "machine": val_host,
            "file_base": constructed_base,
            "photog_display": photog_display,
            "photog_is_new": photog_is_new,
            "photog_is_default": photog_is_default
        }
                
        save_start_dir(SCAN_CONFIG_FILE, result_data["scan_dir"])
        save_start_dir(SAVE_CONFIG_FILE, result_data["save_dir"])
        root.destroy()

    def handle_cancel():
        root.destroy()

    # Footer Action Frame
    footer_frame = tk.Frame(root)
    footer_frame.pack(fill="x", side="bottom", pady=15)
    
    btn_submit = tk.Button(footer_frame, text="Generate Logs", width=16, command=handle_submit)
    btn_submit.pack(side="left", expand=True)
    
    btn_cancel = tk.Button(footer_frame, text="Cancel", width=16, command=handle_cancel)
    btn_cancel.pack(side="right", expand=True)

    root.update_idletasks()
    win_width = 950
    win_height = 575
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    pos_x = (screen_width // 2) - (win_width // 2)
    pos_y = (screen_height // 2) - (win_height // 2)
    
    root.geometry(f"{win_width}x{win_height}+{pos_x}+{pos_y}")

    root.mainloop()
    return result_data

initialize_template_files()
