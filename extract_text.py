import os
import json
import csv

try:
    from jsonpath_ng.ext import parser as jsonpath_parser
except ImportError:
    print("jsonpath-ng library not found. Please install it: pip install jsonpath-ng")
    exit(1)

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
    and create a corresponding JSON map file with deep JSONPaths.
    """
    tsv_extracted_data = []
    map_extracted_data = []
    list_num_counter = 1 # Initialize 1-based sequential index for text items

    base_filename = os.path.basename(filepath)
    print(f"Processing file: {base_filename}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                root_list = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Warning: Could not decode JSON from {base_filename}. Error: {e}. Skipping file.")
                return None, None
    except FileNotFoundError:
        print(f"Warning: File {base_filename} not found in {jsonfiles_dir}. Skipping.")
        return None, None
    except Exception as e:
        print(f"Warning: An unexpected error occurred while opening {base_filename}. Error: {e}. Skipping file.")
        return None, None

    if not isinstance(root_list, list):
        print(f"Warning: Root of JSON in {base_filename} is not a list. Skipping file.")
        return None, None

    for i, troop_object in enumerate(root_list):
        if troop_object is None: # Handle potential null objects in the root list
            # print(f"Info: Encountered null object at root index {i} in {base_filename}. Skipping.")
            continue
        
        if not isinstance(troop_object, dict):
            # print(f"Warning: Item at root index {i} in {base_filename} is not a dictionary. Skipping.")
            continue

        if "pages" not in troop_object or not isinstance(troop_object["pages"], list):
            # print(f"Warning: Missing or invalid 'pages' list in troop object at index {i} in {base_filename}. Skipping troop object.")
            continue

        for j, page_obj in enumerate(troop_object["pages"]):
            if not isinstance(page_obj, dict):
                # print(f"Warning: Page object at troop index {i}, page index {j} in {base_filename} is not a dictionary. Skipping page.")
                continue

            if "list" not in page_obj or not isinstance(page_obj["list"], list):
                # print(f"Warning: Missing or invalid 'list' (event commands) in page object at troop index {i}, page index {j} in {base_filename}. Skipping page.")
                continue
            
            for k, event_cmd in enumerate(page_obj["list"]):
                if not isinstance(event_cmd, dict) or "code" not in event_cmd:
                    # print(f"Info: Event command at T:{i} P:{j} E:{k} is not a valid command object or missing 'code'. Skipping.")
                    continue

                code = event_cmd.get("code")
                indent = event_cmd.get("indent", 0) # Default indent to 0 if missing
                parameters = event_cmd.get("parameters") # Parameters might be missing for some codes like 0

                if not isinstance(parameters, list) and code in [101, 102, 401, 402]: # Only codes that need parameters are strictly checked
                    # print(f"Warning: 'parameters' field is missing or not a list for code {code} at T:{i} P:{j} E:{k} in {base_filename}. Skipping entry.")
                    continue
                
                current_texts_to_add = [] # Store {'text': ..., 'json_path': ...} for current event_cmd

                try:
                    if code == 101:
                        if parameters and len(parameters) > 0 and isinstance(parameters[-1], str):
                            text = parameters[-1]
                            if text: # Ensure non-empty string for code 101
                                json_path_str = str(jsonpath_parser.parse(f'$[{i}].pages[{j}].list[{k}].parameters[{len(parameters) - 1}]'))
                                current_texts_to_add.append({'text': text, 'json_path': json_path_str, 'code': code, 'indent': indent})
                        # else:
                            # print(f"Warning: Could not extract text for code 101 at T:{i} P:{j} E:{k}. Invalid params: {parameters}")
                    
                    elif code == 102:
                        if parameters and len(parameters) > 0 and isinstance(parameters[0], list):
                            texts_array = parameters[0]
                            for param_idx, text_item in enumerate(texts_array):
                                if isinstance(text_item, str):
                                    json_path_str = str(jsonpath_parser.parse(f'$[{i}].pages[{j}].list[{k}].parameters[0][{param_idx}]'))
                                    current_texts_to_add.append({'text': text_item, 'json_path': json_path_str, 'code': code, 'indent': indent})
                                # else:
                                    # print(f"Warning: Non-string item in texts_array for code 102 at T:{i} P:{j} E:{k}, param_idx {param_idx}.")
                        # else:
                            # print(f"Warning: Could not extract texts_array for code 102 at T:{i} P:{j} E:{k}. Invalid params: {parameters}")

                    elif code == 401:
                        if parameters and len(parameters) > 0 and isinstance(parameters[0], str):
                            text = parameters[0]
                            json_path_str = str(jsonpath_parser.parse(f'$[{i}].pages[{j}].list[{k}].parameters[0]'))
                            current_texts_to_add.append({'text': text, 'json_path': json_path_str, 'code': code, 'indent': indent})
                        # else:
                            # print(f"Warning: Could not extract text for code 401 at T:{i} P:{j} E:{k}. Invalid params: {parameters}")
                    
                    elif code == 402:
                        if parameters and len(parameters) > 0 and isinstance(parameters[-1], str):
                            text = parameters[-1]
                            json_path_str = str(jsonpath_parser.parse(f'$[{i}].pages[{j}].list[{k}].parameters[{len(parameters) - 1}]'))
                            current_texts_to_add.append({'text': text, 'json_path': json_path_str, 'code': code, 'indent': indent})
                        # else:
                            # print(f"Warning: Could not extract text for code 402 at T:{i} P:{j} E:{k}. Invalid params: {parameters}")

                    # Add successfully extracted texts to TSV and Map data
                    for item_data in current_texts_to_add:
                        tsv_extracted_data.append([list_num_counter, item_data['code'], item_data['indent'], item_data['text']])
                        map_extracted_data.append({"list_num": list_num_counter, "json_path": item_data['json_path']})
                        list_num_counter += 1
                
                except IndexError as e:
                    print(f"Warning: IndexError for code {code} at T:{i} P:{j} E:{k}. Params: {parameters}. Error: {e}. Skipping.")
                except TypeError as e:
                    print(f"Warning: TypeError for code {code} at T:{i} P:{j} E:{k}. Params: {parameters}. Error: {e}. Skipping.")
                except Exception as e:
                    print(f"Warning: Unexpected error for code {code} at T:{i} P:{j} E:{k}. Error: {e}. Skipping.")

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
        if filename.endswith(".json") and not filename.endswith(".map.json"): # Process only main JSON files
            full_path = os.path.join(jsonfiles_dir, filename)
            if os.path.isfile(full_path):
                 # For this task, specifically target Troops.json
                if filename == "Troops.json":
                    process_json_file(full_path)
                # else:
                #    print(f"Skipping file {filename} as it's not Troops.json (per current task focus).")
            # else:
                # print(f"Skipping {filename} as it is not a file.")

if __name__ == "__main__":
    main()
    print("Script finished.")
