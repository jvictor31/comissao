# 💰 Sistema de Gestão de Comissões

Sistema web completo para cálculo, visualização e exportação de comissões de vendas, desenvolvido com FastAPI e integrado a banco de dados relacional.

> ⚠️ Este projeto foi baseado em um sistema corporativo real, porém adaptado para fins de portfólio com estrutura simplificada e dados fictícios.

---

## 🚀 Demonstração do que o sistema faz

* Login com sessão
* Consulta de vendas por período
* Filtro por lojas e vendedores
* Cálculo automático de comissão
* Visualização em painel web
* Exportação de dados em:

  * CSV
  * PDF

---

## 🧠 Tecnologias utilizadas

* Python
* FastAPI
* MySQL
* Jinja2 (templates HTML)
* SessionMiddleware
* xhtml2pdf
* ReportLab
* Docker-ready (adaptável)

---

## 📁 Estrutura do projeto

```
comissao/
├── api.py              # Rotas e aplicação principal (FastAPI)
├── services.py         # Regras de negócio e queries
├── models.py           # Modelos Pydantic
├── database.py         # Conexão com banco
├── auth.py             # Autenticação
├── templates/          # HTML (Jinja2)
├── static/             # CSS, imagens
├── .env.example
├── requirements.txt
```

---

## ⚙️ Como rodar o projeto

### 1. Clone o repositório

```bash
git clone https://github.com/jvictor31/comissao
cd comissao
```

---

### 2. Crie um ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

---

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

---

### 4. Configure o ambiente

Crie o arquivo `.env`:

```bash
cp .env.example .env
```

Edite com suas credenciais locais:

```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=comissao_db
DB_USER=root
DB_PASSWORD=root
```

---

## 🗄️ Banco de Dados (IMPORTANTE)

### ⚠️ Contexto real

O sistema original utiliza um banco corporativo com schemas como:

* `sqldados`
* `starmoveis_custom`

Para fins de portfólio, você pode simular isso localmente e claro, alterar os nomes das tabelas nos códigos Python também.

---

## 🧪 Criando banco de teste (SIMULADO)

### 1. Criar banco

```sql
CREATE DATABASE comissao_db;
USE comissao_db;
```

---

### 2. Criar tabelas simplificadas

```sql
CREATE TABLE vendedores (
    no INT PRIMARY KEY,
    name VARCHAR(100),
    funcao INT,
    storeno INT
);

CREATE TABLE lojas (
    storeno INT PRIMARY KEY
);

CREATE TABLE vendas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    storeno INT,
    vendno INT,
    grupo VARCHAR(1),
    venda DECIMAL(10,2),
    custo DECIMAL(10,2),
    data_venda DATE
);
```

---

### 3. Inserir dados de teste

```sql
INSERT INTO vendedores VALUES
(1, 'João', 71, 10),
(2, 'Maria', 46, 10);

INSERT INTO lojas VALUES (10);

INSERT INTO vendas (storeno, vendno, grupo, venda, custo, data_venda)
VALUES
(10, 1, 'M', 1000, 600, '2024-01-10'),
(10, 1, 'E', 500, 300, '2024-01-11'),
(10, 2, 'C', 800, 500, '2024-01-12');
```

---

## 🔐 Login (IMPORTANTE)

O sistema original valida senha com criptografia específica do banco Nérus.

👉 Para ambiente local, você pode usar a opção abaixo:

### ✔ Opção 1 (mais simples)

Alterar temporariamente no `auth.py`:

```python
def autenticar_usuario(login, senha):
    return {
        "id": 1,
        "login": login,
        "nome": "Usuário Teste",
        "funcao": 71,
        "storeno": 10,
        "is_gerente": True
    }
```

---

## ▶️ Executando o projeto

```bash
uvicorn api:app --reload
```

Acesse:

```
http://localhost:8000
```

---

## 🔎 Principais endpoints

| Rota            | Descrição            |
| --------------- | -------------------- |
| `/`             | Tela de login        |
| `/painel`       | Dashboard            |
| `/consultar`    | Consulta com filtros |
| `/comissoes`    | API JSON             |
| `/exportar_csv` | Exportação CSV       |
| `/exportar_pdf` | Exportação PDF       |

---

## 📊 Regras de negócio

O sistema calcula comissão com base em:

* Grupo de produto (`M`, `E`, `C`, `S`, `P`)
* Margem de venda
* Função do vendedor
* Loja

Inclui lógica específica para:

* Vendedores
* Gerentes
* Produtos promocionais
* Produtos de saldo

---

## 🧠 Arquitetura

Separação clara por responsabilidades:

* **api.py** → Rotas e HTTP
* **services.py** → Regras de negócio
* **auth.py** → Autenticação
* **database.py** → Conexão com banco
* **templates/** → Interface

---

## 📈 Melhorias futuras

* JWT Authentication
* Docker + docker-compose
* Testes automatizados
* Swagger mais detalhado
* Deploy em cloud (AWS/GCP)

---

## ⚠️ Aviso

Este projeto:

* NÃO contém dados reais
* NÃO expõe credenciais
* NÃO replica integralmente o ambiente corporativo

---

## 👨‍💻 Autor

João Victor Portella
