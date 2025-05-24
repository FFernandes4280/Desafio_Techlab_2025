import os
import pandas as pd
import gradio as gr
from dotenv import load_dotenv, find_dotenv
from huggingface_hub import InferenceClient
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# ==== Setup ====
_ = load_dotenv(find_dotenv())
api_key = os.getenv("HF_API_TOKEN")

client = InferenceClient(
    provider="hf-inference",
    api_key=api_key,
)

# ==== Embeddings e FAISS ====
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
dimension = 384  # Dimensão dos embeddings do modelo MiniLM
faiss_index = faiss.IndexFlatL2(dimension)
metadata_store = []  # Lista paralela para armazenar metadados dos vetores

def embed_text(text):
    return embedding_model.encode([text])[0]  # retorna um vetor 1D

# ==== Manipulação de arquivos ====
class FileInput:
    def __init__(self, allowed_extensions=None):
        self.allowed_extensions = allowed_extensions or [".xlsx"]
        self.valid_files = []

    def is_valid_extension(self, filename):
        return any(filename.endswith(ext) for ext in self.allowed_extensions)

    def validate_file(self, filepath):
        try:
            pd.read_excel(filepath, nrows=1)
            return True
        except Exception as e:
            print(f"[Error] Unable to read {filepath}: {str(e)}")
            return False

    def list_all_files_recursively(self, root_dir):
        all_files = []
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                all_files.append(full_path)
        return all_files

    def index_by_row(self, df, source_name):
        for i, row in df.iterrows():
            pessoa = row.get("Nome", f"Linha {i}")
            atributos = []
            for col, val in row.items():
                atributos.append(f"{col}: {val}")
            text = f"Registro de {pessoa} - " + "; ".join(atributos)
            vec = embed_text(text)
            faiss_index.add(np.array([vec]))
            metadata_store.append({
                "tipo": "linha",
                "pessoa": pessoa,
                "fonte": source_name,
                "conteudo": text
            })

    def index_numerical_stats(self, df, source_name):
        numeric_df = df.select_dtypes(include=["number"])
        for col in numeric_df.columns:
            col_data = numeric_df[col].dropna()
            if col_data.empty:
                continue
            stats_text = (
                f"A coluna '{col}' na fonte '{source_name}' possui:\n"
                f"- Média: {col_data.mean():.2f}\n"
                f"- Máximo: {col_data.max():.2f}\n"
                f"- Mínimo: {col_data.min():.2f}\n"
                f"- Soma: {col_data.sum():.2f}\n"
                f"- Total de registros: {len(col_data)}"
            )
            vec = embed_text(stats_text)
            faiss_index.add(np.array([vec]))
            metadata_store.append({
                "tipo": "estatística",
                "coluna": col,
                "fonte": source_name,
                "conteudo": stats_text
            })

    def load_files(self, input_paths):
        files = []

        if isinstance(input_paths, str) and os.path.isdir(input_paths):
            all_files = self.list_all_files_recursively(input_paths)
        elif isinstance(input_paths, list):
            all_files = []
            for path in input_paths:
                if os.path.isdir(path):
                    all_files.extend(self.list_all_files_recursively(path))
                else:
                    all_files.append(path)
        else:
            raise ValueError("Invalid input: provide a directory or a list of files.")

        for filepath in all_files:
            if not self.is_valid_extension(filepath):
                print(f"[Warning] Ignored (unsupported extension): {filepath}")
                continue
            if not os.path.exists(filepath):
                print(f"[Warning] File not found: {filepath}")
                continue
            if self.validate_file(filepath):
                try:
                    df = pd.read_excel(filepath)
                    csv_content = df.to_csv(index=False)
                    files.append({
                        "filename": os.path.basename(filepath),
                        "content": csv_content
                    })

                    # Indexar por linha e estatísticas numéricas
                    self.index_by_row(df, os.path.basename(filepath))
                    self.index_numerical_stats(df, os.path.basename(filepath))
                except Exception as e:
                    print(f"[Error] Failed to process {filepath}: {str(e)}")

        self.valid_files = files
        return files

# ==== Carregar dados ====
data = FileInput()
arquivos_validos = data.load_files("Planilhas")

# ==== Consulta ao modelo ====
def query_model(context, question):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Context: {context}\nQuestion: {question}"}
    ]
    completion = client.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct",
        messages=messages,
    )
    return completion.choices[0].message["content"]

# ==== Função principal ====
def responder(question):
    try:
        question_vec = embed_text(question)
        D, I = faiss_index.search(np.array([question_vec]), k=5)  # top 5 matches
        context_chunks = [metadata_store[i]["conteudo"] for i in I[0] if i < len(metadata_store)]
        context = "\n".join(context_chunks)
        print("Context:", context)
        response = query_model(context, question)
        return response
    except Exception as e:
        return f"[Error] {str(e)}"

# ==== Interface Gradio ====
iface = gr.Interface(
    fn=responder,
    inputs=gr.Textbox(lines=2, placeholder="Digite sua pergunta sobre os dados..."),
    outputs="text",
    title="Chat com Dados Excel usando RAG + FAISS",
    description="Use um modelo LLM gratuito para consultar dados de planilhas (.xlsx)."
)

iface.launch()
