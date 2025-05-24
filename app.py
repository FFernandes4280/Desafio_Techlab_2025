import os
import pandas as pd
from dotenv import find_dotenv, load_dotenv
from groq import Groq

_ = load_dotenv(find_dotenv())
api_key = os.getenv("GROQ_TOKEN")

client = Groq(
    api_key=api_key,
)

class FileInput:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.files = []

    def load_files(self):

        for dirpath, filenames in os.walk(self.root_dir):
            for filename in filenames:
                if filename.endswith(".xlsx"):
                    full_path = os.path.join(dirpath, filename)
                    csv_content = self._read_and_convert_to_csv(full_path)
                    if csv_content:  
                        self.files.append(csv_content)

    def _read_and_convert_to_csv(self, filepath):
        try:
            df = pd.read_excel(filepath)
            csv_content = df.to_csv(index=False)
            return csv_content
        except Exception as e:
            print(f"[Erro] Não foi possível processar o arquivo {filepath}: {e}")
            return None

    def get_files(self):
        return self.files

# class FileClassifier:


class Agent:
    def __init__(self, client, model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=1, max_tokens=1024, top_p=1, stream=True, stop=None):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.stream = stream
        self.stop = stop

    def create_completion(self, messages):
        try:
            response = ""
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_completion_tokens=self.max_tokens,
                top_p=self.top_p,
                stream=self.stream,
                stop=self.stop,
            )

            for chunk in completion:
                delta_content = chunk.choices[0].delta.content or ""
                response += delta_content
                print(delta_content, end="")  
            return response
        except Exception as e:
            print(f"[Erro] Não foi possível criar a conclusão: {e}")
            return None

    def generate_response_with_context(self, context, instruction):
        messages = [
            {"role": "system", "content": "Você é um assistente útil."},
            {"role": "user", "content": context},
            {"role": "user", "content": instruction},
        ]
        return self.create_completion(messages)
    
# Inicializa a classe com o diretório raiz
file_input = FileInput("Planilhas")

# Carrega os arquivos
file_input.load_files()

# Obtém os dados
arquivos_validos = file_input.get_files()

agent = Agent(client)

# Contexto e instrução
context = arquivos_validos[0]
instruction = "Me dê todos os dados de adolfo moreira."

# Gera a resposta
response = agent.generate_response_with_context(context, instruction)

# Exibe a resposta
print(response)