from fastapi import FastAPI, HTTPException
import uvicorn
from pydantic import BaseModel
from typing import List, Dict
import os
import requests
from calendar_availability import (
    listar_event_types, 
    resolver_event_type, 
    buscar_horarios_disponiveis, 
    agendar_servico,
    remarcar_servico,
    cancelar_servico,
    CAL_BASE_URL,
    HEADERS
)

app = FastAPI(title="API de Agendamento Cal.com")


class AgendamentoRequest(BaseModel):
    nome_servico: str
    data: str  # Ex: 2024-10-25
    hora: str  # Ex: 09:00
    nome_cliente: str
    email_cliente: str



@app.get("/servicos")
def get_servicos():
    try:
        dados = listar_event_types()

        lista = [
            {
                "id": e["id"],
                "titulo": e["title"],
                "slug": e["slug"]
            }
            for e in dados.get("data", [])
        ]

        # Cria texto pronto Manychat
        servicos_formatados = " ".join(
            [f"{s['titulo']}" for s in lista]
        )

        return {
            "status": "success",
            "total": len(lista),
            "servicos": lista,
            "servicos_formatados": servicos_formatados
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "message": str(e)
        })


@app.get("/disponibilidade")
def get_disponibilidade(servico: str, data: str):
    """
    Busca horários disponíveis para um serviço em uma data específica.
    /disponibilidade?servico=Limpeza&data=2024-10-25
    """
    try:
        # 1. Resolve o serviço
        servico_info = resolver_event_type(servico)

        # 2. Busca horários
        resultado = buscar_horarios_disponiveis(servico_info, data)

        lista_slots = resultado.get("slots", [])

        horarios = [
            {
                "label": s["label"],
                "start": s["start"]
            }
            for s in lista_slots
        ]

        # Texto pronto Manychat
        horarios_formatados = " ".join(
            [f"{h['label']}" for h in horarios]
        )

        return {
            "status": "success",
            "servico": servico_info["title"],
            "data": data,
            "total": len(horarios),
            "horarios": horarios,
            "horarios_formatados": horarios_formatados
        }

    except Exception as e:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "message": str(e)
        })

    
class AgendamentoRequest(BaseModel):
    nome_servico: str
    data: str
    hora: str
    nome_cliente: str
    phone_cliente: str

@app.post("/agendar")
def post_agendar(req: AgendamentoRequest):
    try:
        reserva = agendar_servico(
            req.nome_servico,
            req.data,
            req.hora,
            req.nome_cliente,
            req.phone_cliente
        )
        return {"status": "sucesso", "data": reserva}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
class RemarcarRequest(BaseModel):
    booking_uid: str
    nova_data: str
    nova_hora: str
    nome_servico: str

@app.post("/remarcar")
def post_remarcar(req: RemarcarRequest):
    try:
        resultado = remarcar_servico(
            req.booking_uid,
            req.nova_data,
            req.nova_hora,
            req.nome_servico
        )
        return {"status": "sucesso", "data": resultado}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/cancelar")
def post_cancelar(booking_uid: str):
    try:
        resultado = cancelar_servico(booking_uid)
        return {"status": "sucesso", "data": resultado}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)