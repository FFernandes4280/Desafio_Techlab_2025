from langchain.agents import tool
import pandas as pd

@tool
def normalize_df(i: int, j: int, formatted_rows: list[dict], df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize the DataFrame by updating a range of rows with corresponding correctly formatted rows.

    Args:
        df (pd.DataFrame): The DataFrame to be updated.
        i (int): The starting index (inclusive) of the rows to update.
        j (int): The ending index (inclusive) of the rows to update.
        formatted_rows (list[dict]): A list of dictionaries, where each dictionary
                                     represents a correctly formatted row.
                                     Keys should be column names and values the new data.
                                     Each dict in the list will be applied to a consecutive row
                                     starting from index 'i'.

    Returns:
        pd.DataFrame: The updated DataFrame.
    """ 
    for idx, row_data in enumerate(formatted_rows):
        row_index = i + idx
        if row_index > j:
            break
        for column, value in row_data.items():
            df.at[row_index, column] = value
    return df
    