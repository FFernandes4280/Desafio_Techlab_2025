import os
from langchain.tools import tool

@tool
def load_file_paths(directory: str) -> list[str]:
    """
    Scans the specified directory and its subdirectories for .xlsx files.
    Returns a list of full file paths to these Excel files.
    """
    file_paths = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".xlsx"):
                full_path = os.path.join(dirpath, filename)
                file_paths.append(full_path)
    if not file_paths:
        raise ValueError(f"No .xlsx files found in directory: {directory}")
    print(f"Found files: {file_paths}")
    return file_paths