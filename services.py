from database import get_connection
import logging

logger = logging.getLogger(__name__)


def buscar_vendas(data_inicio: str, data_fim: str, lojas=None, vendedores=None):

    data_inicio = data_inicio.replace("-", "")
    data_fim = data_fim.replace("-", "")

    logger.info(f"Iniciando busca de vendas | inicio={data_inicio} | fim={data_fim}")

    filtros = []
    params = []

    filtros.append("mapavenda.dtord BETWEEN %s AND %s")
    params.append(data_inicio)
    params.append(data_fim)

    filtros.append("mapavenda.vendno <> 672")

    if lojas:

        placeholders = ",".join(["%s"] * len(lojas))

        filtros.append(f"mapavenda.storeno IN ({placeholders})")

        params.extend(lojas)

    if vendedores:

        placeholders = ",".join(["%s"] * len(vendedores))

        filtros.append(f"mapavenda.vendno IN ({placeholders})")

        params.extend(vendedores)

    where_sql = " AND ".join(filtros)

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = f"""
        SELECT
            mapavenda.storeno,
            mapavenda.vendno,
            emp.name AS vendedor,
            emp.funcao,
            mapavenda.grupo,

            TRUNCATE(SUM(mapavenda.venda) / 100, 2) AS valor_total,

            CASE
                WHEN mapavenda.grupo = 'M'
                THEN TRUNCATE(
                    (1 - SUM(mapavenda.custo) / SUM(mapavenda.venda)) * 10000,
                    0
                )
                ELSE NULL
            END AS margem,

            starmoveis_custom.fn_com2(
                CASE
                    WHEN mapavenda.grupo IN ('E','C','P','S') THEN 0
                    ELSE TRUNCATE(
                        (1 - SUM(mapavenda.custo) / SUM(mapavenda.venda)) * 10000,
                        0
                    )
                END,
                mapavenda.grupo,
                emp.funcao,
                mapavenda.storeno
            ) AS percentual_comissao,

            ROUND(
                (
                    TRUNCATE(SUM(mapavenda.venda) / 100, 2) *
                    starmoveis_custom.fn_com2(
                        CASE
                            WHEN mapavenda.grupo IN ('E','C','P','S') THEN 0
                            ELSE TRUNCATE(
                                (1 - SUM(mapavenda.custo) / SUM(mapavenda.venda)) * 10000,
                                0
                            )
                        END,
                        mapavenda.grupo,
                        emp.funcao,
                        mapavenda.storeno
                    ) / 10000
                ),
            2) AS comissao

        FROM starmoveis_custom.mapavenda

        JOIN sqldados.prd
            ON TRIM(mapavenda.prdno) = TRIM(prd.no)

        JOIN sqldados.emp
            ON emp.no = mapavenda.vendno
            AND mapavenda.storeno = emp.storeno

        WHERE {where_sql}

        GROUP BY
            mapavenda.storeno,
            mapavenda.vendno,
            emp.name,
            mapavenda.grupo,
            emp.funcao
        """

        logger.info("Executando query de comissões")

        cursor.execute(query, params)

        resultados = cursor.fetchall()

        logger.info(f"Query executada com sucesso | registros retornados: {len(resultados)}")

        cursor.close()
        conn.close()

        for r in resultados:

            if r["margem"] is not None:
                r["margem"] = round(r["margem"] / 100, 2)

            if r["percentual_comissao"] is not None:
                r["percentual_comissao"] = round(r["percentual_comissao"] / 100, 2)

        logger.info("Processamento dos resultados finalizado")

        return resultados

    except Exception as e:

        logger.exception("Erro ao buscar vendas no banco")

        raise e


