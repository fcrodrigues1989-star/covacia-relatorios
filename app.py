
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

app = FastAPI()

API_KEY = os.getenv("API_KEY", "COVAC2025")

class RelatorioInput(BaseModel):
    tipo: str
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
    if x_api_key and x_api_key.strip() == expected:
        return True
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        if token == expected:
            return True
    return False

@app.post("/gerar-json")
def gerar_json(body: RelatorioInput, request: Request, x_api_key: Optional[str] = Header(default=None)):
    if not _auth_ok(request, x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Acesso não autorizado.")
    
    # Exemplo de geração de arquivo DOCX (simulado)
    nome_arquivo = f"Relatorio_{body.tipo}_teste.docx"
    caminho = f"/tmp/{nome_arquivo}"
    with open(caminho, "w") as f:
        f.write("Relatório gerado com sucesso (simulação).")
    
    return {"status": "ok", "message": "Relatório gerado no modelo oficial.", "docx_url": f"/files/{nome_arquivo}"}

@app.get("/files/{file_name}")
def baixar_arquivo(file_name: str):
    caminho = f"/tmp/{file_name}"
    if not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(caminho, filename=file_name)
