import os
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent 
from langchain_core.prompts import PromptTemplate
from langchain.tools import tool

# --- Environment Setup ---
_ = load_dotenv(find_dotenv())

# --- Global Variables 
ROOT_DIR = "Planilhas"
OUTPUT_PATH = "result.xlsx"

EMPLOYEE_COLS = {
    "ID Funcional": "ID_Colaborador",
    "Nome Completo": "Nome_Colaborador",
    "Nome": "Nome_Colaborador",
    "ID": "ID_Colaborador",
    "Matrícula": "ID_Colaborador",
    "Centro de Custo": "Centro_Custo",
    "Departamento": "Centro_Custo",
    "Área": "Centro_Custo"
}

SUM_COL_CANDIDATES = [
    "Valor Total", "Custo Total", "Valor Final", "Total Licença",
    "Custo", "Valor", "Preço", "Mensalidade", "Coparticipação", "Custo Individual"
]

KNOWN_TOOL_NAMES = [
    "copilot", "google workspace", "m365", "office 365", "excel", "word",
    "powerpoint", "outlook", "teams", "slack", "zoom", "jira", "azure",
    "aws", "github", "gitlab", "notion", "figma", "salesforce", "power bi",
    # Add other specific tool names your company uses
]

KNOWN_BENEFIT_NAMES = [
    "unimed", "bradesco saude", "amil", "sulamerica", "porto seguro saude", # Health
    "odontoprev", "bradesco dental", # Dental
    "vr", "va", "alelo", "sodexo", "ticket restaurante", "ticket alimentação", # Meal/Food Vouchers
    "gympass", "totalpass", "wellhub", # Fitness/Wellbeing
    "vale transporte", "vt", # Transportation
    "seguro de vida", "previdencia privada", # Other benefits
]

NAME_KEYWORDS = ["nome", "colaborador", "funcionário", "empregado", "name", "employee"]
CPF_KEYWORDS = ["cpf"] 
COST_CENTER_KEYWORDS = ["centro de custo", "departamento", "área", "setor", "cost center", "department"]

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest", 
    temperature=0.1,
    # convert_system_message_to_human=True # Sometimes useful for models not explicitly supporting system messages
)

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

@tool
def get_file_classification(file_path: str) -> str:
    """
    Classifies a file by first checking if it's an employee file
    based on its column structure. If not, it attempts to classify it as
    a 'tool' or 'benefit' based on keywords in its filename.

    Returns:
        str: Classification type ("employee", "tool", "benefit").
    """
    try:
        df = pd.read_excel(file_path, nrows=5) # Read only a few rows for efficiency
        df_columns_lower = [str(col).lower() for col in df.columns]

        found_name = False
        found_cpf = False
        found_cost_center = False

        for col_lower in df_columns_lower:
            if any(keyword in col_lower for keyword in NAME_KEYWORDS):
                found_name = True
            if any(keyword in col_lower for keyword in CPF_KEYWORDS):
                found_cpf = True
            if any(keyword in col_lower for keyword in COST_CENTER_KEYWORDS):
                found_cost_center = True
        
        if found_name and found_cpf and found_cost_center:
            print(f"[Info] File '{file_path}' classified as 'employee' by columns.")
            return "employee"

    except Exception as e:
        print(f"[Warning] Could not read or process columns for {file_path} during master file check: {e}")

    # --- Part 2: If not Employee Master by columns, try name-based classification for Tool/Benefit ---
    filename_lower = os.path.basename(file_path).lower()

    # Check for Known Tool Names
    for tool_name in KNOWN_TOOL_NAMES:
        if tool_name in filename_lower:
            print(f"[Info] File '{file_path}' classified as 'tool' by name.")
            return "tool"

    # Check for Known Benefit Names
    for benefit_name in KNOWN_BENEFIT_NAMES:
        if benefit_name in filename_lower:
            print(f"[Info] File '{file_path}' classified as 'benefit' by name.")
            return "benefit"

@tool
def standardize_column_names_by_content_comparison(
    classified_files: dict[str, str]
    ) -> tuple[str, str, pd.DataFrame]:
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
    for path, classification in classified_files.items():
        if classification == "employee":
            master_df = pd.read_excel(path)
            output_data.append((path, classification, master_df))
            break
    
    master_col_unique_sets = {
        col_name: set(master_df[col_name].dropna().astype(str))
        for col_name in master_df.columns
    }

    # 2. Iterate through other DataFrames to standardize their columns
    for path, classification in classified_files.items():
        if classification == "employee":
            
            continue 
        df_other = pd.read_excel(path)
        print(f"[Info] Standardizing columns for {classification}...")
        
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
            new_columns = {}
            processed_original_cols = set()

            for original_col, new_name_candidate in rename_map.items():
                current_col_data = df_other[original_col]
                if new_name_candidate in new_columns:
                    print(f"  '{path}': Conflict for target name '{new_name_candidate}'. Column '{original_col}' will keep its original name.")
                    if original_col not in new_columns: 
                         new_columns[original_col] = current_col_data
                else:
                    new_columns[new_name_candidate] = current_col_data
                processed_original_cols.add(original_col)

            for original_col in df_other.columns:
                if original_col not in processed_original_cols:
                    new_columns[original_col] = df_other[original_col]
            
            df_other = pd.DataFrame(new_columns) 
            print(f"  '{path}': Columns after standardization: {df_other.columns.tolist()}")

        output_data.append((path, classification, df_other))

    return output_data

