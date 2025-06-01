import pandas as pd
from langchain.tools import tool

@tool
def standardize_column_names(columns_to_rename: list[dict], df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes the names of multiple columns in a DataFrame.
    Changes the names of the columns based on the provided list of mappings.

    Args:
        columns_to_rename (list[dict]): A list of dictionaries, each containing:
            - "current_name" (str): The current name of the column to rename.
            - "standardized_name" (str): The new standardized name for the column.
        df (pd.DataFrame): The DataFrame to modify.

    Returns:
        pd.DataFrame: The updated DataFrame containing only the renamed columns.
    """
    if {'CPF', 'Nome'}.issubset(df.columns) and len(df.columns) == 3: 
        return df

    renamed_columns = {}

    for column in columns_to_rename:
        current_name = column.get("current_name")
        standardized_name = column.get("standardized_name")
        if current_name in df.columns:
            renamed_columns[current_name] = standardized_name
            print(f"Renamed column '{current_name}' to '{standardized_name}'.")
        else:
            print(f"Column '{current_name}' not found in DataFrame.")

    # Rename the columns in the DataFrame
    df = df.rename(columns=renamed_columns)
    # Return only the renamed columns
    return df[list(renamed_columns.values())]