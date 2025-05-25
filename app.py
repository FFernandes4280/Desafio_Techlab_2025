import os
import pandas as pd
import io
from dotenv import find_dotenv, load_dotenv
from groq import Groq

_ = load_dotenv(find_dotenv())
api_key = os.getenv("GROQ_TOKEN")

client = Groq(
    api_key=api_key,
)

def create_context_body(csv_file):
    documents = []
    for file in csv_file:
        df = pd.read_csv(io.StringIO(file))
        for column in df.columns:
            column_data = f"Coluna: {column}\nDados: {df[column].dropna().tolist()}"
            documents.append(column_data)
    return documents

class FileInput:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.files = []

    def load_files(self):
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            for filename in filenames:
                if filename.endswith(".xlsx"):
                    full_path = os.path.join(dirpath, filename)
                    csv_content = self._read_and_convert_to_csv(full_path)
                    if csv_content:
                        self.files.append(csv_content)
        return self.files

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

class FileClassifier:
    def __init__(self, agent, file_input):
        self.agent = agent
        self.file_input = file_input
        self.instruction = (
            "Sua tarefa é classificar arquivos de planilha com base nos nomes das colunas fornecidas. "
            "Você deve escolher exatamente uma das seguintes categorias para cada planilha:\n\n"
            "1. 'colaboradores': colunas relacionadas a pessoas e suas funções na empresa, como 'Departamento', 'Colaborador', 'Cargo', 'Salário', 'Centro de Custo', 'Matrícula'.\n"
            "2. 'beneficios': colunas associadas a planos de saúde, vales e coparticipações, como 'Beneficiário', 'Plano', 'Coparticipação', 'Dependentes', "
            "'Valor Parcela Assinante', 'Valor Desconto Coparticipação', 'Data de Início'.\n"
            "3. 'ferramentas': colunas relacionadas ao uso de softwares ou licenças, como 'Ferramenta', 'Licença', 'Usuário', 'Data Ativação', 'Valor Mensal', 'Produto', 'Assinatura'.\n\n"
            "Importante: apenas **uma única** planilha deve ser classificada como 'colaboradores'. "
            "Todas as outras planilhas devem ser classificadas como 'beneficios', 'ferramentas' ou 'Outros'.\n\n"
            "Se uma planilha contiver termos que aparecem em mais de uma categoria, escolha aquela cujo **conjunto de colunas predominantes for mais claramente associado**.\n"
            "Se nenhuma categoria for adequada, retorne 'Outros'.\n\n"
            "Retorne **apenas o nome da categoria**: 'colaboradores', 'beneficios', 'ferramentas' ou 'Outros'. "
            "Não explique sua decisão nem inclua nenhum outro texto além da categoria."
        )
        self.classified_files = []

    def classify_files(self):
        for file in self.file_input:
            try:
                header = file.split("\n")[0]
                response = self.agent.generate_response_with_context(header, self.instruction)
                if response:
                    self.classified_files.append((header, response))
            except Exception as e:
                print(f"[Erro] Não foi possível classificar o arquivo: {e}")
        return self.classified_files

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
            print(response)
            return response
        except Exception as e:
            print(f"[Erro] Não foi possível criar a conclusão: {e}")
            return None

    def generate_response_with_context(self, context, instruction):
        messages = [
            {"role": "system", "content": "Você é um assistente útil."},
            {"role": "user", "content": f"{instruction}\n\n{context}"},
        ]
        return self.create_completion(messages)

class CreateTable:
    def __init__(self, agent):
        self.agent = agent

    def define_columns(self, file_input):
        instruction = """
        Você receberá um conjunto de colunas de uma ou mais planilhas. Sua tarefa é identificar e retornar **apenas as colunas relevantes e não repetidas**.

        Siga estas regras:
        1. Se duas colunas tiverem nomes diferentes, mas os mesmos dados, mantenha apenas **uma** delas.
        2. Se duas colunas tiverem o mesmo nome e os mesmos dados, mantenha apenas **uma**.
        3. Remova colunas que sejam identificadores exclusivos, como: 'CNPJ', 'ID', 'Código', ou similares.
        4. **Exceção**: mantenha a coluna 'CPF', mesmo que seja um identificador.
        5. Retorne todas as colunas que não se repetem ou que contenham dados distintos, exceto os identificadores.

        Retorne apenas a lista final de colunas selecionadas, sem explicações.
        """
        documents = create_context_body(file_input)
        context = "\n\n".join(documents)
        return self.agent.generate_response_with_context(
            context=context,
            instruction=instruction,
        )

file_input = FileInput("Planilhas")
arquivos = file_input.load_files()
agent = Agent(client)
create_table = CreateTable(agent)
create_table.define_columns(arquivos)
