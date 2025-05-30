import os
import pandas as pd
from langchain.tools import tool
from groq import Groq # Import the Groq client

@tool
def get_file_classification(file_path: str) -> str:
    """
    Classifies a file as 'employee' or 'other' by analyzing its column names
    using an LLM to identify typical employee data fields (name, CPF, department, salary),
    regardless of their exact naming conventions.

    Returns:
        str: Classification type ("employee" or "other").
    """
    try:
        # Read only a few rows to get column names efficiently
        df = pd.read_excel(file_path, nrows=5)
        # Get column names as a list (can keep original case or lower for LLM analysis)
        column_names = [str(col) for col in df.columns]
    except Exception as e:
        print(f"[Warning] Could not read file '{file_path}': {e}. Classifying as 'other'.")
        return "other" # If the file can't be read, it's not an employee file for processing

    # Initialize the Groq client (ensure your GROQ_API_KEY is set as an environment variable)
    llm_client = Groq() 

    # Prepare the prompt for the LLM
    column_list_str = ", ".join(column_names)
    llm_prompt = f"""
    Examine the following list of column names from an Excel file: '{column_list_str}'.

    Your goal is to determine if this file is primarily an 'employee' data file.
    An 'employee' file MUST contain columns that semantically represent:
    1.  **Employee Name** (e.g., "Nome Completo", "Full Name", "Employee Name")
    2.  **CPF or Identification Number** (e.g., "CPF", "ID", "Número Registro", "Identification Number")
    3.  **Department or Cost Center** (e.g., "Departamento", "Centro de Custo", "Área", "Department")
    4.  **Salary or Remuneration** (e.g., "Salário", "Remuneração Bruta", "Monthly Pay", "Salary")

    Consider synonyms, common abbreviations, and different language terms for these concepts.
    Based *only* on whether these four essential data types are present in the columns,
    respond with either 'employee' or 'other'.

    Your response must be a single word: either 'employee' or 'other'.
    Do not include any other text, explanations, or punctuation.
    """

    messages = [
        {
            "role": "system",
            "content": "You are a strict data classifier. Respond with 'employee' if the provided columns represent a standard employee dataset (containing Name, ID, Department, and Salary information), otherwise respond with 'other'. Your output must be a single word: 'employee' or 'other'."
        },
        {
            "role": "user",
            "content": llm_prompt
        }
    ]

    try:
        response = llm_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct", # Use your preferred Groq model
            messages=messages,
            temperature=0.0, # Keep temperature low for more deterministic classification
            max_tokens=10 # Limit tokens to prevent verbosity
        )
        
        # Clean and normalize the LLM's response
        classification_result = response.choices[0].message.content.strip().lower()

        if "employee" in classification_result:
            print(f"[Info] File '{file_path}' classified as 'employee' by LLM analysis.")
            return "employee"
        else:
            print(f"[Info] File '{file_path}' classified as 'other' by LLM analysis.")
            return "other"

    except Exception as e:
        print(f"[Error] LLM classification failed for '{file_path}': {e}. Classifying as 'other'.")
        return "other"