@tool
def consolidate_data_and_generate_report(standardized_files: list[tuple[str, str, pd.DataFrame]]) -> None: # Modificado para retornar o DataFrame
    """
    Consolidates standardized DataFrames into a single report.
    The report includes:
    - Collaborators
    - Collaborator Documents
    - Collaborator cost center
    - Collaborator Salary
    - The mensal cost of each benefit and tool the collaborator uses
    - The total cost of each benefit and tool plus the salary of that collaborator
    """
    employee_dfs = []
    tool_dfs_data = []
    benefit_dfs_data = []

    for path, classification, df in standardized_files:
        if classification == 'employee':
            employee_dfs.append(df)
        elif classification == 'tool':
            tool_dfs_data.append((path, df)) 
        elif classification == 'benefit':
            benefit_dfs_data.append((path, df))

    # 1. Consolida o DataFrame principal de empregados
    master_df = pd.concat(employee_dfs, ignore_index=True)

    # 2. Mescla os DataFrames de ferramentas
    NOME_DA_COLUNA_ID = 'Nome'

    for i, (path_tool, df_tool) in enumerate(tool_dfs_data):
        if NOME_DA_COLUNA_ID not in df_tool.columns:
            print(f"Alerta: DataFrame de ferramenta {path_tool} não contém a coluna ID '{NOME_DA_COLUNA_ID}'. Pulando merge.")
            continue
        last_column_name = df_tool.columns[-1]
        columns_to_select_tool = list(set([NOME_DA_COLUNA_ID, last_column_name]))
        df_tool_subset = df_tool[columns_to_select_tool]
        df_tool_subset.rename(columns={last_column_name: Path(path_tool).stem}, inplace=True)
        master_df = pd.merge(master_df, df_tool_subset, on=NOME_DA_COLUNA_ID, how='left')

    # 3. Mescla os DataFrames de benefícios
    for i, (path_benefit, df_benefit) in enumerate(benefit_dfs_data):
        if NOME_DA_COLUNA_ID not in df_benefit.columns:
            print(f"Alerta: DataFrame de benefício {path_benefit} não contém a coluna ID '{NOME_DA_COLUNA_ID}'. Pulando merge.")
            continue
        last_column_name = df_benefit.columns[-1]
        columns_to_select_benefit = list(set([NOME_DA_COLUNA_ID, last_column_name]))
        df_benefit_subset = df_benefit[columns_to_select_benefit]
        df_benefit_subset.rename(columns={last_column_name: Path(path_benefit).stem}, inplace=True)
        master_df = pd.merge(master_df, df_benefit_subset, on=NOME_DA_COLUNA_ID, how='left')
    
    master_df['Total'] = master_df.select_dtypes(include=np.number).sum(axis=1)
    print("DataFrame consolidado:")
    print(master_df.head())

    master_df.to_excel(OUTPUT_PATH, index=False)       

def agent_pipeline():
    try:
        print("Step 1: Loading file paths...")
        all_files = load_file_paths.invoke({"directory": ROOT_DIR})        
        
        print("Step 2: Classifying files...")
        classified_files = {}
        for file in all_files:
            classification_result = get_file_classification.invoke({"file_path": file})
            classified_files[file] = classification_result

        print("Step 3: Standardizing column names by content comparison...")
        standardized_files = standardize_column_names_by_content_comparison.invoke({"classified_files": classified_files})

        print("Step 4: Consolidating data and generating report...")
        consolidate_data_and_generate_report.invoke({"standardized_files": standardized_files})

    except Exception as e:
        print(f"An error occurred in the pipeline: {e}")
        import traceback
        traceback.print_exc()

tools_list = [
    load_file_paths,
    get_file_classification,
    standardize_column_names_by_content_comparison,
    consolidate_data_and_generate_report
]

react_prompt_template_str = """
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}
"""

prompt = PromptTemplate.from_template(react_prompt_template_str)
agent = create_react_agent(llm, tools_list, prompt) 
agent_executor = AgentExecutor(agent=agent, tools=tools_list, verbose=True, handle_parsing_errors=True)

if __name__ == "__main__":
    agent_pipeline()