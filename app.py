import pandas as pd
import json
from dotenv import find_dotenv, load_dotenv
from groq import Groq
import os

from tools.load_files import load_file_paths
from tools.standardize_files import standardize_column_names
from tools.normalize_df import normalize_df

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document 
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

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

def get_embedding_model():
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    model_kwargs = {'device': 'cpu'} 
    encode_kwargs = {'normalize_embeddings': False} 

    embedding_model = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    return embedding_model

def create_retriever_from_excel(file_path: str):
    df = pd.read_excel(file_path)

    documents = []
    for index, row in df.iterrows():

        content = f"Funcionário: {row['Nome']}, CPF: {row['CPF']}"
        
        for col in df.columns:
            if col not in ['Nome', 'CPF']: 
                content += f", {col}: {row[col]}"
        
        metadata = row.to_dict()
        
        documents.append(Document(page_content=content, metadata=metadata))

    embeddings = get_embedding_model()

    print("Creating vector store for result.xlsx...")
    vectorstore = FAISS.from_documents(documents, embeddings)
    print("Vector store created.")

    return vectorstore.as_retriever()
  
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
    
    normalizeCPFPrompt = """
    You are a highly skilled Data Standardization Specialist. Your critical mission is to ensure the provided DataFrame
    adheres to strict formatting standards for key columns. Assume the DataFrame's columns are already correctly named
    ('CPF', 'Nome', and '{LAST_COLUMN}').

    **Standardize 'CPF' Column**

    **Target CPF Format:**
    The 'CPF' column must be a string formatted precisely as `'DDD.DDD.DDD-XX'`.
    Here's what each part means:
    * 'D' represents a single **digit from 0 to 9**.
    * 'X' represents the **literal uppercase letter 'X'**.
    * The CPF must always have exactly **11 characters (9 digits + 2 'X's)**.
    * It must include **dots** after the 3rd and 6th digits.
    * It must include a **hyphen** before the last two 'X's.
    * **Crucial Rule:** If the original last two characters are numeric or any other placeholder (e.g., '01', 'AB'), they **MUST be replaced with 'XX'**.

    **Example:**
    * `'12345678901'` becomes `'123.456.789-XX'`
    * `'987.654.321-AB'` becomes `'987.654.321-XX'`
    * `'001.002.003-XX'` remains `'001.002.003-XX'`

    **Action:**
    You must normalize the data within the rows from index {i} to {j} (inclusive). For each of these rows,
    generate a dictionary for 'CPF' applying the specified target format.

    Columns: {COLUMN_NAMES_LIST}
    Must normalize the rows {i} to {j}: {MUST_NORMALIZE}
    """
    
    for file in file_paths:
        df = pd.read_excel(file)
        
        if list(df.columns) == list(OUTPUT_DATA_FRAME.columns):
            continue  
        sheetName = file.split("/")[-1].split("-")[-1].replace(".xlsx", "")
        dfs[sheetName] = df  

    for file_name, df_to_process in dfs.items(): 
        # Step 1: Standardize column names for the current file's DataFrame
        new_df = run_agent(renamePrompt.format(COLUMN_NAMES_LIST=list(df_to_process.columns), FILE_NAME=file_name), df_to_process)
        
        print(f"\n--- Starting Normalization for '{file_name}' ---")
        
        # Step 2: Normalize data in batches for new_df
        current_i = 0
        batch_size = 5 
        
        while current_i < len(new_df):
            current_j = min(current_i + batch_size, len(new_df)) 
            
            current_batch_df = new_df.iloc[current_i:current_j]
            num_rows_in_batch = len(current_batch_df)

            if num_rows_in_batch == 0:
                break 
            
            normalized_df_result_of_batch = run_agent(
                normalizeCPFPrompt.format(
                    LAST_COLUMN=new_df.columns[-1],
                    MUST_NORMALIZE=current_batch_df, 
                    i=current_i,
                    j=current_j-1, 
                    COLUMN_NAMES_LIST=list(new_df.columns),
                    num_rows_in_batch=num_rows_in_batch 
                ),
                new_df 
            )
            
            # Update current_i for the next batch
            new_df = normalized_df_result_of_batch
            current_i = current_j
            
        new_df.to_excel('debug'+file_name+'.xlsx', index=False)
        OUTPUT_DATA_FRAME = pd.merge(OUTPUT_DATA_FRAME, new_df, on=['Nome', 'CPF'], how='left')
        print(f"Merged file: {file_name}")


    # Final calculation and save after all files are processed and merged
    OUTPUT_DATA_FRAME['Total'] = OUTPUT_DATA_FRAME.select_dtypes(include='number').sum(axis=1)
    OUTPUT_DATA_FRAME.to_excel(OUTPUT_PATH, index=False)

    print("\n--- Iniciando Chatbot ---")
    
    retriever = create_retriever_from_excel(OUTPUT_PATH)

    # Define the LLM for the chatbot
    llm = ChatGroq(temperature=0.0, model_name="llama3-8b-8192", groq_api_key=os.environ.get("GROQ_API_KEY"))

    # Define the prompt for the conversational retrieval chain
    template = """Você é um assistente útil que responde a perguntas sobre dados de funcionários com base no contexto fornecido.
    Se você não souber a resposta, apenas diga que não sabe, não tente inventar uma resposta.
    Responda em Português.

    Contexto: {context}

    Pergunta: {question}"""

    prompt = ChatPromptTemplate.from_template(template)

    qa_chain = ConversationalRetrievalChain.from_llm(
        llm,
        retriever,
        chain_type="stuff",
        verbose=False, 
        return_source_documents=True,
        combine_docs_chain_kwargs={"prompt": prompt}
    )

    print("Chatbot iniciado. Faça perguntas sobre os dados (digite 'sair' para encerrar).")
    chat_history = []

    while True:
        user_query = input("Você: ")
        if user_query.lower() == 'sair':
            print("Até logo!")
            break

        try:
            result = qa_chain.invoke({"question": user_query, "chat_history": chat_history})
            print(f"Bot: {result['answer']}")
            chat_history.append((user_query, result['answer']))
        except Exception as e:
            print(f"Ocorreu um erro ao processar sua pergunta: {e}")
            print("Por favor, tente novamente.")

