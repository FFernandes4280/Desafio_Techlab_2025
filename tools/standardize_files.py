import pandas as pd
from langchain.tools import tool

@tool
def standardize_column_names_by_content_comparison(classified_files: dict[str, str]) -> tuple[str, str, pd.DataFrame]:
    """
    Standardizes column names of DataFrames by comparing their content
    with a designated 'employee_master' DataFrame.
    It iterates through classified DataFrames. For files not classified
    as 'employee_master', it compares each of their columns against all
    columns in the 'employee_master' DataFrame.
    Renaming occurs if a column's data is an exact match (Rule 1) or
    if all its unique values are a subset of the unique values in a
    master column (Rule 2). Otherwise, original names are kept.
    """
    master_df = None
    output_data = []

    # 1. Find the employee_master DataFrame
    employee_master_path = None
    for path, classification in classified_files.items():
        if classification == "employee":
            master_df = pd.read_excel(path)
            output_data.append((path, classification, master_df))
            employee_master_path = path # Store the path to avoid re-reading
            break

    if master_df is None:
        raise ValueError("No employee master file found for standardization.")

    master_col_unique_sets = {
        col_name: set(master_df[col_name].dropna().astype(str))
        for col_name in master_df.columns
    }

    # 2. Iterate through other DataFrames to standardize their columns
    for path, classification in classified_files.items():
        if path == employee_master_path: # Skip the master file itself
            continue
        df_other = pd.read_excel(path)
        print(f"[Info] Standardizing columns for {classification} file: {path}...")

        rename_map = {}

        for other_col_name in df_other.columns:
            renamed_by_rule = False
            for master_col_name in master_df.columns:
                # Rule 1: Exact Match (Series.equals handles NaNs appropriately)
                try:
                    if df_other[other_col_name].equals(master_df[master_col_name]):
                        if other_col_name != master_col_name:
                            rename_map[other_col_name] = master_col_name
                            print(f"  '{path}': Column '{other_col_name}' matches (exact) '{master_col_name}' from master. Renaming.")
                        else:
                            print(f"  '{path}': Column '{other_col_name}' matches (exact) '{master_col_name}' from master. Name is already the same.")
                        renamed_by_rule = True
                        break
                except Exception as e:
                    print(f"  Error during exact match for {other_col_name} vs {master_col_name}: {e}")


            if not renamed_by_rule:
                # Rule 2: Subset Match (based on unique values)
                other_col_unique_set = set(df_other[other_col_name].dropna().astype(str))

                if not other_col_unique_set:
                    print(f"'{path}': Column '{other_col_name}' is empty or all NaN. Keeping original name.")
                    continue

                for master_col_name, master_set in master_col_unique_sets.items():
                    if other_col_unique_set.issubset(master_set):
                        if other_col_name != master_col_name:
                            rename_map[other_col_name] = master_col_name
                            print(f"  '{path}': Column '{other_col_name}' values are a subset of '{master_col_name}' from master. Renaming.")
                        else:
                            print(f"  '{path}': Column '{other_col_name}' values are a subset of '{master_col_name}' from master. Name is already the same.")
                        renamed_by_rule = True
                        break

            if not renamed_by_rule:
                # Rule 3: No Match
                print(f"  '{path}': Column '{other_col_name}' did not match any master column by content. Keeping original name.")

        if rename_map:
            # Create a new DataFrame with renamed columns
            df_temp = df_other.copy()
            df_other = pd.DataFrame()
            for original_col in df_temp.columns:
                new_name = rename_map.get(original_col, original_col)
                if new_name in df_other.columns: # Handle potential duplicate new names
                    # If a conflict arises, keep the original name for the conflicting column
                    print(f"  '{path}': Conflict for target name '{new_name}'. Column '{original_col}' will keep its original name.")
                    df_other[original_col] = df_temp[original_col]
                else:
                    df_other[new_name] = df_temp[original_col]

            print(f"  '{path}': Columns after standardization: {df_other.columns.tolist()}")

        output_data.append((path, classification, df_other))
    return output_data