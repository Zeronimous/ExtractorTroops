import os
import json
import csv
import copy # To ensure we modify a copy of the loaded JSON data

try:
    from jsonpath_ng import parse as jsonpath_parse
except ImportError:
    print("jsonpath-ng library not found. Please ensure it is installed: pip install jsonpath-ng")
    exit(1)

# Define input and output directories
tsvfiles_dir = "tsvfiles"       # Input for TSVs (with translated 'Text') and .map.json files
jsonfiles_dir = "jsonfiles"     # Input for original JSONs
fixedjsonfiles_dir = "fixedjsonfiles" # Output for modified JSONs

def ensure_output_dir_exists(directory_path):
    """Checks if the output directory exists and creates it if not."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Created output directory: {directory_path}")

def load_mappings(map_filepath):
    """Loads the JSON mapping file."""
    if not os.path.exists(map_filepath):
        print(f"Warning: Mapping file {map_filepath} not found. Skipping.")
        return None, None
    try:
        with open(map_filepath, 'r', encoding='utf-8') as f:
            map_data = json.load(f)
            if "original_filename" not in map_data or "mappings" not in map_data:
                print(f"Warning: Mapping file {map_filepath} is malformed (missing 'original_filename' or 'mappings'). Skipping.")
                return None, None
            mappings_dict = {item["list_num"]: item["json_path"] for item in map_data["mappings"]}
            return map_data["original_filename"], mappings_dict
    except json.JSONDecodeError as e:
        print(f"Warning: Could not decode JSON from mapping file {map_filepath}. Error: {e}. Skipping.")
        return None, None
    except Exception as e:
        print(f"Warning: An unexpected error occurred while loading mapping file {map_filepath}. Error: {e}. Skipping.")
        return None, None

def process_tsv_file_with_map(tsv_filepath):
    """
    Processes a single TSV file (where the 'Text' column contains the translation)
    using its corresponding .map.json file to inject translated text back into the original JSON file.
    """
    base_tsv_filename = os.path.basename(tsv_filepath)
    map_filename = os.path.splitext(base_tsv_filename)[0] + ".json.map.json"
    map_filepath = os.path.join(tsvfiles_dir, map_filename)

    print(f"Processing TSV file: {base_tsv_filename} with map: {map_filename}")

    original_json_doc_name, mappings = load_mappings(map_filepath)
    if not original_json_doc_name or not mappings:
        return

    original_json_filepath = os.path.join(jsonfiles_dir, original_json_doc_name)
    output_json_filepath = os.path.join(fixedjsonfiles_dir, original_json_doc_name)

    if not os.path.exists(original_json_filepath):
        print(f"Warning: Original JSON file {original_json_filepath} (from map) not found. Skipping TSV file {base_tsv_filename}.")
        return

    try:
        with open(original_json_filepath, 'r', encoding='utf-8') as f:
            original_json_data = json.load(f)
            modified_json_data = copy.deepcopy(original_json_data)
    except json.JSONDecodeError as e:
        print(f"Warning: Could not decode JSON from {original_json_filepath}. Error: {e}. Skipping.")
        return
    except Exception as e:
        print(f"Warning: An unexpected error occurred while opening {original_json_filepath}. Error: {e}. Skipping.")
        return

    updates_count = 0
    try:
        with open(tsv_filepath, 'r', newline='', encoding='utf-8') as tsvfile:
            reader = csv.reader(tsvfile, delimiter='\t')
            header = next(reader, None)
            if not header:
                print(f"Warning: TSV file {base_tsv_filename} is empty or has no header. Skipping.")
                return

            try:
                listnum_col_idx = header.index("ListNum")
                # The 'Text' column now contains the translated text
                text_col_idx = header.index("Text")
            except ValueError as e:
                # Updated error message for missing columns
                print(f"Warning: TSV file {base_tsv_filename} is missing 'ListNum' or 'Text' column. Error: {e}. Skipping.")
                return
            
            for row_idx, row in enumerate(reader):
                if len(row) <= max(listnum_col_idx, text_col_idx):
                    print(f"Warning: Row {row_idx + 1} in {base_tsv_filename} is shorter than expected. Skipping row.")
                    continue

                try:
                    list_num_from_tsv = int(row[listnum_col_idx])
                except ValueError:
                    print(f"Warning: Invalid ListNum '{row[listnum_col_idx]}' in row {row_idx + 1} of {base_tsv_filename}. Skipping row.")
                    continue
                
                # This is now the (potentially) translated text
                translated_text_from_text_column = row[text_col_idx]

                if not translated_text_from_text_column: # Skip if text (translation) is empty
                    # print(f"Info: Text (translation) is empty for ListNum {list_num_from_tsv} in {base_tsv_filename}. Skipping update.")
                    continue
                
                json_path_str = mappings.get(list_num_from_tsv)
                if not json_path_str:
                    print(f"Warning: ListNum {list_num_from_tsv} from TSV row {row_idx + 1} not found in map file {map_filename}. Skipping update for this row.")
                    continue
                
                try:
                    jsonpath_expr = jsonpath_parse(json_path_str)
                    matches = jsonpath_expr.update(modified_json_data, translated_text_from_text_column)
                    if matches:
                        updates_count += 1
                    else:
                        print(f"Warning: JSONPath '{json_path_str}' (for ListNum {list_num_from_tsv}) not found or did not match in {original_json_doc_name}. Update skipped for this row.")
                except Exception as e:
                    print(f"Warning: Error processing JSONPath '{json_path_str}' (for ListNum {list_num_from_tsv}) from {base_tsv_filename}. Error: {e}. Skipping update for this row.")

    except FileNotFoundError:
        print(f"Warning: TSV file {tsv_filepath} not found during processing. Skipping.")
        return
    except Exception as e:
        print(f"Warning: An error occurred while reading or processing {base_tsv_filename}. Error: {e}. Skipping.")
        return

    if updates_count > 0:
        try:
            with open(output_json_filepath, 'w', encoding='utf-8') as outfile:
                json.dump(modified_json_data, outfile, ensure_ascii=False, indent=4)
            print(f"Successfully wrote modified JSON to: {output_json_filepath} with {updates_count} updates.")
        except IOError as e:
            print(f"Error: Could not write modified JSON file {output_json_filepath}. Error: {e}")
        except Exception as e:
            print(f"Error: An unexpected error occurred while writing JSON {output_json_filepath}. Error: {e}")
    else:
        print(f"No updates were made to {original_json_doc_name} based on {base_tsv_filename} and its map. Output file not written.")


def main():
    """
    Main function to iterate through TSV files and process them for JSON injection
    using their corresponding .map.json files. Assumes the 'Text' column in the TSV
    contains the translated text.
    """
    ensure_output_dir_exists(fixedjsonfiles_dir)

    if not os.path.exists(tsvfiles_dir):
        print(f"Error: Input TSV/Map directory '{tsvfiles_dir}' does not exist. Exiting.")
        return
    
    if not os.path.exists(jsonfiles_dir):
        print(f"Error: Original JSON directory '{jsonfiles_dir}' does not exist. Exiting.")
        return

    processed_files = 0
    for filename in os.listdir(tsvfiles_dir):
        if filename.endswith(".tsv") and not filename.endswith(".map.json"):
            full_tsv_path = os.path.join(tsvfiles_dir, filename)
            if os.path.isfile(full_tsv_path):
                process_tsv_file_with_map(full_tsv_path)
                processed_files +=1
    
    if processed_files == 0:
        print("No TSV files found in the tsvfiles directory to process.")


if __name__ == "__main__":
    main()
    print("Injection script finished.")
