"""
Directory Scanner & TSV Reporter
================================

This script performs a high-performance recursive scan of a specified directory
and exports metadata (path, type, name, date, size) to a TSV file. 

Designed to be run locally to scan both internal local drives and mounted 
external/network volumes containing large media libraries (>30,000 files).

Key Optimizations:
1. Iterative Traversal: Uses a stack instead of recursion to prevent 
   stack overflow errors on deeply nested directories.
2. Buffered I/O: Writes to disk in chunks to minimize disk access overhead.
3. Batch Processing: Accumulates rows in memory before passing them to the CSV writer.
4. os.scandir: Uses Python's optimized iterator which retrieves file attributes 
   without requiring separate system calls for every file.
5. Customized Shared GUI Selection: Uses a Tkinter dialog box 
   initialized to a persistent directory state shared across the 
   script suite. This maintains workflow continuity and streamlines 
   directory selection within nested directory structures on mounted 
   external volumes.

Author:        Karen R. Christie
Original Date: December 2025
Refactored:    January 2026 (GUI Integration)
Doc Updated:   June 2026 (Architectural Context)
"""

import os
import datetime
import csv
import stat
import tkinter as tk
from tkinter import filedialog

# Import the provided utilities for directory configuration
import photo_dir_utils as utils

def scan_to_tsv_optimized(search_path: str, base_name: str):
    """
    Scans a directory tree and writes file details to a TSV file.

    Side Effects:
        Writes tab-separated rows directly to a file named 
        "{base_name}-file_report.tsv" in the current working directory.

    Args:
        search_path: The absolute path to the directory to scan.
        base_name: A substring used to determine the starting point 
                   for the 'Directory path' column in the output.
    """
    
    output_filename = f"{base_name}-file_report.tsv"

    # Validation: Ensure the target directory exists before starting
    if not os.path.exists(search_path):
        print(f"Error: The directory '{search_path}' does not exist.")
        return

    print(f"Scanning '{search_path}'...")
    print(f"Writing results to: '{output_filename}'")

    included_count = 0
    excluded_count = 0
    
    # Batch size for memory buffering; balances RAM usage against disk I/O overhead.
    BATCH_SIZE = 2000 
    batch_rows = []

    try:
        # I/O OPTIMIZATION:
        # buffering=262144 sets a 256KB buffer manually to override the system default.
        # This minimizes disk access overhead when writing large streams over network layers.
        with open(output_filename, mode='w', newline='', encoding='utf-8', buffering=262144) as tsv_file:
            writer = csv.writer(tsv_file, delimiter='\t')
            
            # Write Header Row
            writer.writerow(['Directory path', 'File type', 'Filename', 'Date (mm/dd/yyyy)', 'Size (KB)'])

            # Use an explicit LIFO stack to execute an iterative depth-first traversal.
            # This bounds memory usage linearly and bypasses Python's recursion depth limits.
            # Tuple Format: (full_system_path, relative_display_path)
            stack = [(search_path, search_path[search_path.find(base_name):] if base_name in search_path else search_path)]

            while stack:
                current_path, display_path = stack.pop()

                try:
                    # os.scandir() yields an iterator of DirEntry objects containing 
                    # cached file attributes, preventing repetitive disk lookups.
                    with os.scandir(current_path) as it:
                        for entry in it:
                            
                            # Fast Name Check: Skip system/hidden dot-files immediately
                            if entry.name.startswith('.'):
                                excluded_count += 1
                                continue

                            try:
                                # Cache the stat object to avoid hitting the disk 
                                # multiple times for date, size, and attributes.
                                entry_stat = entry.stat()
                            except OSError:
                                # File might be locked or vanished during scan
                                continue

                            # Platform Check: Apply bitwise mask for hidden files on Windows
                            if os.name == 'nt':
                                if entry_stat.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN:
                                    excluded_count += 1
                                    continue

                            # --- Process Files ---
                            if entry.is_file():
                                try:
                                    _, ext = os.path.splitext(entry.name)
                                    file_type = ext.lstrip('.').lower()

                                    mod_time = datetime.datetime.fromtimestamp(entry_stat.st_mtime)
                                    formatted_date = mod_time.strftime('%m/%d/%Y')

                                    file_size_kb = round(entry_stat.st_size / 1024, 2)

                                    batch_rows.append([
                                        display_path,
                                        file_type,
                                        entry.name,
                                        formatted_date,
                                        file_size_kb
                                    ])
                                    
                                    included_count += 1

                                    # Flush accumulated rows to disk to maintain the memory ceiling.
                                    if len(batch_rows) >= BATCH_SIZE:
                                        writer.writerows(batch_rows)
                                        batch_rows = []

                                except Exception:
                                    pass # Skip individual file errors for speed and continuity

                            # --- Process Directories ---
                            elif entry.is_dir():
                                sub_display = os.path.join(display_path, entry.name)
                                stack.append((entry.path, sub_display))

                except PermissionError:
                    # Skip folders without read permissions
                    continue
            
            # Write any remaining rows that did not fill the final batch
            if batch_rows:
                writer.writerows(batch_rows)

    except IOError as e:
        print(f"Error writing to file: {e}")
        return

    print("-" * 50)
    print(f"Scan Complete.")
    print(f"Files listed:    {included_count}")
    print(f"Hidden/Excluded: {excluded_count}")
    print(f"Report saved to '{output_filename}'")
    print("-" * 50)

if __name__ == "__main__":
    # --- GUI & UTILS INTEGRATION ---
    
    # Initialize Tkinter and hide the main root window
    root = tk.Tk()
    root.withdraw()

    # Get the last used directory from the shared suite configuration utility
    start_dir = utils.get_start_dir()
    print(f"Opening selection window (starting at: {start_dir})...")

    selected_path = filedialog.askdirectory(
        initialdir=start_dir,
        title="Select Directory to Create Report"
    )

    if selected_path:
        selected_path = os.path.normpath(selected_path)

        # Persist this selection for future script executions within the suite
        utils.save_start_dir(selected_path)

        # Derive base substring name from the target path root
        base_name = os.path.basename(selected_path)

        scan_to_tsv_optimized(selected_path, base_name)
    else:
        print("Operation cancelled. No directory selected.")
