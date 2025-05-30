import os
import json
import csv
# It's good practice to try importing and note if specific installation is needed.
# The problem description mentions jsonpath_ng.ext specifically.
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
    Processes a single JSON file to extract text into a TSV file
    and create a corresponding JSON map file with JSONPaths.
    """
    tsv_extracted_data = []
    map_extracted_data = []
    list_num_counter = 1 # Initialize 1-based sequential index for text items

    base_filename = os.path.basename(filepath)
    print(f"Processing file: {base_filename}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Warning: Could not decode JSON from {base_filename}. Error: {e}. Skipping file.")
                return None, None # Return None for both TSV and map data
    except FileNotFoundError:
        print(f"Warning: File {base_filename} not found in {jsonfiles_dir}. Skipping.")
        return None, None
    except Exception as e:
        print(f"Warning: An unexpected error occurred while opening {base_filename}. Error: {e}. Skipping file.")
        return None, None

    if not isinstance(data, list):
        print(f"Warning: Root of JSON in {base_filename} is not a list. Skipping file.")
        return None, None

    for idx, event_obj in enumerate(data):
        if not isinstance(event_obj, dict) or "code" not in event_obj:
            continue

        code = event_obj.get("code")
        indent = event_obj.get("indent")

        try:
            parameters = event_obj.get("parameters")
            if not isinstance(parameters, list):
                continue

            texts_to_add = [] # Store (text, json_path_str) tuples temporarily

            if code == 101:
                if len(parameters) > 0 and isinstance(parameters[-1], str):
                    text = parameters[-1]
                    json_path_str = str(jsonpath_parser.parse(f'$[{idx}].parameters[{len(parameters) - 1}]'))
                    texts_to_add.append({'text': text, 'json_path': json_path_str})
                else:
                    print(f"Warning: Could not extract text for code 101 in {base_filename} at index {idx}. Parameters: {parameters}. Skipping entry.")
            
            elif code == 102:
                if len(parameters) > 0 and isinstance(parameters[0], list):
                    texts_array = parameters[0]
                    for param_idx, text_item in enumerate(texts_array):
                        if isinstance(text_item, str):
                            json_path_str = str(jsonpath_parser.parse(f'$[{idx}].parameters[0][{param_idx}]'))
                            texts_to_add.append({'text': text_item, 'json_path': json_path_str})
                        else:
                            print(f"Warning: Non-string item in texts_array for code 102 in {base_filename} at index {idx}, param_idx {param_idx}. Item: {text_item}. Skipping item.")
                else:
                    print(f"Warning: Could not extract texts_array for code 102 in {base_filename} at index {idx}. Parameters: {parameters}. Skipping entry.")

            elif code == 401:
                if len(parameters) > 0 and isinstance(parameters[0], str):
                    text = parameters[0]
                    json_path_str = str(jsonpath_parser.parse(f'$[{idx}].parameters[0]'))
                    texts_to_add.append({'text': text, 'json_path': json_path_str})
                else:
                    print(f"Warning: Could not extract text for code 401 in {base_filename} at index {idx}. Parameters: {parameters}. Skipping entry.")

            elif code == 402:
                if len(parameters) > 0 and isinstance(parameters[-1], str):
                    text = parameters[-1]
                    json_path_str = str(jsonpath_parser.parse(f'$[{idx}].parameters[{len(parameters) - 1}]'))
                    texts_to_add.append({'text': text, 'json_path': json_path_str})
                else:
                    print(f"Warning: Could not extract text for code 402 in {base_filename} at index {idx}. Parameters: {parameters}. Skipping entry.")

            # Add successfully extracted texts to TSV and Map data
            for item_data in texts_to_add:
                tsv_extracted_data.append([list_num_counter, code, indent, item_data['text']])
                map_extracted_data.append({"list_num": list_num_counter, "json_path": item_data['json_path']})
                list_num_counter += 1

        except IndexError as e:
            print(f"Warning: IndexError for code {code} in {base_filename} at index {idx}. Parameters: {parameters}. Error: {e}. Skipping entry.")
        except TypeError as e:
            print(f"Warning: TypeError for code {code} in {base_filename} at index {idx}. Parameters: {parameters}. Error: {e}. Skipping entry.")
        except Exception as e:
            print(f"Warning: An unexpected error occurred processing code {code} in {base_filename} at index {idx}. Error: {e}. Skipping entry.")

    # Write TSV file
    if tsv_extracted_data:
        output_tsv_filename = os.path.splitext(base_filename)[0] + ".tsv"
        output_tsv_filepath = os.path.join(tsvfiles_dir, output_tsv_filename)
        
        try:
            with open(output_tsv_filepath, 'w', newline='', encoding='utf-8') as tsvfile:
                writer = csv.writer(tsvfile, delimiter='\t')
                writer.writerow(["ListNum", "Code", "Indent", "Text"]) # New header
                writer.writerows(tsv_extracted_data)
            print(f"Successfully wrote TSV: {output_tsv_filepath}")
        except IOError as e:
            print(f"Error: Could not write TSV file {output_tsv_filepath}. Error: {e}")
        except Exception as e:
            print(f"Error: An unexpected error occurred while writing TSV {output_tsv_filepath}. Error: {e}")
    elif base_filename == "Troops.json":
        print(f"No data extracted for TSV from {base_filename}.")

    # Write JSON Map file
    if map_extracted_data:
        output_map_filename = base_filename + ".map.json" # e.g., Troops.json.map.json
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
        except Exception as e:
            print(f"Error: An unexpected error occurred while writing JSON map {output_map_filepath}. Error: {e}")
    elif base_filename == "Troops.json":
         print(f"No data extracted for JSON Map from {base_filename}.")
    
    return tsv_extracted_data, map_extracted_data


def main():
    """
    Main function to iterate through JSON files and process them.
    """
    ensure_output_dir_exists(tsvfiles_dir)

    if not os.path.exists(jsonfiles_dir):
        print(f"Error: Input directory '{jsonfiles_dir}' does not exist. Exiting.")
        return

    for filename in os.listdir(jsonfiles_dir):
        if filename == "Troops.json": # Only process this file for now
            full_path = os.path.join(jsonfiles_dir, filename)
            if os.path.isfile(full_path):
                process_json_file(full_path)
            else:
                print(f"Skipping {filename} as it is not a file.")


if __name__ == "__main__":
    main()
    print("Script finished.")
