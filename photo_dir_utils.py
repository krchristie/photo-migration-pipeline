"""
Photo Directory Subsystem Utilities
----------------------------------
Provides shared configuration, file string normalization, directory persistence, 
and date validation utilities utilized across the photo migration pipeline.

================================================================================
"""

import os
import re
from datetime import datetime

# --- CONFIGURATION CONSTANTS ---
# Hidden flat file tracking the path of the last directory accessed
CONFIG_FILE = os.path.expanduser("~/.renamer_config")

# Text files for persistent storage of known photographers & places
PHOTOG_FILE = "photographerIDs.txt"
PLACES_FILE = "photoPlaces.txt"

# Graphical User Interface layout color theme definitions
TEXT_COLOR = "royalblue"   
ERROR_COLOR = "red"        

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

def get_start_dir():
    """
    Reads the configuration file to retrieve the most recently accessed 
    directory path.

    Returns:
        str: The absolute path to the most recently accessed folder if valid,
             otherwise the user's home directory.
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                last_path = f.read().strip()
                if os.path.isdir(last_path):
                    return last_path
        except Exception:
            pass
    return os.path.expanduser("~")

def save_start_dir(path):
    """
    Saves the current working directory path to the configuration file.

    Maintains pipeline continuity across successive scripts by logging 
    the active location.

    Args:
        path (str): The directory path to write to disk.
    """
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write(path)
    except Exception as e:
        print(f"Warning: Could not save last used directory. {e}")

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
                    parts = line.strip().split('\t')
                    if parts and parts[0]:
                        allowed.add(parts[0])
        except Exception as e:
            print(f"Warning: Could not read {filename}. {e}")
    return allowed

def add_allowed_value(filename, new_value):
    """
    Appends a newly verified metadata value to a local text database log.

    Args:
        filename (str): The target text database file.
        new_value (str): The text token to add.

    Returns:
        bool: True if the file update succeeded, False if rejected or failed.
    """
    # Safeguard: Strictly reject empty entries or whitespace-only records
    if not new_value or not new_value.strip():
        return False
        
    try:
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(f"\n{new_value}")
        return True
    except Exception as e:
        print(f"  [Error] Could not update {filename}. {e}")
        return False

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
    # Clean non-breaking characters and collapse irregular spaces
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
