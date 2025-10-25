from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from docx import Document
from datetime import datetime
import os, unicodedata

def _clean(s: str) -> str:
    if not s: return ""
    s = s.replace("\xa0", " ").strip()
    s = " ".join(s.split())
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()

def _val(x, padrao="Não há."):
    return x.strip() if (x and x.strip()) else padrao

def _is_blank(cell_text: str) -> bool:
    return _clean(cell_text) == ""

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
FILES_DIR = os.path.join(BASE_DIR, "files")
os.makedirs(FILES_DIR, exist_ok=True)

TEMPLATE_MAP = {
    "sentenca": "MODELO_RELATORIO_SENTENCA.docx",
    "ms_sentenca": "MODELO_RELATORIO_MS_SENTENCA.docx",
    "acordao": "MODELO_RELATORIO_ACORDAO.docx",
    "decisao_monocratica": "MODELO_RELATORIO_DECISAO_MONOCRATICA.docx",
}

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

app = FastAPI(title="CovacIA - Relatórios Automáticos")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/gerar-json")
def gerar_json(body: RelatorioInput, x_api_key: Optional[str] = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Acesso não autorizado.")

    tipo = (body.tipo or "sentenca").lower()
    template_name = TEMPLATE_MAP.get(tipo, "MODELO_RELATORIO_SENTENCA.docx")
    template_path = os.path.join(TEMPLATES_DIR, template_name)

    if not os.path.exists(template_path):
        raise HTTPException(status_code=400, detail=f"Modelo não encontrado: {template_name}")

    doc = Document(template_path)

    dois_alias = {
        "parte requerente": "Parte requerente",
        "impetrante": "Parte requerente",
        "ies": "IES",
        "impetrada": "IES",
        "nº processo": "N.º processo",
        "n. processo": "N.º processo",
        "n processo": "N.º processo",
        "juizo": "Juízo",
        "juízo": "Juízo",
        "orgao julgador": "Juízo",
        "órgão julgador": "Juízo",
        "camara": "Juízo",
        "câmara": "Juízo",
    }

    bloco_alias = {
        "sintese dos fatos | inicial": "Síntese dos fatos | Inicial",
        "sintese dos fatos": "Síntese dos fatos",
        "informacoes": "Informações",
        "contestacao": "Contestação",
        "sentenca": "Sentença",
        "acordao": "Acórdão",
        "decisao monocratica": "Decisão Monocrática",
        "obrigacao de fazer": "Obrigação de fazer",
        "obrigacao de pagar": "Obrigação de pagar",
        "procedimento de pagamento e/ou cumprimento de obrigacao": "Procedimento de pagamento e/ou cumprimento de obrigação",
    }

    rotulo_por_tipo = {
        "sentenca": "Sentença",
        "ms_sentenca": "Sentença",
        "acordao": "Acórdão",
        "decisao_monocratica": "Decisão Monocrática",
    }
    rotulo_decisao = rotulo_por_tipo.get(tipo, "Sentença")

    texto_defesa = _val(body.informacoes, "") or body.contestacao

    dois_campos = {
        "Parte requerente": _val(body.parte_requerente),
        "IES": _val(body.ies),
        "N.º processo": _val(body.numero_processo),
        "Juízo": _val(body.juizo),
    }
    blocos = {
        "Síntese dos fatos | Inicial": _val(body.sintese),
        "Síntese dos fatos": _val(body.sintese),
        "Informações": _val(texto_defesa),
        "Contestação": _val(body.contestacao),
        "Sentença": _val(body.decisao),
        "Acórdão": _val(body.decisao),
        "Decisão Monocrática": _val(body.decisao),
        "Obrigação de fazer": _val(body.obrig_fazer),
        "Obrigação de pagar": _val(body.obrig_pagar),
        "Procedimento de pagamento e/ou cumprimento de obrigação": _val(body.procedimento),
    }

    for table in doc.tables:
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                label_raw = cell.text
                label = _clean(label_raw)
                if label in {"sentenca", "acordao", "decisao monocratica"}:
                    cell.text = rotulo_decisao

                if label in dois_alias:
                    canon = dois_alias[label]
                    target_idx = ci + 1 if (ci + 1) < len(row.cells) else (len(row.cells) - 1)
                    target_cell = row.cells[target_idx]
                    if _is_blank(target_cell.text):
                        target_cell.text = dois_campos[canon]

            for ci, cell in enumerate(row.cells):
                label = _clean(cell.text)
                if label in bloco_alias and (ri + 1) < len(table.rows):
                    chave = bloco_alias[label]
                    if chave in ["Sentença", "Acórdão", "Decisão Monocrática"]:
                        chave = rotulo_decisao
                    valor = blocos[chave]
                    for c in table.rows[ri + 1].cells:
                        if _is_blank(c.text):
                            c.text = valor

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_name = f"Relatorio_{tipo}_{stamp}.docx"
    out_path = os.path.join(FILES_DIR, out_name)
    doc.save(out_path)

    return JSONResponse({
        "status": "ok",
        "message": "Relatório gerado no modelo oficial.",
        "docx_url": f"{BASE_URL}/files/{out_name}"
    })

app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")
