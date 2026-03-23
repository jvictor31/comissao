import logging
import csv
import os

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from collections import defaultdict
from io import StringIO, BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
from xhtml2pdf import pisa

from auth import autenticar_usuario
from services import buscar_vendas, listar_lojas, listar_vendedores, buscar_comissoes_gerente

# --------------------------------
# CONFIGURAÇÃO DE LOG
# --------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# --------------------------------
# APP
# --------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="capitalverde_comissoes"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


# --------------------------------
# MIDDLEWARE DE LOG
# --------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):

    logger.info(f"REQUEST {request.method} {request.url}")

    response = await call_next(request)

    logger.info(f"RESPONSE {response.status_code}")

    return response


# --------------------------------
# FUNÇÃO PARA VERIFICAR LOGIN
# --------------------------------

def exigir_login(request: Request):

    usuario = request.session.get("usuario")

    if not usuario:
        logger.warning("Usuário tentou acessar rota protegida sem login")
        raise HTTPException(status_code=401)

    return usuario


# --------------------------------
# TELA LOGIN
# --------------------------------

@app.get("/")
def tela_login(request: Request):

    logger.info("Abrindo tela de login")

    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )
# --------------------------------
# API
# --------------------------------

@app.get("/comissoes")
def api_comissoes(
    data_inicio: str,
    data_fim: str,
    usuario=Depends(exigir_login)
):

    logger.info(
        f"API /comissoes chamada | usuario={usuario['login']} | inicio={data_inicio} | fim={data_fim}"
    )

    dados = buscar_vendas(data_inicio, data_fim)

    return dados

# --------------------------------
# LOGIN
# --------------------------------

@app.post("/login")
def login(
    request: Request,
    login: str = Form(...),
    senha: str = Form(...)
):

    logger.info(f"Tentativa de login: {login}")

    usuario = autenticar_usuario(login, senha)

    if not usuario:

        logger.warning("Login inválido")

        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "erro": "Usuário ou senha inválidos"
            }
        )

    request.session["usuario"] = usuario

    logger.info(f"Login realizado com sucesso: {login}")

    return RedirectResponse("/painel", status_code=302)


# --------------------------------
# PAINEL
# --------------------------------

@app.get("/painel")
def painel(
    request: Request,
    data_inicio: str = "",
    data_fim: str = "",
    lojas: str = "",
    vendedores: str = "",
    cargo: str = "vendedor",
    usuario=Depends(exigir_login)
):

    logger.info(f"Usuário {usuario['login']} acessou painel")

    lista_lojas = listar_lojas()

    return templates.TemplateResponse(
        "painel.html",
        {
            "request": request,
            "usuario": usuario,

            # 🔥 lista para o SELECT
            "lojas": lista_lojas,

            # 🔥 filtros (strings)
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "lojas_selecionadas": lojas,        # ✅ agora correto
            "vendedores_selecionados": vendedores,
            "cargo": cargo
        }
    )


# --------------------------------
# CONSULTA DE COMISSÕES
# --------------------------------

