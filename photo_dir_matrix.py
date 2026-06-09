"""
Directory Scanner & TSV Reporter
================================

This script performs a recursive scan of a specified directory
and exports metadata (path, type, name, date, size) to a TSV file. 

Designed to be run locally to scan both internal local drives and mounted 
external/network volumes containing large media libraries (>30,000 files).

Key Optimizations & Performance Notes:
1. Iterative Traversal: Uses a stack instead of recursion to prevent 
   stack overflow errors on deeply nested directories.
2. Buffered I/O: Writes to disk in chunks to minimize disk access overhead.
3. Batch Processing: Accumulates rows in memory before passing them to the CSV writer.
4. os.scandir: Uses Python's optimized iterator which retrieves file attributes 
   without requiring separate system calls for every file.
5. Runtime Expectation: When scanning massive libraries (such as Apple Photos or 
   iPhoto packages containing over 15,000 to 30,000 files) stored on mounted 
   external drives or network shares, the initial scan can take a significant 
   amount of time to fully parse. The script has not frozen; it is processing 
   large disk I/O queues.
"""

import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox, StringVar, Radiobutton, Label, Entry, Button
from collections import Counter, defaultdict

def normalize_filename(filename):
    """
    Removes ' copy' from the filename stem to allow matching.
    """
    base, ext = os.path.splitext(filename)
    normalized_base = base.replace(' copy', '')
    return normalized_base + ext

def get_group_name(files_in_group):
    """
    Determines the name to use (shortest filename preferred).
    """
    files_in_group.sort(key=lambda x: (len(x), x))
    return files_in_group[0]

def analyze_directory_sets(all_duplicate_groups):
    """
    Implements Greedy Clustering to determine Directory Sets.
    Returns a map: directory_path -> (Set_Name, Count_in_Set_Name)
    """
    dir_counts = Counter()
    adjacency = defaultdict(set)

    for group in all_duplicate_groups:
        # Update Counts
        for row in group:
            d = row.get('Directory path', '')
            dir_counts[d] += 1

        # Build Adjacency
        dirs_in_group = list(set(row.get('Directory path', '') for row in group))
        for i in range(len(dirs_in_group)):
            for j in range(i + 1, len(dirs_in_group)):
                d1 = dirs_in_group[i]
                d2 = dirs_in_group[j]
                adjacency[d1].add(d2)
                adjacency[d2].add(d1)

    sorted_dirs = [d for d, c in dir_counts.most_common()]

    dir_to_set_info = {}
    visited = set()

    for start_dir in sorted_dirs:
        if start_dir in visited:
            continue
            
        set_name = start_dir
        set_count = dir_counts[start_dir]
        
        stack = [start_dir]
        visited.add(start_dir)
        dir_to_set_info[start_dir] = (set_name, set_count)
        
        while stack:
            current = stack.pop()
            neighbors = adjacency[current]
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    dir_to_set_info[neighbor] = (set_name, set_count)
                    stack.append(neighbor)
                    
    return dir_to_set_info

