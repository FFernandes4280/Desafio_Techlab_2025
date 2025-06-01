import pandas as pd
import json
from dotenv import find_dotenv, load_dotenv
from groq import Groq

from tools.load_files import load_file_paths
from tools.standardize_files import standardize_column_names

# --- Environment Setup ---
_ = load_dotenv(find_dotenv())

# --- Global Variables
ROOT_DIR = "Planilhas"
OUTPUT_PATH = "result.xlsx"
OUTPUT_DATA_FRAME = pd.read_excel("Planilhas/Dados Colaboradores.xlsx")

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

            df = function_to_call.invoke(function_args)  

        return df  
    
if __name__ == "__main__":
    file_paths = load_file_paths.invoke({"directory": ROOT_DIR})
    dfs = dict()

    renamePrompt = """
    You are a Data Standardization Specialist. Your primary responsibility is to identify and standardize key column names within a DataFrame,
    based solely on the provided list of existing column names.

    Given the following list of column names from a DataFrame:
    {COLUMN_NAMES_LIST}

    Your task is to precisely identify three critical columns from this list:

    1.  **Employee Document Column**: Identify the column name that represents the employee's unique identifier (e.g., 'CPF', 'Documento Funcionario', 'Employee ID'). You **must** indicate that this column should be renamed to **'CPF'**.
    2.  **Monthly Spent Column**: Identify the column name that represents the total monthly cost or expenditure (e.g., 'Custo Mensal', 'Valor Mensal', 'Total Gasto', 'Gastos', 'Monthly Cost'). You **must** indicate that this column should be renamed to **{FILE_NAME}**.
    3.  **Name Column**: Identify the column name that contains the employee's name (e.g., 'Nome', 'Employee Name', 'Colaborador'). You **must** indicate that this column should be renamed to **'Nome'**.

    It is **guaranteed** that the name column, employee document column and the monthly spent column will always be present in the provided list of column names, although their current names will vary.
    """
    
    normalizePrompt = """

    """
    for file in file_paths:
        df = pd.read_excel(file)
        
        if list(df.columns) == list(OUTPUT_DATA_FRAME.columns):
            continue  
        sheetName = file.split("/")[-1].split("-")[-1].replace(".xlsx", "")
        dfs[sheetName] = df  

    for file_name, df in dfs.items():
        new_df = run_agent(renamePrompt.format(COLUMN_NAMES_LIST=list(df.columns), FILE_NAME=file_name), df)
        normalized_df = new_df

        OUTPUT_DATA_FRAME = pd.merge(OUTPUT_DATA_FRAME, normalized_df, on=['Nome', 'CPF'], how='left')

    OUTPUT_DATA_FRAME['Total'] = OUTPUT_DATA_FRAME.select_dtypes(include='number').sum(axis=1)
    OUTPUT_DATA_FRAME.to_excel(OUTPUT_PATH, index=False)


