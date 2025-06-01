import pandas as pd
import json
from dotenv import find_dotenv, load_dotenv
from groq import Groq

from tools.load_files import load_file_paths
from tools.standardize_files import standardize_column_names
from tools.normalize_df import normalize_df

# --- Environment Setup ---
_ = load_dotenv(find_dotenv())

# --- Global Variables
ROOT_DIR = "Planilhas"
OUTPUT_PATH = "result.xlsx"
OUTPUT_DATA_FRAME = pd.read_excel("Planilhas/DadosColaboradores.xlsx")

def run_agent(userPrompt, df):
    global OUTPUT_DATA_FRAME  

    client = Groq()
    messages = [
        {
            "role": "user",
            "content": userPrompt
        }
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "standardize_column_names",
                "description": "Will receive the list of important column names and the names they should be standardized to.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "columns_to_rename": {
                            "type": "array", 
                            "items": {
                                "type": "object",
                                "properties": {
                                    "current_name": {
                                        "type": "string",
                                        "description": "The current column name in the DataFrame."
                                    },
                                    "standardized_name": {
                                        "type": "string",
                                        "description": "The standardized column name to rename to."
                                    }
                                },
                                "required": ["current_name", "standardized_name"]
                            },
                            "description": "A list of dictionaries where each dictionary maps a current column name to its standardized name.",
                        }
                    },
                    "required": ["columns_to_rename"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "normalize_df",
                "description": "Updates a specific range of rows (from index 'i' to 'j' inclusive) using a provided list of formatted row data. Each dictionary in the 'formatted_rows' list will be applied to a corresponding row within the specified range.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "i": {
                            "type": "integer",
                            "description": "The starting index (inclusive) of the rows in the DataFrame to be updated."
                        },
                        "j": {
                            "type": "integer",
                            "description": "The ending index (inclusive) of the rows in the DataFrame to be updated."
                        },
                        "formatted_rows": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "description": "A dictionary representing a single correctly formatted row. Keys are column names and values are the new data for that column in the row.",
                                "additionalProperties": {
                                    "anyOf": [
                                        {"type": "string"},
                                        {"type": "number"},
                                        {"type": "boolean"},
                                        {"type": "null"}
                                    ]
                                }
                            },
                            "description": "A list of dictionaries. Each dictionary contains key-value pairs where keys are column names and values are the new data to apply to a corresponding row in the specified range. The first dictionary in this list will be applied to row 'i', the second to 'i+1', and so on."
                        }
                    },
                    "required": ["i", "j", "formatted_rows"]
                }
            }
        }
    ]

    # Faz a chamada inicial para o modelo
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",  
        messages=messages,  
        stream=False,
        tools=tools,  
        tool_choice="auto", 
        max_completion_tokens=4096,  
    )
    
    # Extrai a resposta e as chamadas de tools
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        # Define as funções disponíveis para serem chamadas
        available_functions = {
            "standardize_column_names": standardize_column_names,
            "normalize_df": normalize_df
        }

        messages.append(response_message)
        # print(tool_calls)
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)

            # Add the DataFrame to the tool arguments
            if function_name == "standardize_column_names":
                function_args["df"] = df

            if function_name == "normalize_df":
                function_args["df"] = df

            df = function_to_call.invoke(function_args)  

        return df  
    
if __name__ == "__main__":
    file_paths = load_file_paths.invoke({"directory": ROOT_DIR})
    dfs = dict()

    renamePrompt = """
    You are a column Standardization Specialist. Your primary responsibility is to identify and standardize key column names within a DataFrame,
    based solely on the provided list of existing column names.

    Given the following list of column names from a DataFrame:
    {COLUMN_NAMES_LIST}

    Your task is to precisely identify three critical columns from this list:

    1.  **Employee Document Column**: Identify the column name that represents the employee's unique identifier (e.g., 'CPF', 'Documento Funcionario', 'Employee ID'). You **must** indicate that this column should be renamed to **'CPF'**.
    2.  **Name Column**: Identify the column name that contains the employee's name (e.g., 'Nome', 'Employee Name', 'Colaborador'). You **must** indicate that this column should be renamed to **'Nome'**.
    3.  **Monthly Spent Column**: Identify the column name that represents the total monthly cost or expenditure (e.g., 'Custo Mensal', 'Valor Mensal', 'Total Gasto', 'Gastos', 'Monthly Cost'). You **must** indicate that this column should be renamed to **{FILE_NAME}**.

    It is **guaranteed** that the name column, employee document column and the monthly spent column will always be present in the provided list of column names, although their current names will vary.
    """
    
    normalizePrompt = """
    You are a highly skilled Data Standardization Specialist. Your critical mission is to ensure the provided DataFrame
    adheres to strict formatting standards for key columns. Assume the DataFrame's columns are already correctly named ('CPF', 'Nome', and '{LAST_COLUMN}').

    **Task 1: Standardize 'CPF' Column**

    **Target CPF Format:**
    The 'CPF' column must be a string formatted precisely as `'XXX.XXX.XXX-DD'`, where 'X' and 'D' represent a single digit
    from 0 to 9. This means it should always have 11 digits, with dots after the 3rd and 6th digits, and a hyphen before the
    last two digits.

    **Task 2: Normalize the {LAST_COLUMN}**

    **Target {LAST_COLUMN} Format:**
    The **{LAST_COLUMN}** of the DataFrame must be formatted as a **numeric value only**. This means:

    1.  Any currency symbols (e.g., 'R$', '$') must be removed.
    2.  Any **thousands separators** (e.g., commas ',') must be removed.
    3.  The column must then be converted to a suitable numeric data type (e.g., float).

    **Action:**
    You must normalize the data within the rows from index {i} to {j} (inclusive). For each of these rows,
    generate a dictionary that includes **ALL** columns present in the 'Columns' list below. For 'CPF' and
    '{LAST_COLUMN}', apply the specified target formats. For all other columns (like 'Nome'), their values should be included **as they are** from the original 'Must normalize the rows' data.

    Columns: {COLUMN_NAMES_LIST}
    Must normalize the rows {i} to {j}: {MUST_NORMALIZE}

    """
    
    for file in file_paths:
        df = pd.read_excel(file)
        
        if list(df.columns) == list(OUTPUT_DATA_FRAME.columns):
            continue  
        sheetName = file.split("/")[-1].split("-")[-1].replace(".xlsx", "")
        dfs[sheetName] = df  

    for file_name, df in dfs.items():
        new_df = run_agent(renamePrompt.format(COLUMN_NAMES_LIST=list(df.columns), FILE_NAME=file_name), df)

        i = 0
        for j in range(5, len(new_df), 5):
            normalized_df = run_agent(normalizePrompt.format(LAST_COLUMN=new_df.columns[-1], MUST_NORMALIZE=new_df.iloc[i:j], i=i, j=j-1, COLUMN_NAMES_LIST=list(new_df.columns)), new_df)
            i = j                                                                                                  
        OUTPUT_DATA_FRAME = pd.merge(OUTPUT_DATA_FRAME, normalized_df, on=['Nome', 'CPF'], how='left')
        print(f"Merged file: {file_name}")
        break


    OUTPUT_DATA_FRAME['Total'] = OUTPUT_DATA_FRAME.select_dtypes(include='number').sum(axis=1)
    OUTPUT_DATA_FRAME.to_excel(OUTPUT_PATH, index=False)


