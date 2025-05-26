import os
import pandas as pd
from dotenv import find_dotenv, load_dotenv
from groq import Groq

_ = load_dotenv(find_dotenv())
api_key = os.getenv("GROQ_TOKEN")

client = Groq(
    api_key=api_key,
)

def create_context_body(dataframes):
    documents = []
    for name, df in dataframes:
        for column in df.columns:
            column_data = f"Arquivo: {name}\nColuna: {column}\nDados: {df[column].dropna().tolist()}"
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
                    file_name, df = self._read_excel(full_path)
                    if df is not None:
                        self.files.append((file_name, df))

    def _read_excel(self, filepath):
        try:
            df = pd.read_excel(filepath)
            file_name = os.path.splitext(os.path.basename(filepath))[0]  
            return file_name, df
        except Exception as e:
            print(f"[Erro] Não foi possível processar o arquivo {filepath}: {e}")
            return None, None

    def get_files(self):
        return self.files

class FileClassifier:
    def __init__(self, agent, file_input):
        self.agent = agent
        self.file_input = file_input
        self.instruction = ("...instruções da tarefa de classificação...")
        self.classified_files = []

    def classify_files(self):
        for file_name, df in self.file_input:
            try:
                header = ", ".join(df.columns)
                response = self.agent.generate_response_with_context(header, self.instruction)
                if response:
                    self.classified_files.append((file_name, response))
            except Exception as e:
                print(f"[Erro] Não foi possível classificar o arquivo: {e}")
        return self.classified_files

class Agent:
    def __init__(self, client, model="llama-3.3-70b-versatile", temperature=1, max_tokens=1024, top_p=1, stream=True, stop=None):
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

class ManageTable:
    def __init__(self, agent):
        self.agent = agent

    def define_columns(self, file_input):
        instruction = """
        Sua tarefa é selecionar colunas específicas de planilhas, seguindo exatamente as regras abaixo. Respeite com rigor as instruções e não inclua colunas que não sejam explicitamente solicitadas.

        ## 1. Para arquivos do tipo 'colaboradores':
        Selecione apenas colunas que correspondam aos seguintes campos (mesmo que com nomes diferentes ou sinônimos):
        - Nome (ex: "Nome", "Colaborador", "Funcionário", "Empregado")
        - CPF (ex: "CPF", "CPF do Colaborador")
        - Departamento (ex: "Departamento", "Área", "Setor")
        - Salário (ex: "Salário", "Remuneração", "Vencimentos", "Valor Bruto")

        ## 2. Para arquivos do tipo 'benefício' ou 'ferramenta':
        - Se existir uma coluna chamada ou semelhante a "Valor Total", "Valor Mensal", ou "Valor Total do Plano", selecione **somente essa**.
        - Caso **não** exista essa coluna, selecione **apenas** colunas numéricas que representem valores monetários, como:
        "Valor Mensal", "Valor Parcela", "Valor Desconto", "Custo", "Coparticipação", "Preço", "Parcela".

        ### MUITO IMPORTANTE:
        - **NÃO** inclua colunas como: "Assinante", "Licença", "Beneficiário", "Nome do Plano", "Copilot", ou qualquer outro campo que **não represente valor monetário**.
        - Nunca selecione mais de uma coluna de valor se houver uma chamada "Total" ou equivalente.
        - Se houver dúvida entre colunas de texto e de valor, **escolha somente as que claramente contêm valores numéricos em reais**.

        ## Exemplo de formato esperado:
        [
        ("Arquivo1", ["Coluna A", "Coluna B"]),
        ("Arquivo2", ["Coluna X"])
        ]

        Use **exatamente** os nomes dos arquivos (sem extensão) e **retorne somente a lista** nesse formato. Não inclua nenhuma explicação, título ou comentário.
        """
        documents = create_context_body(file_input)
        context = "\n\n".join(documents)
        response = self.agent.generate_response_with_context(
            context=context,
            instruction=instruction,
        )
        formatted_response = eval(response)
        return formatted_response


    def create_table(self, file_input, columns):
        combined_columns = {}
        columns_dict = dict(columns)

        for filename, df in file_input:
            try:
                if filename in columns_dict:
                    colunas_desejadas = columns_dict[filename]
                    colunas_validas = [col for col in colunas_desejadas if col in df.columns]
                    for col in colunas_validas:
                        if col not in combined_columns:
                            combined_columns[col] = []
                        combined_columns[col].extend(df[col].dropna().tolist())
            except Exception as e:
                print(f"[Erro] Falha ao processar o arquivo {filename}: {e}")

        if combined_columns:
            result_df = pd.DataFrame(dict([(col, pd.Series(data)) for col, data in combined_columns.items()]))

            column_to_file_map = {}
            for filename, df in file_input:
                if filename in columns_dict:
                    colunas_desejadas = columns_dict[filename]
                    colunas_validas = [col for col in colunas_desejadas if col in df.columns]
                    for col in colunas_validas:
                        if col not in columns_dict.get("Dados Colaboradores", []):
                            column_to_file_map[col] = filename

            result_df.rename(
                columns=lambda col: f"{column_to_file_map[col]}" if col in column_to_file_map else col,
                inplace=True
            )

            result_df['Total'] = result_df.select_dtypes(include='number').sum(axis=1)

            output_path = "result.xlsx"
            result_df.to_excel(output_path, index=False)
            return output_path
        else:
            print("[Aviso] Nenhum dado correspondente foi encontrado.")
            return None
    
file_input = FileInput("Planilhas")
file_input.load_files()
arquivos = file_input.get_files()

agent = Agent(client)
create_table = ManageTable(agent)
columns = create_table.define_columns(arquivos)

create_table.create_table(arquivos, columns)