def listar_lojas():

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT bankno
        FROM sqldados.store
        WHERE bankno NOT IN (1,2,33,300,301)
        ORDER BY bankno
        """

        cursor.execute(query)

        lojas = cursor.fetchall()

        cursor.close()
        conn.close()

        return lojas

    except Exception as e:

        logger.exception("Erro ao buscar lojas")

        raise e


def listar_vendedores(storeno: int, cargo : str):

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        if cargo == "gerente":
            filtro_funcao = "funcao = 35"
        else:
            filtro_funcao = "funcao IN (71,46)"

        query = f"""
        SELECT
            no,
            name
        FROM sqldados.emp
        WHERE storeno = %s
        AND {filtro_funcao}
        ORDER BY name
        """

        cursor.execute(query, (storeno,))

        vendedores = cursor.fetchall()

        cursor.close()
        conn.close()

        return vendedores

    except Exception as e:

        logger.exception("Erro ao buscar vendedores")

        raise e

def buscar_comissoes_gerente(data_inicio: str, data_fim: str, lojas=None):

    data_inicio = data_inicio.replace("-", "")
    data_fim = data_fim.replace("-", "")

    filtros = []
    params = []

    filtros.append("mapavenda.dtord BETWEEN %s AND %s")
    filtros.append("mapavenda.vendno <> 672")
    filtros.append("emp.funcao IN (35, 71, 46)")
    params.append(data_inicio)
    params.append(data_fim)

    if lojas:
        placeholders = ",".join(["%s"] * len(lojas))
        filtros.append(f"mapavenda.storeno IN ({placeholders})")
        params.extend(lojas)

    where_sql = " AND ".join(filtros)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = f"""
    SELECT
        mapavenda.storeno,

        SUM(CASE WHEN mapavenda.grupo='M'
            THEN mapavenda.venda ELSE 0 END)/100 AS venda_moveis,

        SUM(CASE WHEN mapavenda.grupo='M'
            THEN mapavenda.custo ELSE 0 END)/100 AS custo_moveis,

        SUM(CASE WHEN mapavenda.grupo IN ('E','C','P')
            THEN mapavenda.venda ELSE 0 END)/100 AS venda_promocao,

        SUM(CASE WHEN mapavenda.grupo='S'
            THEN mapavenda.venda ELSE 0 END)/100 AS venda_saldo

    FROM starmoveis_custom.mapavenda
    JOIN sqldados.emp
        ON emp.no = mapavenda.vendno
        AND emp.storeno = mapavenda.storeno
    WHERE {where_sql}
    GROUP BY mapavenda.storeno
    """

    cursor.execute(query, params)
    dados_lojas = cursor.fetchall()

    resultado = []

    cursor.execute("""
    SELECT no AS vendno, name AS nome, storeno
    FROM sqldados.emp
    WHERE funcao = 35
    """)

    gerentes = cursor.fetchall()

    mapa_gerentes = {g["storeno"]: g for g in gerentes}

    for loja in dados_lojas:

        storeno = loja["storeno"]

        venda_moveis = float(loja["venda_moveis"] or 0)
        custo_moveis = float(loja["custo_moveis"] or 0)
        venda_promocao = float(loja["venda_promocao"] or 0)
        venda_saldo = float(loja["venda_saldo"] or 0)

        margem = 0
        if venda_moveis > 0:
            margem = (1 - (custo_moveis / venda_moveis)) * 100

        margem_sql = int(margem * 100)

        gerente = mapa_gerentes.get(storeno)

        vendno = gerente["vendno"] if gerente else 0
        nome_gerente = gerente["nome"] if gerente else "GERENTE"

        cursor.execute("""
        SELECT comissao
        FROM starmoveis_custom.cadastrocomissaoger
        WHERE storeno=%s
        AND margemmin <= %s
        ORDER BY margemmin DESC
        LIMIT 1
        """, (storeno, margem_sql))

        row = cursor.fetchone()

        perc_moveis = float(row["comissao"]) if row else 0

        comissao_moveis = venda_moveis * (perc_moveis / 10000)

        comissao_promocao = venda_promocao * 0.005

        perc = 0
        comissao_saldo = 0

        if storeno == 31:

            if venda_saldo >= 300000:
                perc = 0.009
            elif venda_saldo >= 270000:
                perc = 0.008
            elif venda_saldo >= 250000:
                perc = 0.007

            comissao_saldo = venda_saldo * perc

        resultado.append({
            "storeno": storeno,
            "grupo": "M",
            "vendedor": nome_gerente,
            "vendno": vendno,
            "valor_total": round(venda_moveis,2),
            "margem": round(margem,2),
            "percentual_comissao": perc_moveis/100 if perc_moveis else 0,
            "comissao": round(comissao_moveis,2)
        })

        resultado.append({
            "storeno": storeno,
            "grupo": "P",
            "vendedor": nome_gerente,
            "vendno": vendno,
            "valor_total": round(venda_promocao,2),
            "margem": None,
            "percentual_comissao": 0.5,
            "comissao": round(comissao_promocao,2)
        })

        if storeno == 31:
            resultado.append({
                "storeno": storeno,
                "grupo": "S",
                "vendedor": nome_gerente,
                "vendno": vendno,
                "valor_total": round(venda_saldo,2),
                "margem": None,
                "percentual_comissao": perc*100,
                "comissao": round(comissao_saldo,2)
            })

    cursor.close()
    conn.close()

    return resultado