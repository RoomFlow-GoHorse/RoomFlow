# RoomFlow

Sistema de gerenciamento e reserva de salas desenvolvido em **Python** com **Streamlit**, utilizando arquitetura **MVC**.

## Tecnologias

* Python
* Streamlit

## Requisitos

Antes de executar o projeto, certifique-se de ter instalado:

* [Python](https://www.python.org/downloads/) 3.10 ou superior
* Git

## Instalação

### 1. Clone o repositório

```bash
git clone <URL_DO_REPOSITORIO>
```

Entre na pasta do projeto:

```bash
cd RoomFlow
```

### 2. Crie o ambiente virtual

No Windows:

```powershell
python -m venv .venv
```

### 3. Ative o ambiente virtual

No PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

No Prompt de Comando (CMD):

```cmd
.venv\Scripts\activate
```

### 4. Instale as dependências

Com o ambiente virtual ativado:

```bash
pip install -r requirements.txt
```
ou

```bash
pip install streamlit 
```

## Executando o projeto

Com o ambiente virtual ativado, execute:

```bash
streamlit run main.py
```

O Streamlit iniciará o sistema e exibirá no terminal o endereço para acessar a aplicação pelo navegador.

Normalmente:

```text
http://localhost:8501
```

## Estrutura do projeto

```text
RoomFlow/
├── controllers/         # Ações das telas e seleção das rotas
├── models/              # Dados e operações por domínio
├── views/
│   ├── pages/           # Telas completas
│   └── components/      # Elementos visuais compartilhados
├── services/            # Integração com a sessão e navegação do Streamlit
├── data/                # Dados iniciais de demonstração
├── config/              # Constantes, perfis e permissões declaradas
├── css/                 # Estilos da interface
├── assets/              # Imagens e logos
├── tests/               # Testes dos models
├── main.py              # Configuração e inicialização do app
├── requirements.txt
└── README.md
```

### Arquitetura MVC

O fluxo das operações é `View → Controller → Model`. O resultado retorna à
view para apresentação. No Streamlit, as telas chamam os controllers quando
o usuário interage com os widgets.

* **Models:** consultam e alteram reservas, espaços, usuários, notificações e
  conflitos. Recebem um armazenamento como argumento e não importam Streamlit.
* **Views:** renderizam páginas e componentes e mantêm o estado visual dos
  formulários. Para acessar dados da aplicação, chamam os controllers.
* **Controllers:** intermediam as operações dos models e a sessão da aplicação.
  `app_controller.py` seleciona a página; `dashboard_controller.py` reúne indicadores.
* **Services:** adaptam o estado da sessão, navegação e avisos ao Streamlit.
* **main.py:** configura o Streamlit, inicializa a sessão e chama o controller da aplicação.

Os dados continuam sendo simulados e armazenados por sessão, sem banco de dados.
Cadastro e recuperação de senha continuam sendo fluxos demonstrativos.
O login consulta os mesmos usuários da sessão usados pela administração.

### Testes

```bash
python -m unittest discover -s tests -v
```

## Desenvolvimento

Sempre que uma nova biblioteca for adicionada ao projeto, atualize o arquivo `requirements.txt` para que outros desenvolvedores possam instalar as mesmas dependências.

Para atualizar o arquivo com as dependências instaladas:

```bash
pip freeze > requirements.txt
```

## Status

🚧 Projeto em desenvolvimento.