@app.post("/consultar")
def consultar(
    request: Request,
    data_inicio: str = Form(...),
    data_fim: str = Form(...),
    cargo: str = Form(...),
    lojas: str = Form(None),
    vendedores: str = Form(None),
    usuario=Depends(exigir_login)
):

    lista_lojas = [l for l in lojas.split(",") if l.strip()] if lojas else None
    lista_vendedores = [v for v in vendedores.split(",") if v.strip()] if vendedores else None

    logger.info(
        f"Consulta solicitada | usuario={usuario['login']} | inicio={data_inicio} | fim={data_fim} | lojas={lista_lojas} | vendedores={lista_vendedores}"
    )

    if cargo == "vendedor":
        dados = buscar_vendas(data_inicio, data_fim, lista_lojas, lista_vendedores)
    else:
        dados = buscar_comissoes_gerente(data_inicio, data_fim, lista_lojas)

    dados = sorted(dados, key=lambda x: ((x["storeno"] or 0), x["vendno"] or 0))

    totais_vendedor = defaultdict(lambda: {"nome": "", "vendas": 0, "comissao": 0})

    for d in dados:

        vend = d["vendno"]

        totais_vendedor[vend]["nome"] = d["vendedor"]
        totais_vendedor[vend]["vendas"] += d["valor_total"]
        totais_vendedor[vend]["comissao"] += d["comissao"]

    total_vendas = sum(d.get("valor_total", 0) for d in dados)
    total_comissoes = sum(d.get("comissao", 0) for d in dados)

    logger.info(f"Consulta retornou {len(dados)} registros")
    
    def formatar_moeda(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # formatar datas
    data_inicio_br = formatar_data(data_inicio)
    data_fim_br = formatar_data(data_fim)

    # formatar dados individuais
    for d in dados:
        d["valor_formatado"] = formatar_moeda(d.get("valor_total") or 0)
        d["comissao_formatada"] = formatar_moeda(d.get("comissao") or 0)

    # formatar totais por vendedor
    for vend, t in totais_vendedor.items():
        t["vendas_formatado"] = formatar_moeda(t["vendas"] or 0)
        t["comissao_formatado"] = formatar_moeda(t["comissao"] or 0)

    # totais gerais
    total_vendas_formatado = formatar_moeda(total_vendas)
    total_comissoes_formatado = formatar_moeda(total_comissoes)

    return templates.TemplateResponse(
        "tabela_comissoes.html",
        {
            "request": request,
            "dados": dados,
            "cargo": cargo,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "data_inicio_br": data_inicio_br,
            "data_fim_br": data_fim_br,
            "lojas": lojas,
            "vendedores": vendedores,
            "total_vendas_formatado": total_vendas_formatado,
            "total_comissoes_formatado": total_comissoes_formatado,
            "totais_vendedor": totais_vendedor
        }
    )

# --------------------------------
# LOGOUT
# --------------------------------

@app.get("/logout")
def logout(request: Request):

    request.session.clear()

    logger.info("Usuário fez logout")

    return RedirectResponse("/", status_code=302)

# --------------------------------
# LOJAS
# --------------------------------

@app.get("/lojas")
def lojas(usuario=Depends(exigir_login)):

    logger.info("Listando lojas")

    lojas = listar_lojas()

    return lojas

# --------------------------------
# VENDEDORES
# --------------------------------

@app.get("/vendedores")
def vendedores(
    storeno: str,
    cargo: str,
    usuario=Depends(exigir_login)
):

    lojas = storeno.split(",")

    logger.info(f"Listando vendedores das lojas {lojas}")

    todos = []

    for loja in lojas:
        vendedores = listar_vendedores(loja, cargo)
        todos.extend(vendedores)

    # remover duplicados
    vendedores_unicos = {v["no"]: v for v in todos}.values()

    return list(vendedores_unicos)

def normalizar_dados_exportacao(dados, cargo):
    cargo = (cargo or "").lower()
    resultado = defaultdict(lambda: {"M":0,"E":0,"C":0,"S":0,"P":0})

    for d in dados:

        vend = d["vendno"]
        grupo = d["grupo"]
        comissao = d["comissao"]

        if cargo == "gerente":

            #  REGRA DO GERENTE
            if grupo == "M":
                resultado[vend]["M"] += comissao

            elif grupo in ("E", "C", "P"):
                resultado[vend]["P"] += comissao

            elif grupo == "S":
                resultado[vend]["S"] += comissao

        else:
            #  REGRA NORMAL (VENDEDOR)
            if grupo in resultado[vend]:
                resultado[vend][grupo] += comissao

    return resultado

@app.get("/exportar_csv")
def exportar_csv(
    request: Request,
    data_inicio: str,
    data_fim: str,
    lojas: str = None,
    vendedores: str = None,
    usuario=Depends(exigir_login)
):

    if lojas:
        lista_lojas = [l for l in lojas.split(",") if l.strip()]
        if not lista_lojas:
            lista_lojas = None
    else:
        lista_lojas = None

    if vendedores and vendedores != "None":
        lista_vendedores = [v for v in vendedores.split(",") if v.strip()]
        if not lista_vendedores:
            lista_vendedores = None
    else:
        lista_vendedores = None

    cargo = request.query_params.get("cargo", "vendedor").lower()

    logger.info(f"VENDEDORES FILTRO: {lista_vendedores}")
    logger.info(f"LOJAS FILTRO: {lista_lojas}")
    logger.info(f"CARGO: {cargo}")

    if cargo == "vendedor":
        dados = buscar_vendas(data_inicio, data_fim, lista_lojas, lista_vendedores)
    else:
        dados = buscar_comissoes_gerente(data_inicio, data_fim, lista_lojas)

    resultado = normalizar_dados_exportacao(dados, cargo)

    output = StringIO()

    writer = csv.writer(output, delimiter=";")

    if cargo == "gerente":
        writer.writerow([
            "vendno",
            "C Moveis",
            "C Promocao",
            "C Saldo"
        ])
    else:
        writer.writerow([
            "vendno",
            "C Moveis",
            "C Eletro",
            "C Celular",
            "C Saldo",
            "C Promocao"
        ])

    for vend, grupos in resultado.items():

        if cargo == "gerente":
            writer.writerow([
                vend,
                round(grupos["M"],2),
                round(grupos["P"],2),
                round(grupos["S"],2)
            ])
        else:
            writer.writerow([
                vend,
                round(grupos["M"],2),
                round(grupos["E"],2),
                round(grupos["C"],2),
                round(grupos["S"],2),
                round(grupos["P"],2)
            ])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=comissoes.csv"
        }
    )

