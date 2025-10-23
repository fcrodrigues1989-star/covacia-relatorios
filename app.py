# app.py — CovacIA Relatórios Online (versão direta + BASE_URL)
# --------------------------------------------------------------
# Esta versão gera relatórios jurídicos nos modelos oficiais da Covac.
# Agora com BASE_URL configurável para que os links retornem completos (clicáveis).

from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from docx import Document
from datetime import datetime
import os

# --------------------------------------------------------------
# CONFIGURAÇÕES INICIAIS
# --------------------------------------------------------------
API_KEY = os.getenv("API_KEY")  # chave opcional para controle de acesso
BASE_URL = os.getenv("BASE_URL", "")  # endereço base do Render (ex: https://covacia-relatorios.onrender.com)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
FILES_DIR = os.path.join(BASE_DIR, "files")
os.makedirs(FILES_DIR, exist_ok=True)

TEMPLATE_MAP = {
    "sentenca": "MODELO_RELATORIO_SENTENCA.docx",
    "acordo": "MODELO_RELATORIO_ACORDO.docx",
    "ms_sentenca": "MODELO_RELATORIO_MS_SENTENCA.docx",
    "acordao": "MODELO_RELATORIO_ACORDAO.docx",
    "decisao_monocratica": "MODELO_RELATORIO_DECISAO_MONOCRATICA.docx",
}

# --------------------------------------------------------------
# MODELO DE DADOS
# --------------------------------------------------------------
class RelatorioInput(BaseModel):
    tipo: Optional[str] = "sentenca"
    parte_requerente: Optional[str] = None
    ies: Optional[str] = None
    numero_processo: Optional[str] = None
    juizo: Optional[str] = None
    sintese: Optional[str] = None
    contestacao: Optional[str] = None
    informacoes: Optional[str] = None
    decisao: Optional[str] = None
    obrig_fazer: Optional[str] = None
    obrig_pagar: Optional[str] = None
    procedimento: Optional[str] = None

# --------------------------------------------------------------
# FUNÇÃO AUXILIAR
# --------------------------------------------------------------
def _val(x: Optional[str], padrao: str = "Não há.") -> str:
    return x.strip() if (x and x.strip()) else padrao

# --------------------------------------------------------------
# APP FASTAPI
# --------------------------------------------------------------
app = FastAPI(title="CovacIA – Gerador de Relatórios (Online)")

@app.get("/health")
def health():
    return {"status": "ok"}

# --------------------------------------------------------------
# ENDPOINT PRINCIPAL — /gerar-json
# --------------------------------------------------------------
@app.post("/gerar-json")
def gerar_json(body: RelatorioInput, x_api_key: Optional[str] = Header(default=None)):
    # segurança opcional
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Acesso não autorizado (X-API-Key ausente ou incorreta)")

    tipo = (body.tipo or "sentenca").lower()
    template_name = TEMPLATE_MAP.get(tipo)
    if not template_name:
        raise HTTPException(status_code=400, detail="Tipo inválido. Use: sentenca, acordo, ms_sentenca, acordao, decisao_monocratica.")
    
    template_path = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.exists(template_path):
        raise HTTPException(status_code=400, detail=f"Modelo não encontrado: {template_name}")

    doc = Document(template_path)

    dois_campos = {
        "Parte requerente": _val(body.parte_requerente),
        "IES": _val(body.ies),
        "N.º processo": _val(body.numero_processo),
        "Nº processo": _val(body.numero_processo),
        "Juízo": _val(body.juizo),
        "Juizo": _val(body.juizo),
    }

    rotulo_por_tipo = {
        "sentenca": "Sentença",
        "acordo": "Sentença",
        "ms_sentenca": "Sentença",
        "acordao": "Acórdão",
        "decisao_monocratica": "Decisão Monocrática",
    }
    rotulo_decisao = rotulo_por_tipo.get(tipo, "Sentença")

    texto_defesa = body.informacoes if _val(body.informacoes, "") else body.contestacao

    blocos = {
        "Síntese dos fatos": _val(body.sintese),
        "Síntese dos fatos | Inicial": _val(body.sintese),
        "Informações": _val(texto_defesa),
        "Sentença": _val(body.decisao),
        "Acórdão": _val(body.decisao),
        "Decisão Monocrática": _val(body.decisao),
        "Obrigação de fazer": _val(body.obrig_fazer),
        "Obrigação de pagar": _val(body.obrig_pagar),
        "Procedimento de pagamento e/ou cumprimento de obrigação": _val(body.procedimento),
    }

    for table in doc.tables:
        for ri, row in enumerate(table.rows):
            row_text = " | ".join(c.text.strip() for c in row.cells)
            for ci, cell in enumerate(row.cells):
                label = cell.text.strip()
                if label in dois_campos and ci + 1 < len(row.cells):
                    row.cells[ci+1].text = dois_campos[label]
                if label in ["Sentença", "Acórdão", "Decisão Monocrática"]:
                    cell.text = rotulo_decisao

            labels_blocos = [
                "Síntese dos fatos | Inicial", "Síntese dos fatos", "Informações",
                "Sentença", "Acórdão", "Decisão Monocrática",
                "Obrigação de fazer", "Obrigação de pagar",
                "Procedimento de pagamento e/ou cumprimento de obrigação"
            ]
            for lb in labels_blocos:
                if lb in row_text and ri + 1 < len(table.rows):
                    chave = "Sentença" if lb in ["Sentença","Acórdão","Decisão Monocrática"] else lb
                    valor = blocos[chave]
                    for c in table.rows[ri+1].cells:
                        c.text = valor

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_name = f"Relatorio_{tipo}_{stamp}.docx"
    out_path = os.path.join(FILES_DIR, out_name)
    doc.save(out_path)

    # 🔗 Retorno agora vem com o link completo
    return JSONResponse({
        "status": "ok",
        "message": "Relatório gerado no modelo oficial.",
        "docx_url": f"{BASE_URL}/files/{out_name}"
    })

# --------------------------------------------------------------
# ARQUIVOS GERADOS — /files
# --------------------------------------------------------------
app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")

