"""
Directory Scanner & TSV Reporter
================================

DOES NOT RUN IN VERSION 2.0

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

Author:         Karen R. Christie
Original Date:  December 2025
Refactored:     January 2026 (GUI Integration)
Doc Updated:    June 2026 (Architectural Context)
Refactored GUI: June 2026 (Tkinter Dialogs & Persistent States)
================================================================================
"""

import datetime
import os
import stat
import sys
import tkinter as tk

import photo_dir_utils as utils


def scan_to_tsv_optimized(
    search_path: str,
    base_name: str,
    output_target_path: str
) -> None:
    """Scans a target directory tree and logs file metadata records to a TSV.

    Args:
        search_path: The absolute path to the directory being analyzed.
        base_name: The base directory substring used to establish the relative
            root anchor in the output 'Directory path' tracking column.
        output_target_path: The finalized destination file path where the
            report spreadsheet will be generated.
    """
    if not os.path.exists(search_path):
        print(f"Error: The target scan directory '{search_path}' "
              f"does not exist.", file=sys.stderr)
        return

    print(f"Initiating volume traversal on: '{search_path}'")
    print(f"Target destination report path: '{output_target_path}'")

    included_count = 0
    excluded_count = 0

    # Define column schema headers for the consolidated utility writer
    headers = ['Directory path', 'File type', 'Filename', 'Date (mm/dd/yy)',
               'Size (KB)']

    batch_rows = []
    is_first_write = True

    # Establish localized stack-based iterative tree traversal array
    stack = [(search_path, base_name)]

    while stack:
        current_dir, display_path = stack.pop()

        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    if entry.name.startswith('.'):
                        excluded_count += 1
                        continue

                    if entry.is_file():
                        try:
                            f_stat = entry.stat()
                            f_size = max(1, int(f_stat.st_size / 1024))
                            m_time = f_stat.st_mtime
                            f_date = (datetime.datetime.fromtimestamp(m_time)
                                      .strftime('%m/%d/%y'))
                        except OSError:
                            excluded_count += 1
                            continue

                        _, ext = os.path.splitext(entry.name)
                        f_type = ext.upper().lstrip('.') if ext else 'UNKNOWN'

                        batch_rows.append([
                            display_path,
                            f_type,
                            entry.name,
                            f_date,
                            str(f_size)
                        ])
                        included_count += 1

                        # Periodic disk flush every 2000 items
                        if len(batch_rows) >= 2000:
                            current_headers = headers if is_first_write else []
                            utils.write_tsv_report(output_target_path,
                                                   current_headers, batch_rows)
                            is_first_write = False
                            batch_rows.clear()

                    elif entry.is_dir():
                        sub_display = os.path.join(display_path, entry.name)
                        stack.append((entry.path, sub_display))

        except PermissionError:
            continue

    # Flush any remaining unwritten records after exiting the traversal stack
    if batch_rows:
        current_headers = headers if is_first_write else []
        utils.write_tsv_report(output_target_path, current_headers, batch_rows)

    print("-" * 50)
    print("Scan Execution Successfully Completed.")
    print(f"Total files cataloged: {included_count}")
    print(f"Total entries skipped: {excluded_count}")
    print(f"Metadata index saved to: '{output_target_path}'")
    print("-" * 50)


def prompt_reporter_configuration() -> dict | None:
    """Assembles a local window utilizing modular widget building blocks."""
    app_title = "Directory Reporter Configuration Options"
    
    dialog = tk.Toplevel()
    dialog.title(app_title)
    dialog.geometry("975x445")
    
    top_hdr = tk.Label(
        dialog, text=app_title, fg=utils.TEXT_COLOR,
        font=("Arial", 14, "bold")
    )
    top_hdr.pack(anchor="w", padx=20, pady=(15, 5))
    # Add a purple divider line under the app_title
    title_divider = tk.Frame(dialog, height=2, bg=utils.TEXT_COLOR)
    title_divider.pack(fill="x", padx=15, pady=(0, 10))
    
    # 1. Source Scan Section
    scan_picker = utils.SourceDirectoryPicker(dialog)
    scan_picker.pack(fill="x", padx=15, pady=5)
    
    # 2. Report Options Section (Now holds all 5 explicit rows cleanly)
    save_picker = utils.ReportSavePicker(dialog, mode_tag="reporter")
    save_picker.pack(fill="x", padx=15, pady=5)
    
    result = {}
    
    def on_submit():
        scan_picker.persist_state()
        save_picker.persist_state()
        
        result.update({
            "scan_dir": scan_picker.selected_path.get(),
            "save_dir": save_picker.save_dir.get(),
            "filename": save_picker.var_final_filename.get()
        })
        dialog.destroy()
        
    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=5)
    
    tk.Button(btn_frame, text="Generate Report", command=on_submit,
              width=15).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Cancel", command=dialog.destroy,
              width=10).pack(side="left", padx=10)
    
    # Center window dynamically
    dialog.update_idletasks()
    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    cx = int((sw / 2) - (975 / 2))
    cy = int((sh / 2) - (455 / 2))
    dialog.geometry(f"975x455+{cx}+{cy}")

    dialog.grab_set()
    dialog.wait_window()
    return result if result else None


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    print("Launching Report Metadata Configuration Suite...")
    config = prompt_reporter_configuration()

    if config:
        final_scan_path = config['scan_dir']
        full_output_target_path = os.path.join(config['save_dir'],
                                               config['filename'])
        base_name = os.path.basename(final_scan_path)

        scan_to_tsv_optimized(final_scan_path, base_name,
                              full_output_target_path)
    else:
        print("Operation halted. Configuration parameters cancelled.")