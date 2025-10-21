from fastapi import FastAPI
from docx import Document
from fastapi.responses import FileResponse
import os

app = FastAPI()

@app.post("/gerar")
def gerar_relatorio():
    modelo = "MODELO RELATÓRIO DE SENTENÇA.docx"
    doc = Document(modelo)

    # Exemplo de preenchimento
    for tabela in doc.tables:
        for linha in tabela.rows:
            if "Parte requerente" in linha.cells[0].text:
                linha.cells[1].text = "Caroline Felix dos Santos"
            if "IES" in linha.cells[0].text:
                linha.cells[1].text = "SECID – Sociedade Educacional Cidade de São Paulo (UNICID)"
            if "N.º processo" in linha.cells[0].text:
                linha.cells[1].text = "1105335-48.2024.8.26.0002"
            if "Juízo" in linha.cells[0].text:
                linha.cells[1].text = "13ª Vara Cível do Foro Regional II – Santo Amaro – SP"

    saida = "Relatorio_Preenchido.docx"
    doc.save(saida)
    return FileResponse(saida)
