import pandas as pd
from database import get_connection
from unidecode import unidecode

# ==========================================
# 1️⃣ LER PLANILHA
# ==========================================

arquivo = "comissao_planilha_tratada_moveis_saldo.xlsx"

df = pd.read_excel(arquivo)

# padronizar nomes de colunas
df.columns = (
    df.columns
    .str.lower()
    .str.strip()
    .str.replace(" ", "_")
)

print("Colunas encontradas:")
print(df.columns)

# ==========================================
# 2️⃣ GRUPO MOVEIS
# ==========================================

df_moveis = df[[
    "loja",
    "nome",
    "funcao",
    "valor_total_moveis",
    "comissao_moveis"
]].copy()

df_moveis["grupo"] = "M"

df_moveis = df_moveis.rename(columns={
    "nome": "vendedor",
    "valor_total_moveis": "valor_total",
    "comissao_moveis": "comissao"
})

# ==========================================
# 3️⃣ GRUPO SALDO
# ==========================================

df_saldo = df[[
    "loja",
    "nome",
    "funcao",
    "valor_total_saldo",
    "comissao_saldo"
]].copy()

df_saldo["grupo"] = "S"

df_saldo = df_saldo.rename(columns={
    "nome": "vendedor",
    "valor_total_saldo": "valor_total",
    "comissao_saldo": "comissao"
})

# ==========================================
# 4️⃣ JUNTAR PLANILHA
# ==========================================

df_planilha = pd.concat([df_moveis, df_saldo], ignore_index=True)

df_planilha["vendedor"] = df_planilha["vendedor"].apply(unidecode)

# converter valores para número
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

df_planilha["vendedor"] = (
    df_planilha["vendedor"]
    .astype(str)
    .str.strip()
    .str.upper()
)

df_planilha["valor_total"] = pd.to_numeric(df_planilha["valor_total"], errors="coerce").fillna(0)
df_planilha["comissao"] = pd.to_numeric(df_planilha["comissao"], errors="coerce").fillna(0)

df_planilha["valor_total"] = df_planilha["valor_total"].fillna(0)
df_planilha["comissao"] = df_planilha["comissao"].fillna(0)

# ==========================================
# 5️⃣ PADRONIZAR NOMES
# ==========================================

# ==========================================
# 6️⃣ CONECTAR NO BANCO
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
                    WHEN mapavenda.grupo IN ('E','C','P') THEN 0
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
AND mapavenda.grupo IN ('S','M')

GROUP BY
    mapavenda.storeno,
    emp.name,
    mapavenda.grupo

"""

df_api = pd.read_sql(query, conn)

df_api["vendedor"] = df_api["vendedor"].apply(unidecode)

print("\nDADOS DO BANCO:")
print(df_api.head())
print("Total linhas banco:", len(df_api))

df_api["valor_total"] = pd.to_numeric(df_api["valor_total"], errors="coerce").fillna(0)
df_api["comissao"] = pd.to_numeric(df_api["comissao"], errors="coerce").fillna(0)

conn.close()

# ==========================================
# 7️⃣ PADRONIZAR BANCO
# ==========================================

df_api["loja"] = (
    df_api["loja"]
    .astype(str)
    .str.strip()
    .astype(int)
)

df_api["loja"] = df_api["loja"].astype(int)

df_api["grupo"] = (
    df_api["grupo"]
    .astype(str)
    .str.strip()
    .str.upper()
)

df_api["vendedor"] = (
    df_api["vendedor"]
    .astype(str)
    .str.strip()
    .str.upper()
)

# ==========================================
# 8️⃣ AGRUPAR BANCO
# ==========================================

df_api = df_api.groupby(
    ["loja", "vendedor", "grupo"],
    as_index=False
).agg({
    "valor_total": "sum",
    "comissao": "sum"
})

df_planilha["valor_total"] = df_planilha["valor_total"].round(2)
df_planilha["comissao"] = df_planilha["comissao"].round(2)

df_api["valor_total"] = df_api["valor_total"].round(2)
df_api["comissao"] = df_api["comissao"].round(2)

# ==========================================
# 9️⃣ COMPARAR PLANILHA X BANCO
# ==========================================

print("\nVENDEDORES PLANILHA:")
print(df_planilha[["loja","vendedor","grupo"]].drop_duplicates().head(10))

print("\nVENDEDORES BANCO:")
print(df_api[["loja","vendedor","grupo"]].drop_duplicates().head(10))

chaves_planilha = set(
    df_planilha["loja"].astype(str) + "|" +
    df_planilha["vendedor"] + "|" +
    df_planilha["grupo"]
)

chaves_banco = set(
    df_api["loja"].astype(str) + "|" +
    df_api["vendedor"] + "|" +
    df_api["grupo"]
)

df_planilha["loja"] = df_planilha["loja"].astype(int)

print("\nChaves só na planilha:", len(chaves_planilha - chaves_banco))
print("Chaves só no banco:", len(chaves_banco - chaves_planilha))

df_final = df_planilha.merge(
    df_api,
    on=["loja", "vendedor", "grupo"],
    how="left",
    suffixes=("_planilha", "_banco")
)

df_final["valor_total_banco"] = df_final["valor_total_banco"].fillna(0)
df_final["comissao_banco"] = df_final["comissao_banco"].fillna(0)

# ==========================================
# 🔟 CALCULAR DIFERENÇAS
# ==========================================

df_final["dif_valor"] = (
    df_final["valor_total_planilha"] - df_final["valor_total_banco"]
)

df_final["dif_comissao"] = (
    df_final["comissao_planilha"] - df_final["comissao_banco"]
)

nao_encontrados = df_final[df_final["valor_total_banco"].isna()]

print("\nVENDEDORES NAO ENCONTRADOS NO BANCO:")
print(nao_encontrados[["loja","vendedor","grupo"]].head(20))

# ==========================================
# 1️⃣1️⃣ FILTRAR DIVERGENCIAS
# ==========================================

df_divergencias = df_final[
    (df_final["dif_valor"] != 0) |
    (df_final["dif_comissao"] != 0)
]

# ==========================================
# 1️⃣2️⃣ EXPORTAR RESULTADOS
# ==========================================

df_final.to_excel("comparacao_completa.xlsx", index=False)

df_divergencias.to_excel("divergencias_comissao.xlsx", index=False)

# ==========================================
# FINAL
# ==========================================

print("====================================")
print("✔ Comparação finalizada")
print("Arquivo completo: comparacao_completa.xlsx")
print("Arquivo divergencias: divergencias_comissao.xlsx")
print("Total divergências encontradas:", len(df_divergencias))
print("====================================")