import logging
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from database import get_connection


# ============================================================
# AUTENTICAÇÃO
# ============================================================
# Responsável por:
# - Validar login e senha no banco Nérus
# - Montar o objeto de usuário da sessão
# - Definir permissões (ex: gerente)


def autenticar_usuario(login: str, senha: str):

    logging.info(f"Iniciando autenticação | login={login}")

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # ----------------------------------------------------
        # VALIDAÇÃO DE LOGIN E SENHA (padrão Nérus)
        # ----------------------------------------------------

        cursor.execute("""
            SELECT u.no, u.name, u.login
            FROM sqldados.users u
            WHERE u.login = %s
              AND CONVERT(
                CONCAT(
                  CHAR(ASCII(MID(pswd,1,1))-5),
                  CHAR(ASCII(MID(pswd,2,1))-7),
                  CHAR(ASCII(MID(pswd,3,1))-8),
                  CHAR(ASCII(MID(pswd,4,1))),
                  CHAR(ASCII(MID(pswd,5,1))-34),
                  CHAR(ASCII(MID(pswd,6,1))-9),
                  CHAR(ASCII(MID(pswd,7,1))-9),
                  CHAR(ASCII(MID(pswd,8,1))-13)
                ) USING utf8
              ) = %s
        """, (login, senha))

        user = cursor.fetchone()

        # ----------------------------------------------------
        # USUÁRIO OU SENHA INVÁLIDOS
        # ----------------------------------------------------

        if not user:

            cursor.close()
            conn.close()

            logging.warning(f"Login inválido | login={login}")

            return None

        # ----------------------------------------------------
        # BUSCAR FUNÇÃO E LOJA DO USUÁRIO
        # ----------------------------------------------------

        cursor.execute("""
            SELECT funcao, storeno
            FROM sqldados.emp
            WHERE no = %s
            LIMIT 1
        """, (user["no"],))

        emp = cursor.fetchone()

        funcao = emp["funcao"] if emp else None
        storeno = emp["storeno"] if emp else None

        # ----------------------------------------------------
        # REGRA DE GERENTE
        # ----------------------------------------------------

        is_gerente = (user["login"] == "JVSP")

        cursor.close()
        conn.close()

        logging.info(f"LOGIN OK | usuario={user['login']}")

        # ----------------------------------------------------
        # OBJETO DE USUÁRIO (SERÁ SALVO NA SESSÃO)
        # ----------------------------------------------------

        return {
            "id": user["no"],
            "login": user["login"],
            "nome": user["name"],
            "funcao": funcao,
            "storeno": storeno,
            "is_gerente": is_gerente
        }

    except Exception:

        logging.exception("Erro na autenticação")

        return None


# ============================================================
# DEPENDENCY PARA API JSON
# ============================================================
# Usada em endpoints que retornam JSON
# Retorna 401 se não estiver logado


def get_usuario_logado(request: Request):

    usuario = request.session.get("usuario")

    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")

    return usuario


# ============================================================
# DEPENDENCY PARA TELAS HTML
# ============================================================


def exigir_login_html(request: Request):

    usuario = request.session.get("usuario")

    if not usuario:

        return RedirectResponse("/login", status_code=302)

    return usuario


# ============================================================
# DEPENDENCY PARA GERENTES
# ============================================================


def exigir_gerente_html(request: Request):

    usuario = request.session.get("usuario")

    if not usuario:

        return RedirectResponse("/login", status_code=302)

    if not usuario.get("is_gerente"):

        raise HTTPException(
            status_code=403,
            detail="Usuário sem permissão de gerente"
        )

    return usuario