def get_user_options(input_filename):
    dialog = tk.Toplevel()
    dialog.title("Report Options")
    dialog.geometry("600x480")
    
    # Variables
    mode_var = StringVar(value="full")  # Option 1 is default
    sub_path_var = StringVar()
    file_tag_var = StringVar()
    no_dup_filename_var = StringVar()
    
    result = {"mode": None, "sub_path": None, "file_tag": None, "no_dup_filename": None}

    def on_submit(event=None): # Accepts event so it can be bound to <Return>
        result["mode"] = mode_var.get()
        result["sub_path"] = sub_path_var.get().strip()
        result["file_tag"] = file_tag_var.get().strip()
        result["no_dup_filename"] = no_dup_filename_var.get().strip()
        dialog.destroy()

    def on_cancel():
        dialog.destroy()
        
    # Bind the "Enter" / "Return" key to submit the form
    dialog.bind('<Return>', on_submit)
        
    def update_states():
        selection = mode_var.get()
        
        # Reset all to disabled first
        path_entry.config(state='disabled')
        tag_entry.config(state='disabled')
        no_dup_entry.config(state='disabled')
        
        if selection == "sub":
            path_entry.config(state='normal')
            tag_entry.config(state='normal')
            path_entry.focus_set() # Move cursor to first input
        elif selection == "unique":
            no_dup_entry.config(state='normal')
            no_dup_entry.focus_set() # Move cursor to input

    # --- UI LAYOUT ---
    
    Label(dialog, text="Input File (Selectable):", font=("Arial", 10, "bold")).pack(pady=(15, 0))
    
    # 1. Selected File Display (Using Entry widget so it can be copied)
    # We use 'readonly' state so users can select/copy, but not edit.
    file_display_frame = tk.Frame(dialog)
    file_display_frame.pack(pady=(5, 15), padx=20, fill="x")
    
    file_display = Entry(file_display_frame, font=("Arial", 10))
    file_display.pack(fill="x")
    file_display.insert(0, input_filename)
    file_display.config(state='readonly') # Make read-only
    
    Label(dialog, text="Select Report Type:", font=("Arial", 11, "bold")).pack(pady=(0, 10))
    
    # Option 1: Full Report
    Radiobutton(dialog, text="Option 1: Full Report (All Duplicates)", variable=mode_var, value="full", command=update_states).pack(anchor="w", padx=20)

    # Option 2: Sub-Report
    Radiobutton(dialog, text="Option 2: Sub-Report (Matrix by folder)", variable=mode_var, value="sub", command=update_states).pack(anchor="w", padx=20, pady=(10, 0))
    
    frame_sub = tk.LabelFrame(dialog, text="  Option 2 Settings  ", padx=10, pady=10)
    frame_sub.pack(fill="x", padx=40, pady=5)

    Label(frame_sub, text="Filter matches touching this partial path:", anchor="w").pack(fill="x")
    path_entry = Entry(frame_sub, textvariable=sub_path_var, state='disabled')
    path_entry.pack(fill="x", pady=2)
    
    Label(frame_sub, text="Text to add to output filename (appended after hyphen):", anchor="w").pack(fill="x")
    tag_entry = Entry(frame_sub, textvariable=file_tag_var, state='disabled')
    tag_entry.pack(fill="x", pady=2)

    # Option 3: No Duplicates
    Radiobutton(dialog, text="Option 3: Files with NO Duplicates", variable=mode_var, value="unique", command=update_states).pack(anchor="w", padx=20, pady=(10, 0))
    
    frame_unique = tk.LabelFrame(dialog, text="  Option 3 Settings  ", padx=10, pady=10)
    frame_unique.pack(fill="x", padx=40, pady=5)
    
    Label(frame_unique, text="Output Filename (e.g., 'unique_files.tsv'):", anchor="w").pack(fill="x")
    no_dup_entry = Entry(frame_unique, textvariable=no_dup_filename_var, state='disabled')
    no_dup_entry.pack(fill="x", pady=2)

    # Buttons
    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=20)
    Button(btn_frame, text="OK", command=on_submit, width=10).pack(side="left", padx=10)
    Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side="right", padx=10)
    
    dialog.transient()
    dialog.wait_window()
    
    return result

