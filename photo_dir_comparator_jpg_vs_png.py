"""
Photo Directory JPG-vs-PNG Comparator - iPhotos vs Apple Photos
==================================================================

This script compares two tab-separated values (TSV) report spreadsheets:
1. Primary File: The list of files exported from one ecosystem, generally Photos.
2. Repository File: The master archival list from the other, generally iPhotos.

It matches files across systems by isolating the filename base (ignoring 
extensions like .jpg vs .png) and verifying that they exist within subdirectories 
sharing the exact same chronological date string prefix (yyyy_mm_dd).

File sizes are ignored due to the standard size increases introduced during 
Apple Photos format migrations.

Special Handling:
-----------------
Files matching the duplicate nomenclature suffix pattern (e.g., "filename (1).ext")
are intercepted and flagged as 'check for edited version'. This isolates items 
where an edited variant may exist inside the source iPhotos library library database.

================================================================================
"""

import csv
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import photo_dir_utils as utils

# Regex pattern to match trailing duplication marks like ' (1)', ' (2)'
EDIT_PATTERN = re.compile(r'\s\(\d+\)$')

def extract_date_prefix(dir_path):
    """
    Extracts the yyyy_mm_dd date prefix from a standardized directory name.

    Args:
        dir_path (str): The full directory path from the report.

    Returns:
        str: The 8-digit date prefix (e.g., '2004_06_15') if found, 
             otherwise an empty string.
    """
    if not dir_path:
        return ""
    
    folder_name = os.path.basename(os.path.normpath(dir_path))
    
    if len(folder_name) >= 10 and folder_name[4] == '_' and folder_name[7] == '_':
        return folder_name[:10]
        
    return ""

def load_jpg_vs_png_repository(repo_path):
    """
    Reads the master repository report and builds a fast lookup table 
    keyed by filename base and calendar date prefix.
    """
    repo_map = {}
    print(f"Loading JPG-vs-PNG Repository: {os.path.basename(repo_path)}...")
    
    try:
        with open(repo_path, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            reader.fieldnames = [h.strip() for h in reader.fieldnames]
            
            for row in reader:
                fname = row.get('Filename', '').strip()
                dir_path = row.get('Directory path', '').strip()
                
                base_name, _ = os.path.splitext(fname)
                norm_base = utils.normalize_filename(base_name)
                
                date_prefix = extract_date_prefix(dir_path)
                if not date_prefix:
                    continue
                
                key = (norm_base, date_prefix)
                if key not in repo_map:
                    repo_map[key] = {
                        'filename': fname,
                        'path': dir_path
                    }
                    
        print(f"Repository loaded. {len(repo_map)} date-based keys mapped.")
        return repo_map

    except Exception as e:
        messagebox.showerror("Error", f"Failed to read repository file:\n{e}")
        return None

def process_jpg_vs_png_comparison():
    """
    Launches interface selection and runs the jpg-vs-png matching pipeline.
    """
    root = tk.Tk()
    root.withdraw()

    start_dir = utils.get_start_dir()

    print("Select the PRIMARY file (JPG-vs-PNG)...")
    primary_path = filedialog.askopenfilename(
        title="Select PRIMARY Input File",
        initialdir=start_dir,
        filetypes=[("TSV Files", "*.tsv")]
    )
    if not primary_path:
        return

    print("Select the REPOSITORY file (JPG-vs-PNG)...")
    repo_path = filedialog.askopenfilename(
        title="Select REPOSITORY File",
        initialdir=os.path.dirname(primary_path),
        filetypes=[("TSV Files", "*.tsv")]
    )
    if not repo_path:
        return

    utils.save_start_dir(os.path.dirname(primary_path))

    repo_map = load_jpg_vs_png_repository(repo_path)
    if not repo_map:
        return

    base_dir = os.path.dirname(primary_path)
    input_filename = os.path.basename(primary_path)
    
    if "_file_report.tsv" in input_filename:
        output_filename = input_filename.replace(
            "_file_report.tsv", "_jpg_vs_png_status_report.tsv"
        )
    else:
        base, ext = os.path.splitext(input_filename)
        output_filename = f"{base}_jpg_vs_png_status_report{ext}"
    
    output_path = os.path.join(base_dir, output_filename)

    print(f"Comparing jpg-vs-png assets and writing to: {output_filename}")
    
    try:
        with open(primary_path, mode='r', newline='', encoding='utf-8') as f_in, \
             open(output_path, mode='w', newline='', encoding='utf-8') as f_out:
            
            reader = csv.DictReader(f_in, delimiter='\t')
            reader.fieldnames = [h.strip() for h in reader.fieldnames]

            fieldnames = [
                'filename', 
                'file path', 
                'status', 
                'dup filename', 
                'dup file path'
            ]
            writer = csv.DictWriter(f_out, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()

            processed_count = 0
            dup_count = 0
            edit_check_count = 0

            for row in reader:
                src_fname = row.get('Filename', '').strip()
                src_path = row.get('Directory path', '').strip()

                src_base, _ = os.path.splitext(src_fname)
                
                # Check for " (1)" patterns before doing normalization
                if EDIT_PATTERN.search(src_base):
                    status = 'check for edited version'
                    dup_fname = ''
                    dup_path = ''
                    edit_check_count += 1
                else:
                    norm_base = utils.normalize_filename(src_base)
                    date_prefix = extract_date_prefix(src_path)
                    key = (norm_base, date_prefix)
                    
                    match = repo_map.get(key) if date_prefix else None
                    if match:
                        status = 'duplicate'
                        dup_fname = match['filename']
                        dup_path = match['path']
                        dup_count += 1
                    else:
                        status = 'unique'
                        dup_fname = ''
                        dup_path = ''

                writer.writerow({
                    'filename': src_fname,
                    'file path': src_path,
                    'status': status,
                    'dup filename': dup_fname,
                    'dup file path': dup_path
                })
                processed_count += 1

        msg = (f"JPG-vs-PNG Report Complete.\n\n"
               f"Total Processed: {processed_count}\n"
               f"Duplicates Found: {dup_count}\n"
               f"Flagged for Edit Review: {edit_check_count}\n"
               f"Unique Files: {processed_count - dup_count - edit_check_count}\n\n"
               f"Saved to:\n{output_filename}")
        
        print(msg)
        messagebox.showinfo("Comparison Complete", msg)

    except Exception as e:
        print(f"Error during jpg-vs-png processing: {e}")
        messagebox.showerror("Processing Error", str(e))

if __name__ == "__main__":
    process_jpg_vs_png_comparison()