from pydantic import BaseModel


class Venda(BaseModel):
    storeno: int
    vendno: int
    vendedor: str
    grupo: str
    valor_total: float
    margem: float | None
    percentual_comissao: float
    comissao: float