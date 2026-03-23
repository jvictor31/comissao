import pandas as pd
from database import get_connection
from unidecode import unidecode

# ==========================================
# 1️⃣ LER PLANILHA
# ==========================================

arquivo = "comissao_planilha_tratada_total.xlsx"

df = pd.read_excel(arquivo)

df.columns = (
    df.columns
    .str.lower()
    .str.strip()
    .str.replace(" ", "_")
)

print("Colunas encontradas:")
print(df.columns)

# ==========================================
# 2️⃣ GRUPO MOVEIS (M)
# ==========================================

df_m = df[[
    "loja",
    "nome",
    "funcao",
    "valor_total_moveis",
    "comissao_moveis"
]].copy()

df_m["grupo"] = "M"

df_m = df_m.rename(columns={
    "nome": "vendedor",
    "valor_total_moveis": "valor_total",
    "comissao_moveis": "comissao"
})

# ==========================================
# 3️⃣ GRUPO SALDO (S)
# ==========================================

df_s = df[[
    "loja",
    "nome",
    "funcao",
    "valor_total_saldo",
    "comissao_saldo"
]].copy()

df_s["grupo"] = "S"

df_s = df_s.rename(columns={
    "nome": "vendedor",
    "valor_total_saldo": "valor_total",
    "comissao_saldo": "comissao"
})

# ==========================================
# 4️⃣ GRUPO ELETRO (E)
# ==========================================

df_e = df[[
    "loja",
    "nome",
    "funcao",
    "valor_total_eletro",
    "comissao_eletro"
]].copy()

df_e["grupo"] = "E"

df_e = df_e.rename(columns={
    "nome": "vendedor",
    "valor_total_eletro": "valor_total",
    "comissao_eletro": "comissao"
})

# ==========================================
# 5️⃣ GRUPO CELULAR (C)
# ==========================================

df_c = df[[
    "loja",
    "nome",
    "funcao",
    "valor_total_celular",
    "comissao_celular"
]].copy()

df_c["grupo"] = "C"

df_c = df_c.rename(columns={
    "nome": "vendedor",
    "valor_total_celular": "valor_total",
    "comissao_celular": "comissao"
})

# ==========================================
# 6️⃣ JUNTAR PLANILHA
# ==========================================

df_planilha = pd.concat([df_m, df_s, df_e, df_c], ignore_index=True)

# ==========================================
# 7️⃣ PADRONIZAÇÃO
# ==========================================

df_planilha["vendedor"] = (
    df_planilha["vendedor"]
    .fillna("")
    .astype(str)
    .apply(unidecode)
    .str.strip()
    .str.upper()
)

df_planilha["loja"] = (
    df_planilha["loja"]
    .astype(str)
    .str.upper()
    .str.replace("LOJA", "", regex=False)
    .str.strip()
    .astype(int)
)

df_planilha["grupo"] = (
    df_planilha["grupo"]
    .astype(str)
    .str.strip()
    .str.upper()
)

df_planilha["valor_total"] = (
    df_planilha["valor_total"]
    .astype(str)
    .str.replace(",", ".", regex=False)
)

df_planilha["comissao"] = (
    df_planilha["comissao"]
    .astype(str)
    .str.replace(",", ".", regex=False)
)

df_planilha["valor_total"] = pd.to_numeric(df_planilha["valor_total"], errors="coerce").fillna(0)
df_planilha["comissao"] = pd.to_numeric(df_planilha["comissao"], errors="coerce").fillna(0)

df_planilha["valor_total"] = df_planilha["valor_total"].round(2)
df_planilha["comissao"] = df_planilha["comissao"].round(2)

# ==========================================
# 8️⃣ BUSCAR DADOS DO BANCO
# ==========================================

conn = get_connection()

query = """

SELECT
    mapavenda.storeno AS loja,
    emp.name AS vendedor,
    mapavenda.grupo,

    ROUND(SUM(mapavenda.venda) / 100, 2) AS valor_total,

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

JOIN sqldados.emp
    ON emp.no = mapavenda.vendno
    AND emp.storeno = mapavenda.storeno

WHERE mapavenda.dtord BETWEEN '20260101' AND '20260131'
AND mapavenda.vendno <> 672
AND mapavenda.grupo IN ('M','S','C','E')

GROUP BY
    mapavenda.storeno,
    emp.name,
    mapavenda.grupo

ORDER BY
    mapavenda.grupo,
    emp.name

"""

df_api = pd.read_sql(query, conn)

conn.close()

# ==========================================
# 9️⃣ PADRONIZAR BANCO
# ==========================================

df_api["vendedor"] = (
    df_api["vendedor"]
    .astype(str)
    .apply(unidecode)
    .str.strip()
    .str.upper()
)

df_api["loja"] = df_api["loja"].astype(int)

df_api["valor_total"] = pd.to_numeric(df_api["valor_total"], errors="coerce").fillna(0)
df_api["comissao"] = pd.to_numeric(df_api["comissao"], errors="coerce").fillna(0)

df_api["valor_total"] = df_api["valor_total"].round(2)
df_api["comissao"] = df_api["comissao"].round(2)

# ==========================================
# 🔟 COMPARAÇÃO
# ==========================================

df_final = df_planilha.merge(
    df_api,
    on=["loja", "vendedor", "grupo"],
    how="left",
    suffixes=("_planilha", "_banco")
)

df_final["valor_total_banco"] = df_final["valor_total_banco"].fillna(0)
df_final["comissao_banco"] = df_final["comissao_banco"].fillna(0)

df_final["dif_valor"] = (
    df_final["valor_total_planilha"] - df_final["valor_total_banco"]
)

df_final["dif_comissao"] = (
    df_final["comissao_planilha"] - df_final["comissao_banco"]
)

# ==========================================
# 1️⃣1️⃣ FILTRAR DIVERGENCIAS
# ==========================================

df_divergencias = df_final[
    (df_final["dif_valor"] != 0) |
    (df_final["dif_comissao"] != 0)
]

# ==========================================
# 1️⃣2️⃣ EXPORTAR
# ==========================================

df_final.to_excel("comparacao_todos_grupos.xlsx", index=False)

df_divergencias.to_excel("divergencias_todos_grupos.xlsx", index=False)

# ==========================================
# FINAL
# ==========================================

print("====================================")
print("✔ Comparação finalizada")
print("Arquivo completo: comparacao_todos_grupos.xlsx")
print("Arquivo divergencias: divergencias_todos_grupos.xlsx")
print("Total divergências encontradas:", len(df_divergencias))
print("====================================")