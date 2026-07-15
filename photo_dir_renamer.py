"""Directory Renamer & Audit Reporter.

Traverses a flat directory tree containing unstandardized Apple Moment-formatted
folders, extracts embedded timestamp data, and normalizes them into the
standardized pipeline schema: `YYYY_MM_DD-PhotographerID-Place_Description`.

Modifications are performed directly on the filesystem while simultaneously
exporting a tab-separated values (TSV) ledger and a parallel execution log file.

================================================================================
"""

import os
import re
import sys
from datetime import datetime
from typing import List, Dict

import photo_dir_utils as utils

# Pre-compiled regular expression anchor to verify correct pipeline formatting
CORRECT_FORMAT_REGEX = re.compile(r'^\d{4}_\d{2}_\d{2}-')


def clean_to_pascal_case(text: str) -> str:
    """Sanitize raw unstructured text strings into strict PascalCase identifiers.

    Strip out special characters, punctuation marks, and structural spacing,
    capitalizing the initial character of individual alphanumeric tokens.

    Args:
        text: The raw descriptive or location text string to transform.

    Returns:
        A sanitized, cohesive PascalCase text identifier string. Return an empty
        string if the input is invalid, empty, or whitespace-only.
    """
    if not text or not text.strip():
        return ""
    words = re.findall(r'[a-zA-Z0-9]+', text)
    return "".join(w.capitalize() for w in words)


def count_files_in_dir(target_path: str) -> int:
    """Calculate the absolute count of non-hidden files within a directory.

    Perform an immediate surface-level iteration of the specified path. Hidden
    configuration assets (files prefixed with a period) are explicitly omitted.

    Args:
        target_path: The absolute filesystem path of the directory to evaluate.

    Returns:
        The total count of valid, non-hidden target files. Return 0 if an
        OS-level exception or permission error is encountered.
    """
    count = 0
    try:
        with os.scandir(target_path) as it:
            for entry in it:
                if not entry.name.startswith('.') and entry.is_file():
                    count += 1
    except OSError:
        pass
    return count

