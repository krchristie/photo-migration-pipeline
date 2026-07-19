"""
Photo Directory Migration Verifier
==================================

This script performs a strict 1:1 integrity check between two photo directory 
reports to verify a successful file migration between systems or drives.

1. Source File (Primary): The report from the original machine/location.
2. Target File (Repository): The report from the new machine/location.

Matching Logic:
---------------
A file is flagged as 'verified' ONLY if it matches exactly on:
  - Exact Filename (no normalization or suffix stripping)
  - File Size (KB)
  - Relative Directory Path (relative to the root project folder anchor)
"""

import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import photo_dir_utils as utils

def get_relative_path(absolute_path, anchor='photoDirectory'):
    """
    Extracts the relative path structure trailing the specified anchor folder name.
    Ensures path verification works across different machines with different roots.
    """
    if not absolute_path:
        return ""
    # Partition returns (before, anchor, after). We want the anchor + after.
    parts = absolute_path.partition(anchor)
    if parts[1]:  # Anchor found
        return parts[1] + parts[2]
    return absolute_path  # Fallback to absolute if anchor not found

def load_target_manifest(target_report_path):
    """
    Reads the new/target location report and builds a fast lookup map based on 
    exact names, sizes, and relative directory paths.
    """
    target_map = {}
    print(f"Loading Target Manifest: {os.path.basename(target_report_path)}...")
    
    try:
        with open(target_report_path, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            reader.fieldnames = [h.strip() for h in reader.fieldnames]
            
            for row in reader:
                fname = row.get('Filename', '').strip()
                fsize = row.get('Size (KB)', '0').strip()
                abs_path = row.get('Directory path', '').strip()
                
                # Extract relative path to ignore absolute root drive differences
                rel_path = get_relative_path(abs_path)
                
                # Composite key: (Exact Name, Size, Relative Path)
                key = (fname, fsize, rel_path)
                
                target_map[key] = abs_path
                
        print(f"Target manifest loaded. {len(target_map)} structural signatures recorded.")
        return target_map

    except Exception as e:
        messagebox.showerror("Error", f"Failed to read target manifest:\n{e}")
        return None

def run_migration_check():
    """
    Main loop to cross-examine the original directory state against the new drive.
    """
    root = tk.Tk()
    root.withdraw()

    start_dir = utils.get_start_dir()

    # 1. Select Original Source Report
    print("Select the ORIGINAL (Source) report TSV...")
    source_path = filedialog.askopenfilename(
        title="Select ORIGINAL (Source) Report File",
        initialdir=start_dir,
        filetypes=[("TSV Files", "*.tsv")]
    )
    if not source_path:
        return

    # 2. Select New Target Report
    print("Select the NEW (Target Destination) report TSV...")
    target_path = filedialog.askopenfilename(
        title="Select NEW (Target Destination) Report File",
        initialdir=os.path.dirname(source_path),
        filetypes=[("TSV Files", "*.tsv")]
    )
    if not target_path:
        return

    utils.save_start_dir(os.path.dirname(source_path))

    # Load target baseline data
    target_map = load_target_manifest(target_path)
    if not target_map:
        return

    # Output setup
    base_dir = os.path.dirname(source_path)
    input_filename = os.path.basename(source_path)
    output_filename = input_filename.replace(".tsv", "_migration_verification.tsv")
    output_path = os.path.join(base_dir, output_filename)

    print(f"Running verification loop. Writing to: {output_filename}")
    
    try:
        with open(source_path, mode='r', newline='', encoding='utf-8') as f_in, \
             open(output_path, mode='w', newline='', encoding='utf-8') as f_out:
            
            reader = csv.DictReader(f_in, delimiter='\t')
            reader.fieldnames = [h.strip() for h in reader.fieldnames]

            fieldnames = ['filename', 'source absolute path', 'relative path', 'size (kb)', 'status']
            writer = csv.DictWriter(f_out, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()

            total_checked = 0
            verified_count = 0

            for row in reader:
                src_fname = row.get('Filename', '').strip()
                src_abs_path = row.get('Directory path', '').strip()
                src_size = row.get('Size (KB)', '0').strip()
                
                src_rel_path = get_relative_path(src_abs_path)
                
                # Check target map using the exact signature
                lookup_key = (src_fname, src_size, src_rel_path)
                
                if lookup_key in target_map:
                    status = 'verified'
                    verified_count += 1
                else:
                    status = 'missing_or_mismatched'

                writer.writerow({
                    'filename': src_fname,
                    'source absolute path': src_abs_path,
                    'relative path': src_rel_path,
                    'size (kb)': src_size,
                    'status': status
                })
                total_checked += 1

        summary = (f"Migration Audit Complete.\n\n"
                   f"Total Files Checked: {total_checked}\n"
                   f"Successfully Verified: {verified_count}\n"
                   f"Failed/Missing: {total_checked - verified_count}\n\n"
                   f"Results log generated:\n{output_filename}")
        
        print(summary)
        messagebox.showinfo("Verification Finished", summary)

    except Exception as e:
        print(f"Execution Error: {e}")
        messagebox.showerror("Execution Error", str(e))

if __name__ == "__main__":
    run_migration_check()