def formatar_data(data):
    return datetime.strptime(data, "%Y-%m-%d").strftime("%d/%m/%Y")

def link_callback(uri, rel):
    path = os.path.join(BASE_DIR, uri.replace("/static/", "static/"))

    if os.path.isfile(path):
        return path

    raise Exception(f"Arquivo não encontrado: {path}")

def gerar_pdf(html):
    resultado = BytesIO()
    pisa.CreatePDF(
        html,
        dest=resultado,
        link_callback=link_callback
    )
    resultado.seek(0)
    return resultado

@app.get("/exportar_pdf")
def exportar_pdf(
    request: Request,
    data_inicio: str,
    data_fim: str,
    lojas: str = None,
    vendedores: str = None,
    usuario=Depends(exigir_login)
):

    if lojas:
        lista_lojas = [l for l in lojas.split(",") if l.strip()]
        if not lista_lojas:
            lista_lojas = None
    else:
        lista_lojas = None

    if vendedores and vendedores != "None":
        lista_vendedores = [v for v in vendedores.split(",") if v.strip()]
        if not lista_vendedores:
            lista_vendedores = None
    else:
        lista_vendedores = None

    cargo = request.query_params.get("cargo", "vendedor").lower()

    logger.info(f"VENDEDORES FILTRO: {lista_vendedores}")
    logger.info(f"LOJAS FILTRO: {lista_lojas}")
    logger.info(f"CARGO: {cargo}")

    if cargo == "vendedor":
        dados = buscar_vendas(data_inicio, data_fim, lista_lojas, lista_vendedores)
    else:
        dados = buscar_comissoes_gerente(data_inicio, data_fim, lista_lojas)

    vendedores_dict = defaultdict(list)

    for d in dados:
        vendedores_dict[d["vendno"]].append(d)

    data_inicio_br = formatar_data(data_inicio)
    data_fim_br = formatar_data(data_fim)

    html_final = ""

    if not vendedores_dict:
        return StreamingResponse(
            gerar_pdf("<h1>Nenhum dado encontrado</h1>"),
            media_type="application/pdf"
        )

    for vendno, vendas in vendedores_dict.items():

        nome_vendedor = vendas[0].get("vendedor", "Vendedor")

        if "funcao" in vendas[0]:
            funcao = vendas[0].get("funcao", 0)

            if funcao == 46:
                cargo_nome = "Vendedor Comissionado"
            elif funcao == 71:
                cargo_nome = "Vendedor"
            else:
                cargo_nome = "Outro"
        else:
            cargo_nome = "Gerente"

        # calcular comissões por grupo
        comissoes = {"M":0,"E":0,"C":0,"S":0,"P":0}
        valores = {"M":0,"E":0,"C":0,"S":0,"P":0}

        normalizado = normalizar_dados_exportacao(vendas, cargo)

        comissoes = normalizado.get(vendno, {"M":0,"E":0,"C":0,"S":0,"P":0})

        # valores também precisa ajustar 👇
        valores = {"M":0,"E":0,"C":0,"S":0,"P":0}

        for v in vendas:
            grupo = v["grupo"]

            if grupo in valores:
                valores[grupo] += v["valor_total"]

        total_comissao = sum(comissoes.values())

        html = templates.get_template("relatorio_comissao.html").render(
            cargo=cargo_nome,
            tipo=cargo,
            nome=nome_vendedor,
            mes=f"{data_inicio_br} até {data_fim_br}",
            valor_m=f"{valores['M']:.2f}",
            valor_e=f"{valores['E']:.2f}",
            valor_c=f"{valores['C']:.2f}",
            valor_s=f"{valores['S']:.2f}",
            valor_p=f"{valores['P']:.2f}",
            valor_total=f"{sum(valores.values()):.2f}",
            comissao_m=f"{comissoes['M']:.2f}",
            comissao_e=f"{comissoes['E']:.2f}",
            comissao_c=f"{comissoes['C']:.2f}",
            comissao_s=f"{comissoes['S']:.2f}",
            comissao_p=f"{comissoes['P']:.2f}",
            total_comissao=f"{total_comissao:.2f}"
        )

        html_final += f"""
        <html>
        <body>
        <div style="page-break-after:always;">
        {html}
        </div>
        </body>
        </html>
        """

    pdf = gerar_pdf(html_final)

    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=relatorio_comissoes.pdf"
        }
    )