# app.py — versão compatível com /docs e link público
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from docx import Document
from datetime import datetime
import os

# (opcional) ative uma chave de acesso simples
API_KEY = os.getenv("API_KEY")  # defina no Render, se quiser proteger

FILES_DIR = "./files"
os.makedirs(FILES_DIR, exist_ok=True)

class RelatorioInput(BaseModel):
    parte_requerente: str | None = None
    ies: str | None = None
    numero_processo: str | None = None
    juizo: str | None = None
    sintese: str | None = None
    contestacao: str | None = None
    decisao: str | None = None   # sentença / acórdão / decisão monocrática (texto)
    obrig_fazer: str | None = None
    obrig_pagar: str | None = None
    procedimento: str | None = None
    tipo: str = "sentença"       # "sentença" | "acórdão" | "decisão monocrática"

app = FastAPI(title="CovacIA – Gerador de Relatórios (online)")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/gerar-json")
def gerar_json(body: RelatorioInput, x_api_key: str | None = Header(default=None)):
    # Se quiser travar o acesso por chave, defina API_KEY no Render e descomente:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Acesso não autorizado (X-API-Key ausente/errada)")

    template = "MODELO RELATÓRIO DE SENTENÇA.docx"
    if not os.path.exists(template):
        raise HTTPException(status_code=400, detail="Modelo .docx não encontrado na pasta do app.")

    def val(x, padrao="Não há."):
        return x.strip() if (x and x.strip()) else padrao

    doc = Document(template)

    dois_campos = {
        "Parte requerente": val(body.parte_requerente),
        "IES": val(body.ies),
        "N.º processo": val(body.numero_processo),
        "Nº processo": val(body.numero_processo),
        "Juízo": val(body.juizo),
        "Juizo": val(body.juizo),
    }

    rotulo_tipo = {"sentença": "Sentença", "acórdão": "Acórdão", "decisão monocrática": "Decisão Monocrática"}
    rotulo_decisao = rotulo_tipo.get(body.tipo.lower(), "Sentença")

    blocos = {
        "Síntese dos fatos": val(body.sintese),
        "Síntese dos fatos | Inicial": val(body.sintese),
        "Informações": val(body.contestacao),
        "Sentença": val(body.decisao),
        "Acórdão": val(body.decisao),
        "Decisão Monocrática": val(body.decisao),
        "Obrigação de fazer": val(body.obrig_fazer),
        "Obrigação de pagar": val(body.obrig_pagar),
        "Procedimento de pagamento e/ou cumprimento de obrigação": val(body.procedimento),
    }

    for table in doc.tables:
        for ri, row in enumerate(table.rows):
            row_text = " | ".join(c.text.strip() for c in row.cells)

            # 1) dois campos (rótulo à esquerda, valor à direita)
            for ci, cell in enumerate(row.cells):
                label = cell.text.strip()
                if label in dois_campos and ci + 1 < len(row.cells):
                    row.cells[ci+1].text = dois_campos[label]
                # renomeia rótulo decisório conforme tipo
                if label in ["Sentença", "Acórdão", "Decisão Monocrática"]:
                    cell.text = rotulo_decisao

            # 2) blocos (linha de baixo)
            labels_blocos = [
                "Síntese dos fatos | Inicial", "Síntese dos fatos",
                "Informações", "Sentença", "Acórdão", "Decisão Monocrática",
                "Obrigação de fazer", "Obrigação de pagar",
                "Procedimento de pagamento e/ou cumprimento de obrigação"
            ]
            for lb in labels_blocos:
                if lb in row_text and ri + 1 < len(table.rows):
                    # se for rótulo da decisão, usa o texto da chave 'decisao'
                    chave = "Sentença" if lb in ["Sentença","Acórdão","Decisão Monocrática"] else lb
                    valor = blocos[chave]
                    for c in table.rows[ri+1].cells:
                        c.text = valor

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_name = f"Relatorio_{body.tipo}_{stamp}.docx"
    out_path = os.path.join(FILES_DIR, out_name)
    doc.save(out_path)

    return JSONResponse({
        "status": "ok",
        "message": "Relatório gerado no modelo oficial.",
        "docx_url": f"/files/{out_name}"
    })

# pasta pública para baixar os arquivos
app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")
