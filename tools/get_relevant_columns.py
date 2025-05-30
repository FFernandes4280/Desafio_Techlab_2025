import os
import pandas as pd
from langchain.tools import tool
from groq import Groq
import json

@tool
def extract_and_append_data(
    file_path: str,
    file_classification: str
) -> str:
    """
    Extracts relevant columns from a processed file based on its classification
    and appends them to the global OUTPUT_DATA_FRAME.

    Args:
        file_path (str): The path to the Excel file to process.
        file_classification (str): The classification of the file ('employee' or 'other').

    Returns:
        str: A message indicating the success or failure of the operation.
    """
