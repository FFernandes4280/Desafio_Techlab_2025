import pandas as pd
import json
from dotenv import find_dotenv, load_dotenv
from groq import Groq

from tools.load_files import load_file_paths
from tools.classify_files import get_file_classification
from tools.get_relevant_columns import extract_and_append_data
from tools.standardize_files import standardize_column_names_by_content_comparison
from tools.consolidate_files import consolidate_data_and_generate_report

# --- Environment Setup ---
_ = load_dotenv(find_dotenv())

# --- Global Variables
ROOT_DIR = "Planilhas"
OUTPUT_PATH = "result.xlsx"
OUTPUT_DATA_FRAME = pd.DataFrame()

def run_agent(user_prompt):
    client = Groq()
    # Inicializa a conversa com mensagens do sistema e do usuário
    messages = [
        {
            "role": "system",
            "content": """You are a specialized automation agent. Your exclusive task is to 
            determine and execute the exact tool calls necessary to fulfill the user's request.
            **You must not generate any conversational text, greetings, summaries, or explanations.** 
            Respond solely with the appropriate tool calls or, if no tool is applicable or the task is complete, 
            indicate completion directly without additional prose."""
        },
        {
            "role": "user",
            "content": user_prompt,
        }
    ]

    # Define as tools disponíveis
    tools = [
        {
            "type": "function",
            "function": {
                "name": "load_file_paths",
                "description": "Scan a directory for .xlsx files and return their paths.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "The directory to scan for .xlsx files.",
                        }
                    },
                    "required": ["directory"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_file_classification",
                "description": "Classify a file as 'employee', 'tool', or 'benefit' based on its content or name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to classify.",
                        }
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "extract_and_append_data",
                "description": "Extract relevant columns from a file based on its classification and append to the output DataFrame.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to process.",
                        },
                        "file_classification": {
                            "type": "string",
                            "description": "The classification of the file (e.g., 'employee', 'tool', 'benefit').",
                        }
                    },
                    "required": ["file_path", "file_classification"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "standardize_column_names_by_content_comparison",
                "description": "Standardize column names of DataFrames by comparing them with a master DataFrame.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "classified_files": {
                            "type": "object",
                            "description": "A dictionary of file paths and their classifications.",
                        }
                    },
                    "required": ["classified_files"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "consolidate_data_and_generate_report",
                "description": "Consolidate standardized DataFrames into a single report.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "standardized_files": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string"},
                                    "classification": {"type": "string"},
                                    "dataframe": {"type": "object"},
                                },
                            },
                            "description": "A list of tuples containing file paths, classifications, and DataFrames.",
                        }
                    },
                    "required": ["standardized_files"],
                },
            },
        },
    ]

    # Faz a chamada inicial para o modelo
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",  
        messages=messages,  # Histórico da conversa
        stream=False,
        tools=tools,  # Tools disponíveis
        tool_choice="auto",  # Permite ao modelo decidir qual tool usar
        max_completion_tokens=4096,  # Limite de tokens
    )

    # Extrai a resposta e as chamadas de tools
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        # Define as funções disponíveis para serem chamadas
        available_functions = {
            "load_file_paths": load_file_paths,
            "get_file_classification": get_file_classification,
            "extract_and_append_data": extract_and_append_data,
            "standardize_column_names_by_content_comparison": standardize_column_names_by_content_comparison,
            "consolidate_data_and_generate_report": consolidate_data_and_generate_report,
        }

        # Adiciona a resposta do modelo à conversa
        messages.append(response_message)

        # Processa cada chamada de tool
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)

            # Chama a tool usando invoke e obtém a resposta
            function_response = function_to_call.invoke(function_args)

            # Adiciona a resposta da tool à conversa
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response),
                }
            )

        # Faz uma segunda chamada ao modelo com a conversa atualizada
        second_response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
        )

        # Retorna a resposta final
        return second_response.choices[0].message.content

    # Retorna a resposta inicial se nenhuma tool foi chamada
    return response_message.content

if __name__ == "__main__":
    file_paths = load_file_paths.invoke({"directory": ROOT_DIR})

    for file in file_paths:
        user_prompt = f"""
        Please process the file: {file}.
        **Important**: When referring to or passing file paths to tools, **do not modify them in any way, including removing spaces or special characters**. The file paths must be used exactly as provided.

        Follow these steps:
        1.  **Classification**: Determine the primary category or type of data within the file.
        2. **Get relevant columns**: Identify the relevant columns in the file that are necessary for further processing.
        """
        print(run_agent(user_prompt))
        print(OUTPUT_DATA_FRAME)


