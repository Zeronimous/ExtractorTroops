import os
import json
import csv

# jsonpath_ng is not strictly needed if we use f-strings for path construction
# and the injection script handles parsing.
# try:
#     from jsonpath_ng.ext import parser as jsonpath_parser
# except ImportError:
#     print("jsonpath-ng library not found. Please install it: pip install jsonpath-ng")
#     exit(1)

# Define input and output directories
jsonfiles_dir = "jsonfiles"
tsvfiles_dir = "tsvfiles"

def ensure_output_dir_exists(directory_path):
    """Checks if the output directory exists and creates it if not."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Created output directory: {directory_path}")

def process_json_file(filepath):
    """
    Processes a single JSON file with nested structure to extract text into a TSV file
    and create a corresponding JSON map file with deep JSONPaths,
    including enhanced error handling.
    """
    tsv_extracted_data = []
    map_extracted_data = []
    list_num_counter = 1

    base_filename = os.path.basename(filepath)
    print(f"Processing file: {base_filename}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            root_list = json.load(f)
    except FileNotFoundError:
        print(f"Warning: File {base_filename} not found in {jsonfiles_dir}. Skipping.")
        return None, None
    except json.JSONDecodeError as e:
        print(f"Warning: Could not decode JSON from {base_filename}. Error: {e}. Skipping file.")
        return None, None
    except Exception as e:
        print(f"Warning: An unexpected error occurred while opening {base_filename}. Error: {e}. Skipping file.")
        return None, None

    if not isinstance(root_list, list):
        print(f"Warning: Root of JSON in {base_filename} is not a list. Skipping file.")
        return None, None

    for i, troop_object in enumerate(root_list):
        if troop_object is None:
            continue
        if not isinstance(troop_object, dict):
            continue
        if "pages" not in troop_object or not isinstance(troop_object["pages"], list):
            continue

        for j, page_obj in enumerate(troop_object["pages"]):
            if not isinstance(page_obj, dict):
                continue
            if "list" not in page_obj or not isinstance(page_obj["list"], list):
                continue

            for k, event_cmd in enumerate(page_obj["list"]):
                # --- Start of outer try-except for each event_cmd ---
                try:
                    if not isinstance(event_cmd, dict) or "code" not in event_cmd:
                        continue

                    code = event_cmd.get("code")
                    indent = event_cmd.get("indent", 0)
                    parameters = event_cmd.get("parameters")

                    # Centralized parameter list check for relevant codes
                    if code in [101, 102, 401, 402]: # Codes that require parameters
                        if not isinstance(parameters, list):
                            print(f"Warning: Parameters not a list for event at T:{i} P:{j} E:{k}. Code: {code}, Params: {parameters}. Skipping.")
                            continue
                        if not parameters: # Check if parameters list is empty
                             print(f"Warning: Parameters list is empty for event at T:{i} P:{j} E:{k}. Code: {code}. Skipping.")
                             continue


                    text_to_extract_single = None # For codes 101, 401, 402
                    json_path_str_single = None   # For codes 101, 401, 402

                    if code == 101:
                        if not isinstance(parameters[-1], str):
                            print(f"Warning: Invalid params for code 101 at T:{i} P:{j} E:{k}. Params: {parameters}. Expected string at end. Skipping.")
                            continue
                        text_to_extract_single = parameters[-1]
                        if not text_to_extract_single:
                            print(f"Info: Empty string for code 101 at T:{i} P:{j} E:{k}. Params: {parameters}. Skipping.")
                            continue
                        json_path_str_single = f"$[{i}].pages[{j}].list[{k}].parameters[{len(parameters) - 1}]"

                    elif code == 102:
                        if not isinstance(parameters[0], list):
                            print(f"Warning: Invalid params for code 102 at T:{i} P:{j} E:{k}. Params: {parameters}. Expected sub-list at start. Skipping.")
                            continue
                        texts_array = parameters[0]
                        for param_idx, text_item in enumerate(texts_array):
                            if not isinstance(text_item, str):
                                print(f"Warning: Non-string item in sub-array for code 102 at T:{i} P:{j} E:{k}. Params: {parameters}, Item: {text_item}. Skipping item.")
                                continue

                            # For code 102, append directly and increment counter
                            current_json_path = f"$[{i}].pages[{j}].list[{k}].parameters[0][{param_idx}]"
                            tsv_extracted_data.append([list_num_counter, code, indent, text_item])
                            map_extracted_data.append({"list_num": list_num_counter, "json_path": current_json_path})
                            list_num_counter += 1
                        continue # Code 102 handles its own appends, skip common append logic

                    elif code == 401:
                        if not isinstance(parameters[0], str):
                            print(f"Warning: Invalid params for code 401 at T:{i} P:{j} E:{k}. Params: {parameters}. Expected string at start. Skipping.")
                            continue
                        text_to_extract_single = parameters[0]
                        # Ensure text is not empty, though 401 usually has content.
                        if not text_to_extract_single:
                             print(f"Info: Empty string for code 401 at T:{i} P:{j} E:{k}. Params: {parameters}. Skipping.")
                             continue
                        json_path_str_single = f"$[{i}].pages[{j}].list[{k}].parameters[0]"

                    elif code == 402:
                        if not isinstance(parameters[-1], str):
                            print(f"Warning: Invalid params for code 402 at T:{i} P:{j} E:{k}. Params: {parameters}. Expected string at end. Skipping.")
                            continue
                        text_to_extract_single = parameters[-1]
                        if not text_to_extract_single:
                             print(f"Info: Empty string for code 402 at T:{i} P:{j} E:{k}. Params: {parameters}. Skipping.")
                             continue
                        json_path_str_single = f"$[{i}].pages[{j}].list[{k}].parameters[{len(parameters) - 1}]"

                    # Common append logic for codes 101, 401, 402
                    if text_to_extract_single is not None and json_path_str_single is not None:
                        tsv_extracted_data.append([list_num_counter, code, indent, text_to_extract_single])
                        map_extracted_data.append({"list_num": list_num_counter, "json_path": json_path_str_single})
                        list_num_counter += 1

                except Exception as e:
                    print(f"Warning: Unexpected error processing event at T:{i} P:{j} E:{k}. Code: {event_cmd.get('code')}, Params: {event_cmd.get('parameters')}. Error: {e}. Skipping.")
                    continue
                # --- End of outer try-except for each event_cmd ---

    # Write TSV file
    if tsv_extracted_data:
        output_tsv_filename = os.path.splitext(base_filename)[0] + ".tsv"
        output_tsv_filepath = os.path.join(tsvfiles_dir, output_tsv_filename)
        try:
            with open(output_tsv_filepath, 'w', newline='', encoding='utf-8') as tsvfile:
                writer = csv.writer(tsvfile, delimiter='\t')
                writer.writerow(["ListNum", "Code", "Indent", "Text"])
                writer.writerows(tsv_extracted_data)
            print(f"Successfully wrote TSV: {output_tsv_filepath}")
        except IOError as e:
            print(f"Error: Could not write TSV file {output_tsv_filepath}. Error: {e}")
    else:
        print(f"No data extracted for TSV from {base_filename}.")

    # Write JSON Map file
    if map_extracted_data:
        output_map_filename = base_filename + ".map.json"
        output_map_filepath = os.path.join(tsvfiles_dir, output_map_filename)
        map_content = {
            "original_filename": base_filename,
            "mappings": map_extracted_data
        }
        try:
            with open(output_map_filepath, 'w', encoding='utf-8') as mapfile:
                json.dump(map_content, mapfile, ensure_ascii=False, indent=2)
            print(f"Successfully wrote JSON Map: {output_map_filepath}")
        except IOError as e:
            print(f"Error: Could not write JSON Map file {output_map_filepath}. Error: {e}")
    else:
         print(f"No data extracted for JSON Map from {base_filename}.")

    return tsv_extracted_data, map_extracted_data

def main():
    ensure_output_dir_exists(tsvfiles_dir)
    if not os.path.exists(jsonfiles_dir):
        print(f"Error: Input directory '{jsonfiles_dir}' does not exist. Exiting.")
        return

    for filename in os.listdir(jsonfiles_dir):
        if filename.endswith(".json") and not filename.endswith(".map.json"):
            full_path = os.path.join(jsonfiles_dir, filename)
            if os.path.isfile(full_path):
                if filename == "Troops.json": # Process only Troops.json for this task
                    process_json_file(full_path)

if __name__ == "__main__":
    main()
    print("Script finished.")
