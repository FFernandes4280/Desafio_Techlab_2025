# Agente para Alocação de Custos de Ferramentas

## 📌 Visão Geral do Projeto

Este projeto foi desenvolvido como parte do desafio **TechLab 2025**. A proposta consistia na criação de um **agente inteligente** capaz de:

- Receber diversas planilhas externas com informações de custos de ferramentas e benefícios;
- Padronizar, normalizar e integrar esses dados à **planilha principal de colaboradores** da empresa;
- Permitir a análise conversacional dos resultados por meio de um chatbot intuitivo.

O sistema automatiza tarefas de pré-processamento de dados, realizando desde a leitura de arquivos até a transformação e fusão de planilhas. Ao final, o usuário pode interagir com os dados por meio de perguntas em linguagem natural.

---

## 🎯 Desafios Abordados e Soluções Implementadas

### 🔧 1. Orquestração Inteligente de LLMs e Tools

**Desafio**: Usar um modelo de linguagem (LLM) para **selecionar e acionar ferramentas Python externas** de maneira autônoma, com decisões contextuais sobre qual usar e quando.

**Solução**:

- Foram criadas ferramentas (`@tool` via LangChain) específicas para manipulação de `DataFrames`, como: ler arquivos, renomear colunas e padronizar CPFs.
- A **LLaMA 4 (llama-4-scout-17b-16e-instruct)** foi utilizada por sua capacidade de **compreensão contextual avançada**, sendo a responsável por tomar decisões complexas, encadear chamadas de ferramentas e lidar com fluxos longos de raciocínio.
- O modelo é guiado por **prompts otimizados**, que descrevem o funcionamento e o objetivo de cada ferramenta, permitindo que ele forneça argumentos corretos mesmo em chamadas compostas.

> Referência: [GROQ Tool Use Documentation](https://console.groq.com/docs/tool-use)

---

### 📥 2. Coleta Abrangente de Dados

**Desafio**: Detectar automaticamente todas as planilhas em um diretório e subdiretórios, sem omitir arquivos importantes.

**Solução**:

- Criação de uma ferramenta para escanear todos os arquivos `.xlsx` em diretórios e subpastas usando `os.walk`.
- A leitura é feita de forma manual e sequencial, permitindo que o LLM processe um `DataFrame` por vez — garantindo maior controle e precisão na análise.

---

### 📑 3. Padronização de Nomes de Colunas

**Desafio**: Padronizar colunas com nomes diferentes que representam a mesma informação.

**Solução**:

- Inicialmente foi desenvolvida uma função padrão para receber um nome atual e um nome que deve ser alterado, posteriormente foi criado um prompt e uma tool description para que o LLM fosse capaz de chamar essa tool por conta propria com os parâmetros corretos.
- A LLaMA 4 utiliza essa `@tool`, escolhendo os nomes corretos com base em um **prompt que define equivalências** (ex: "Documento" → "CPF").
- Essa lógica garante consistência na estrutura final dos dados.

---

### 🔠 4. Normalização de Dados-Chave

**Desafio**: Padronizar a coluna-chave (CPF), lidando com formatos variados e placeholders.

**Solução**:

- Implementação de uma função para reformatar todos os CPFs no padrão `DDD.DDD.DDD-DD`.
- A chamada é feita pelo LLM como uma `tool`, por meio de um prompt que fornece o formato correto esperado.
- Isso evita duplicações e falhas na mesclagem dos dados.

---

### 📊 5. Gerenciamento de Grandes Volumes de Dados

**Desafio**: Processar `DataFrames` extensos respeitando o limite de tokens da API do LLM e mantendo a acurácia.

**Solução**:

- Divisão dos dados em **batches menores**, garantindo que cada fatia caso o DataFrame seja muito grande não ultrapasse o limite de tokens ou por meio da redução do tamanho da batch,
  os resultados sejam mais precisos.
- Cada lote muda gradualmente o DataFrame que será mesclado no final.

---

### 💬 6. Análise de Dados Conversacional com RAG

**Desafio**: Permitir que usuários façam perguntas em linguagem natural sobre os dados consolidados.

**Solução**:

- Após a fusão e padronização dos dados, o arquivo `result.xlsx` é convertido em um índice vetorial com embeddings.
- O modelo **LLaMA 3.3 (llama3-8b-8192)** foi escolhido aqui por sua leveza e eficiência em tarefas de **pergunta-resposta** baseada em contexto recuperado.
- Aqui o **Retrieval Augmented Generation (RAG)** busca trechos relevantes nos dados vetorizados e passa-os como contexto para o modelo gerar respostas precisas.

---

## 🛠️ Tecnologias Utilizadas

- **Python** (linguagem principal)
- **Pandas**: Manipulação de dados tabulares
- **LangChain**: Framework para agentes LLM e definição de tools
- **Groq API**: Fornece acesso aos modelos LLaMA 3.3 e 4
- **HuggingFace Embeddings**: Geração de vetores para o RAG
- **FAISS**: Vetor store local para busca eficiente
- **python-dotenv**: Gerenciamento seguro de variáveis de ambiente

### Modelos LLM Utilizados:

- **`llama-4-scout-17b-16e-instruct`** (via Groq):
  - Responsável pela orquestração de tools, análise de DataFrames e pré-processamento.
  - Ideal para tarefas com múltiplos passos e tomada de decisão autônoma.

- **`llama3-8b-8192`** (via Groq):
  - Utilizado no chatbot com RAG.
  - Otimizado para performance e velocidade em consultas baseadas em dados estruturados.

---

## 🚀 Como Usar

### 1. Pré-requisitos

- Python 3.8+
- Conta na Groq com chave de API válida

### 2. Instalação

```bash
git clone https://github.com/FFernandes4280/Desafio_Techlab_2025.git
cd Desafio_Techlab_2025
```
Crie o arquivo .env com a sua chave da GROQ:
```bash
GROQ_API_KEY="SUA_CHAVE_API_DA_GROQ_AQUI"
```
A estrutura esperada do repositorio será:
``` bash
.
├── app.py
├── .env
├── result.xlsx (gerado automaticamente)
├── Planilhas/
│   ├── Dados Colaboradores.xlsx
│   ├── Ferramentas/
│   │   └── Github.xlsx
│   └── Beneficios/
│       └── Unimed.xlsx
└── tools/
    ├── load_files.py
    ├── standardize_files.py
    └── normalize_df.py
```
Finalmente, execute com:
``` bash
python app.py
```

🎥 [Clique aqui para ver o vídeo de demonstração](ExemploDeUso.mp4)

