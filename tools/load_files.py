import os
from langchain.tools import tool

@tool
def load_file_paths(directory: str) -> list[str]:
    """
    Scans the specified directory and its subdirectories for .xlsx files.
    Normalizes the filenames by removing spaces and renames the files on disk.
    Returns a list of full, normalized file paths to these Excel files.
    """
    normalized_file_paths = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".xlsx"):
                original_full_path = os.path.join(dirpath, filename)
                
                name_without_ext, ext = os.path.splitext(filename)
                normalized_filename = name_without_ext.replace(" ", "") + ext
                
                normalized_full_path = os.path.join(dirpath, normalized_filename)
                
                if original_full_path != normalized_full_path:
                    try:
                        os.rename(original_full_path, normalized_full_path)
                        print(f"Renamed '{original_full_path}' to '{normalized_full_path}'")
                    except OSError as e:
                        print(f"Error renaming file '{original_full_path}': {e}")
                        normalized_file_paths.append(original_full_path)
                        continue 
                
                normalized_file_paths.append(normalized_full_path)
    
    if not normalized_file_paths:
        raise ValueError(f"No .xlsx files found in directory: {directory}")
    
    return normalized_file_paths
