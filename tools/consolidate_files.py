from pathlib import Path
import pandas as pd
from langchain.tools import tool

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

NAME_KEYWORDS = ["nome", "colaborador", "funcionário", "empregado", "name", "employee"]
CPF_KEYWORDS = ["cpf"] 
COST_CENTER_KEYWORDS = ["centro de custo", "departamento", "área", "setor", "cost center", "department"]

SUM_COL_CANDIDATES = [
    "Valor Total", "Custo Total", "Valor Final", "Total Licença",
    "Custo", "Valor", "Preço", "Mensalidade", "Coparticipação", "Custo Individual"
]

OUTPUT_PATH = "result.xlsx"

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
    if not employee_dfs:
        raise ValueError("No employee data found to consolidate.")
    master_df = pd.concat(employee_dfs, ignore_index=True)

    # Padroniza a coluna 'Nome' para o merge
    NOME_DA_COLUNA_ID = 'Nome_Colaborador' # Usando a coluna padronizada

    # Renomear as colunas do master_df para os nomes padronizados
    master_df.rename(columns=EMPLOYEE_COLS, inplace=True)
    if NOME_DA_COLUNA_ID not in master_df.columns:
        # Tenta inferir o nome da coluna de nome, caso não esteja explicitamente mapeado
        for col_name in master_df.columns:
            if any(keyword in str(col_name).lower() for keyword in NAME_KEYWORDS):
                master_df.rename(columns={col_name: NOME_DA_COLUNA_ID}, inplace=True)
                print(f"Renomeado '{col_name}' para '{NOME_DA_COLUNA_ID}' no master_df.")
                break
    if NOME_DA_COLUNA_ID not in master_df.columns:
        raise ValueError(f"A coluna de ID '{NOME_DA_COLUNA_ID}' não foi encontrada no DataFrame principal após padronização.")


    # 2. Mescla os DataFrames de ferramentas
    for i, (path_tool, df_tool) in enumerate(tool_dfs_data):
        # Tenta encontrar a coluna de nome padronizada ou inferir
        tool_id_col = None
        for col_name in df_tool.columns:
            if any(keyword in str(col_name).lower() for keyword in NAME_KEYWORDS):
                tool_id_col = col_name
                break
        if tool_id_col is None:
            print(f"Alerta: DataFrame de ferramenta {path_tool} não contém uma coluna de nome reconhecível. Pulando merge.")
            continue

        sum_col = None
        for candidate in SUM_COL_CANDIDATES:
            if candidate in df_tool.columns:
                sum_col = candidate
                break

        if sum_col is None:
            print(f"Alerta: DataFrame de ferramenta {path_tool} não contém uma coluna de valor reconhecível. Pulando merge.")
            continue

        columns_to_select_tool = list(set([tool_id_col, sum_col]))
        df_tool_subset = df_tool[columns_to_select_tool].copy() # Use .copy() to avoid SettingWithCopyWarning
        df_tool_subset.rename(columns={tool_id_col: NOME_DA_COLUNA_ID, sum_col: Path(path_tool).stem}, inplace=True)
        master_df = pd.merge(master_df, df_tool_subset, on=NOME_DA_COLUNA_ID, how='left')

    # 3. Mescla os DataFrames de benefícios
    for i, (path_benefit, df_benefit) in enumerate(benefit_dfs_data):
        # Tenta encontrar a coluna de nome padronizada ou inferir
        benefit_id_col = None
        for col_name in df_benefit.columns:
            if any(keyword in str(col_name).lower() for keyword in NAME_KEYWORDS):
                benefit_id_col = col_name
                break
        if benefit_id_col is None:
            print(f"Alerta: DataFrame de benefício {path_benefit} não contém uma coluna de nome reconhecível. Pulando merge.")
            continue

        sum_col = None
        for candidate in SUM_COL_CANDIDATES:
            if candidate in df_benefit.columns:
                sum_col = candidate
                break

        if sum_col is None:
            print(f"Alerta: DataFrame de benefício {path_benefit} não contém uma coluna de valor reconhecível. Pulando merge.")
            continue

        columns_to_select_benefit = list(set([benefit_id_col, sum_col]))
        df_benefit_subset = df_benefit[columns_to_select_benefit].copy() # Use .copy() to avoid SettingWithCopyWarning
        df_benefit_subset.rename(columns={benefit_id_col: NOME_DA_COLUNA_ID, sum_col: Path(path_benefit).stem}, inplace=True)
        master_df = pd.merge(master_df, df_benefit_subset, on=NOME_DA_COLUNA_ID, how='left')

    # Calculate Total Cost
    # Identify numeric columns for summation, excluding ID_Colaborador, CPF_Colaborador, Centro_Custo
    numeric_cols_for_sum = [col for col in master_df.columns if pd.api.types.is_numeric_dtype(master_df[col]) and col not in ['ID_Colaborador', 'CPF_Colaborador']]
    master_df['Total'] = master_df[numeric_cols_for_sum].sum(axis=1, skipna=True)


    print("DataFrame consolidado:")
    print(master_df.head())

    master_df.to_excel(OUTPUT_PATH, index=False)
    print(f"Relatório gerado em: {OUTPUT_PATH}")
