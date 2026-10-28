from pydantic import BaseModel, Field
from typing import List

class DetalhesImagemModelo(BaseModel):
    titulo: str = Field(
        description="Título resumido da imagem."
    )

    descricao: str = Field(
        description="Descrição detalhada do conteúdo da imagem."
    )

    rotulos: List[str] = Field(
        min_length=3,
        max_length=3,
        description="Exatamente três rótulos relevantes para a imagem."
    )