def find_and_report_duplicates():
    root = tk.Tk()
    root.withdraw() 

    # 1. Ask for input file (First Step)
    print("Please select the input TSV file...")
    input_path = filedialog.askopenfilename(
        title="Select Input TSV File",
        filetypes=[("TSV Files", "*.tsv"), ("All Files", "*.*")]
    )
    
    if not input_path:
        print("No file selected. Exiting.")
        return

    # 2. Ask for Report Options
    options = get_user_options(os.path.basename(input_path))
    mode = options["mode"]
    sub_path_filter = options["sub_path"]
    file_tag = options["file_tag"]
    no_dup_filename = options["no_dup_filename"]
    
    if not mode:
        print("Operation cancelled.")
        return

    # Validation
    if mode == "sub":
        if not sub_path_filter:
            messagebox.showwarning("Input Error", "For a Sub-Report, you must enter a directory path to filter by.")
            return
        if not file_tag:
            messagebox.showwarning("Input Error", "For a Sub-Report, you must enter text for the filename tag.")
            return
    elif mode == "unique":
        if not no_dup_filename:
            messagebox.showwarning("Input Error", "For the No Duplicates report, you must enter an output filename.")
            return

    # 3. Process Based on Mode
    base_dir = os.path.dirname(input_path)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    # --- OPTION 3 LOGIC: NO DUPLICATES ---
    if mode == "unique":
        if not no_dup_filename.lower().endswith('.tsv'):
            no_dup_filename += '.tsv'
        output_path = os.path.join(base_dir, no_dup_filename)
        
        print(f"Generating No Duplicates report: {output_path}")
        
        try:
            # Pass 1: Count signatures
            file_signatures = Counter()
            with open(input_path, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                # Clean headers just in case
                reader.fieldnames = [h.strip() for h in reader.fieldnames]
                
                for row in reader:
                    # Signature = Name + Size
                    fname = row.get('Filename', '').strip()
                    fsize = row.get('Size (KB)', '').strip()
                    sig = (fname, fsize)
                    file_signatures[sig] += 1
            
            # Pass 2: Write only unique files
            with open(input_path, mode='r', newline='', encoding='utf-8') as f_in, \
                 open(output_path, mode='w', newline='', encoding='utf-8') as f_out:
                
                reader = csv.DictReader(f_in, delimiter='\t')
                reader.fieldnames = [h.strip() for h in reader.fieldnames]
                
                writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames, delimiter='\t')
                writer.writeheader()
                
                saved_count = 0
                for row in reader:
                    clean_row = {k.strip(): v for k, v in row.items()}
                    fname = clean_row.get('Filename', '').strip()
                    fsize = clean_row.get('Size (KB)', '').strip()
                    sig = (fname, fsize)
                    
                    if file_signatures[sig] == 1:
                        writer.writerow(clean_row)
                        saved_count += 1
            
            messagebox.showinfo("Success", f"Report generated: {no_dup_filename}\nTotal unique files: {saved_count}")
            return # Exit after Option 3

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate unique report: {e}")
            return

    # --- OPTIONS 1 & 2 LOGIC: DUPLICATES ---
    
    # Define output filename for duplicates modes
    if mode == "full":
        output_filename = f"{base_name}_dupsReport_FULL.tsv"
    else: # sub
        safe_tag = file_tag.replace('/', '-').replace('\\', '-').replace(':', '')
        output_filename = f"{base_name}_dupsReport-{safe_tag}.tsv"
        
    output_path = os.path.join(base_dir, output_filename)

    print(f"Scanning: {input_path}")
    print(f"Mode: {mode.upper()}")
    
    grouped_files = {}
    total_files_in_dir = Counter()

    try:
        with open(input_path, mode='r', newline='', encoding='utf-8') as tsvfile:
            reader = csv.DictReader(tsvfile, delimiter='\t')
            reader.fieldnames = [h.strip() for h in reader.fieldnames]

            for row in reader:
                clean_row = {k.strip(): v for k, v in row.items()}
                
                d_path = clean_row.get('Directory path', '')
                if d_path:
                    total_files_in_dir[d_path] += 1
                
                filename = clean_row.get('Filename', '').strip()
                size_str = clean_row.get('Size (KB)', '0').strip()
                
                norm_name = normalize_filename(filename)
                key = (norm_name, size_str)
                
                if key not in grouped_files:
                    grouped_files[key] = []
                grouped_files[key].append(clean_row)

        # Identify Duplicates
        all_duplicate_groups = [v for k, v in grouped_files.items() if len(v) > 1]
        final_groups_to_report = []

        # --- FULL REPORT LOGIC ---
        if mode == "full":
            final_groups_to_report = all_duplicate_groups
            
            print("Analyzing directory topologies...")
            dir_set_info_map = analyze_directory_sets(final_groups_to_report)
            
            print(f"Sorting and Writing to: {output_path}")
            
            groups_to_sort = []
            for group in final_groups_to_report:
                filenames = [r['Filename'] for r in group]
                best_name = get_group_name(filenames)
                size_val = group[0]['Size (KB)'] 
                group_label = f"[{best_name}] of size [{size_val} KB]"
                
                first_file_dir = group[0].get('Directory path', '')
                set_label = "Unknown"
                set_count = 0
                if first_file_dir in dir_set_info_map:
                    info = dir_set_info_map[first_file_dir]
                    set_label = info[0]
                    set_count = info[1]
                
                group_rows = []
                for row in group:
                    group_rows.append([
                        set_label,
                        set_count, 
                        group_label,
                        row.get('Directory path', ''),
                        row.get('File type', ''),
                        row.get('Filename', ''),
                        row.get('Date (mm/dd/yyyy)', ''),
                        row.get('Size (KB)', '')
                    ])
                
                groups_to_sort.append({
                    'sort_key': (-int(set_count), set_label),
                    'rows': group_rows
                })

            groups_to_sort.sort(key=lambda x: x['sort_key'])

            with open(output_path, mode='w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile, delimiter='\t')
                headers = ['Directory set', '# duplicate groups', 'Duplicate Group', 'Directory path', 
                           'File type', 'Filename', 'Date (mm/dd/yyyy)', 'Size (KB)']
                writer.writerow(headers)
                for item in groups_to_sort:
                    writer.writerows(item['rows'])

        # --- SUB-REPORT LOGIC ---
        else: # mode == "sub"
            for group in all_duplicate_groups:
                match_found = False
                for file_data in group:
                    dir_path = file_data.get('Directory path', '')
                    if sub_path_filter in dir_path:
                        match_found = True
                        break
                if match_found:
                    final_groups_to_report.append(group)

            if not final_groups_to_report:
                messagebox.showinfo("Result", "No duplicates found matching criteria.")
                return

            print(f"Found {len(final_groups_to_report)} duplicate groups for sub-report.")
            print("Generating Matrix...")

            involved_dirs = set()
            dup_counts_in_subset = Counter()
            matrix_data = []

            for group in final_groups_to_report:
                filenames = [r['Filename'] for r in group]
                group_name = get_group_name(filenames)
                
                row_data = {}
                count_in_this_group = 0
                
                for row in group:
                    d_path = row.get('Directory path', '')
                    date_val = row.get('Date (mm/dd/yyyy)', '')
                    
                    if d_path:
                        involved_dirs.add(d_path)
                        dup_counts_in_subset[d_path] += 1
                        row_data[d_path] = date_val
                        count_in_this_group += 1
                
                matrix_data.append({
                    'name': group_name,
                    'dates': row_data,
                    'total_count': count_in_this_group
                })

            sorted_dirs_by_count = sorted(list(involved_dirs), key=lambda x: (-dup_counts_in_subset[x], x))
            primary_dir = sorted_dirs_by_count[0] if sorted_dirs_by_count else ""
            other_dirs = sorted([d for d in involved_dirs if d != primary_dir])
            dir_columns = [primary_dir] + other_dirs

            matrix_data.sort(key=lambda x: x['name'])

            with open(output_path, mode='w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile, delimiter='\t')
                
                headers = ["Duplicate Group"] + dir_columns + ["Total Copies"]
                writer.writerow(headers)
                
                for item in matrix_data:
                    row_output = [item['name']]
                    for d_col in dir_columns:
                        row_output.append(item['dates'].get(d_col, ""))
                    row_output.append(item['total_count'])
                    writer.writerow(row_output)
                
                summary_dups = ["# of duplicate files in directory"]
                for d_col in dir_columns:
                    summary_dups.append(dup_counts_in_subset[d_col])
                summary_dups.append("")
                writer.writerow(summary_dups)
                
                summary_totals = ["Total # of files in directory"]
                for d_col in dir_columns:
                    summary_totals.append(total_files_in_dir[d_col])
                summary_totals.append("")
                writer.writerow(summary_totals)

        messagebox.showinfo("Success", f"Report generated:\n{output_filename}")
        print("Done.")

    except Exception as e:
        print(f"Error: {e}")
        messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    find_and_report_duplicates()
