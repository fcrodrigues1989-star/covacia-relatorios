
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os

app = FastAPI(title="CovacIA API")

API_KEY = os.getenv("API_KEY", "COVAC2025")
BASE_URL = os.getenv("BASE_URL", "")  # ex.: https://covacia-relatorios.onrender.com

FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")
os.makedirs(FILES_DIR, exist_ok=True)

class RelatorioInput(BaseModel):
    tipo: str = "sentenca"
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

def _auth_ok(request: Request, x_api_key: Optional[str], expected: Optional[str]) -> bool:
    if not expected:
        return True
    # X-API-Key direto
    if x_api_key and x_api_key.strip() == expected:
        return True
    # Authorization: Bearer <token>
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        if token == expected:
            return True
    return False

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/gerar-json")
def gerar_json(body: RelatorioInput, request: Request, x_api_key: Optional[str] = Header(default=None)):
    if not _auth_ok(request, x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Acesso não autorizado.")
    # Simulação: cria um arquivo .docx vazio para testar o download
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"Relatorio_{body.tipo}_{stamp}.docx"
    caminho = os.path.join(FILES_DIR, nome)
    with open(caminho, "wb") as f:
        f.write(b"Relatorio de teste (conteudo simulado).")
    link = f"{BASE_URL}/files/{nome}" if BASE_URL else f"/files/{nome}"
    return JSONResponse({"status": "ok", "message": "Relatório gerado no modelo oficial.", "docx_url": link})

# Servir arquivos persistentes
app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")