def rename_directories_and_report(
    search_path: str,
    save_dir: str,
    file_base: str,
    photographer_id: str,
    machine_id: str,
    photog_data: Dict = None
) -> None:
    """Traverse a directory to normalize folder structures and log changes.

    Seed an iterative stack walker using strictly the immediate child
    subdirectories of the target root, ensuring the entry point root folder itself
    is never inspected, skipped, or mutated.

    Args:
        search_path: The absolute filesystem root directory containing the
            unstandardized target subdirectories.
        save_dir: The absolute path where the finalized TSV audit log ledger will be generated.
        file_base: The base name for the output files.
        photographer_id: The verified alphanumeric pipeline identifier tag
            assigned to the primary image creator.
        machine_id: Host environment identifier tag where execution is running.
        photog_data: Optional dictionary containing state metadata about the selected 
            or newly added photographer configuration.
    """
    if not os.path.exists(search_path):
        print(f"Error: Target path '{search_path}' does not exist.",
              file=sys.stderr)
        return

    # Generate execution timestamp for tracking context
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"Processing directory: {search_path}")
    print(f"Photographer: {photographer_id}")
    print("-" * 40)

    rename_count = 0
    skip_count = 0

    # Structured column headers and data aggregation container for the TSV report
    headers = ['original dir name', 'new dir name', 'status', 'number of files contained', 'processed_at']
    audit_rows = []

    # Isolate initial parent target subdirectory paths
    stack: List[str] = []
    try:
        with os.scandir(search_path) as it:
            for entry in it:
                if not entry.name.startswith('.') and entry.is_dir():
                    stack.append(entry.path)
    except OSError as e:
        print(f"Error scanning baseline directory contents: {e}",
              file=sys.stderr)
        return

    # Execute flat traversal of target stack entries
    while stack:
        current_path = stack.pop()
        dir_name = os.path.basename(current_path)

        # Skip if directory already matches the target standard schema
        if CORRECT_FORMAT_REGEX.match(dir_name):
            file_count = count_files_in_dir(current_path)
            print(f"Skipped: '{dir_name}' (Already correctly named)")
            audit_rows.append([dir_name, "", "Skipped: Already correctly named",
                               file_count, run_timestamp])
            skip_count += 1
            continue

        # Right-to-left split strategy to handle commas within location strings
        parts = dir_name.rsplit(',', 2)
        parsed_date = None
        discovered_location = ""

        if len(parts) >= 3:
            date_part = f"{parts[-2]},{parts[-1]}".strip()
            parsed_date = utils.parse_date_string(date_part)
            if parsed_date:
                discovered_location = parts[0].strip()
        elif len(parts) == 2:
            date_part = f"{parts[-2]},{parts[-1]}".strip()
            parsed_date = utils.parse_date_string(date_part)

        if not parsed_date:
            parsed_date = utils.parse_date_string(dir_name)

        # Route directory transformation rules based on date resolution
        if parsed_date:
            file_count = count_files_in_dir(current_path)
            
            if discovered_location:
                pascal_place = clean_to_pascal_case(discovered_location)
                place_desc = f"{pascal_place}_peopleORdescription"
            else:
                place_desc = "place_peopleORdescription"
            
            new_name = f"{parsed_date}-{photographer_id}-{place_desc}"
            parent_dir = os.path.dirname(current_path)
            new_path = os.path.join(parent_dir, new_name)

            # Only perform renaming operations if string mutations occurred
            if dir_name != new_name:
                audit_rows.append([dir_name, new_name, "renamed",
                                   file_count, run_timestamp])
                rename_count += 1

                try:
                    os.rename(current_path, new_path)
                    print(f"Renamed: '{dir_name}'  -->  '{new_name}'")
                except OSError as err:
                    print(f"ERROR: Could not rename '{dir_name}'. Reason: {err}", 
                          file=sys.stderr)
            else:
                print(f"Skipped: '{dir_name}' (Already correctly named)")
                audit_rows.append([dir_name, "", "Skipped: Already correctly named",
                                   file_count, run_timestamp])
                skip_count += 1
        else:
            # Log descriptive parsing error messages for unparsed dates
            file_count = count_files_in_dir(current_path)
            if len(parts) < 2:
                msg = f"SKIP: '{dir_name}' does not contain enough commas to be a valid date."
            else:
                date_candidate = parts[-2] + "," + parts[-1]
                msg = f"SKIP: extracted end string '{date_candidate}' is not a valid date."
            print(msg)
            audit_rows.append([dir_name, "", msg, file_count, run_timestamp])
            skip_count += 1

    # Persist the collected operational data rows to the TSV file using utilities
    utils.write_tsv_report(save_dir, file_base, headers, audit_rows)

    # Extract target directory path context for the terminal summary output
    target_output_dir = os.path.dirname(os.path.join(save_dir, file_base))

    print("=" * 50)
    print("Renaming Pipeline Processing Completed.")
    print(f"Total Directories Renamed:    {rename_count}")
    print(f"Total Directories Unmodified: {skip_count}")
    print(f"Audit logs saved to: '{target_output_dir}'")
    print("=" * 50)

    # Generate the parallel context metadata log via utilities
    metadata_context: Dict[str, str] = {
        "date": run_timestamp,
        "machine": machine_id,
        "full path": search_path
    }
    
    summary_lines: List[str] = [
        "Renaming Pipeline Processing Completed.",
        f"Total Directories Renamed:    {rename_count}",
        f"Total Directories Unmodified: {skip_count}"
    ]
    
    # Forward the metadata context along with the optional photographer configuration dictionary 
    utils.write_execution_log(
        save_dir=save_dir,
        file_base=file_base,
        metadata=metadata_context,
        summary_lines=summary_lines,
        photog_data=photog_data
    )

if __name__ == "__main__":
    # Fetch distinct state configurations using the updated absolute path constants
    start_scan = utils.get_start_dir(utils.SCAN_CONFIG_FILE)
    start_save = utils.get_start_dir(utils.SAVE_CONFIG_FILE)
    
    print("Launching Unified Pipeline Configuration Suite...")

    # Pass both distinct paths down to the modified UI generator
    config = utils.prompt_report_configuration(
        start_scan_dir=start_scan, 
        start_save_dir=start_save, 
        show_photographer=True
    )

    if config:
        rename_directories_and_report(
            search_path=config['scan_dir'],
            save_dir=config['save_dir'],
            file_base=config['file_base'],
            photographer_id=config['photographer'],
            machine_id=config['machine'],
            photog_data=config
        )
    else:
        print("Operation halted. Configuration parameters cancelled.")