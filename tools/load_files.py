import os
from langchain.tools import tool

@tool
def load_file_paths(directory: str) -> list[str]:
    """
    Scans the specified directory and its subdirectories for .xlsx files.
    Replaces spaces in file names with underscores.
    Returns a list of full file paths to these Excel files.
    """
    file_paths = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".xlsx"):
                new_filename = filename.replace(" ", "")
                if new_filename != filename:
                    old_path = os.path.join(dirpath, filename)
                    new_path = os.path.join(dirpath, new_filename)
                    os.rename(old_path, new_path)
                    filename = new_filename  
                
                full_path = os.path.join(dirpath, filename)
                file_paths.append(full_path)
    if not file_paths:
        raise ValueError(f"No .xlsx files found in directory: {directory}")
    return file_paths