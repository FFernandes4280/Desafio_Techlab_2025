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
    start_index = max(0, i)
    end_index = min(len(df) - 1, j)

    if start_index > end_index:
        print(f"No rows to update in the range [{i}, {j}] as it's outside DataFrame bounds or invalid.")
        return df 

    num_rows_to_update = (end_index - start_index + 1)
    
    # Iterate through the range of rows to update, and simultaneously through formatted_rows
    for k in range(num_rows_to_update):
        current_df_row_idx = start_index + k
        current_formatted_row = formatted_rows[k]

        for col_name, new_value in current_formatted_row.items():
            if col_name in df.columns:
                if col_name == df.columns[-1]:
                    new_value = float(new_value)
                    
                print(f"Updating column '{col_name}' at row index '{current_df_row_idx}' with value '{new_value}'.")
                df.at[current_df_row_idx, col_name] = new_value
            else:
                print(f"Warning: Column '{col_name}' not found in DataFrame for row index '{current_df_row_idx}'. Skipping update for this column.")
    return df