import os
import requests
import pytz
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict

load_dotenv()

CAL_API_KEY = os.getenv("CAL_API_KEY")
CAL_BASE_URL = os.getenv("CAL_BASE_URL")
TIMEZONE = "America/Sao_Paulo"

HEADERS = {
    "Authorization": f"Bearer {CAL_API_KEY}",
    "Content-Type" : "application/json"
}


def listar_event_types() -> Dict:
    HEADERS["cal-api-version"] = "2024-06-14"

    r = requests.get(
        f"{CAL_BASE_URL}/v2/event-types",
        headers=HEADERS
    )

    if r.status_code != 200:
        raise RuntimeError(
            f"Erro ao listar event types ({r.status_code}): {r.text}"
        )

    return r.json()



def resolver_event_type(nome_servico: str) -> Dict:
    nome = nome_servico.strip().lower()
    event_types = listar_event_types().get("data", [])

    for e in event_types:
        if e["title"].lower() == nome:
            if not e.get("users"):
                raise RuntimeError("Event type sem usuários")

            user = e["users"][0]
            username = user["username"] if isinstance(user, dict) else user

            return {
                "eventTypeId": e["id"],
                "title": e["title"],
                "username": username,
                "duration": e["lengthInMinutes"],
            }

    raise ValueError("Serviço não encontrado")

def buscar_horarios_disponiveis(servico: Dict, data: str) -> Dict:
    datetime.strptime(data, "%Y-%m-%d")

    params = {
        "eventTypeId": servico["eventTypeId"],
        "start": f"{data}T00:00:00-03:00",
        "end": f"{data}T23:59:59-03:00",
        "timeZone": TIMEZONE,
    }

    HEADERS["cal-api-version"] = "2024-09-04"

    r = requests.get(
        f"{CAL_BASE_URL}/v2/slots",
        headers=HEADERS,
        params=params
    )

    if r.status_code != 200:
        raise RuntimeError(
            f"Erro slots ({r.status_code}): {r.text}"
        )

    data_slots = r.json().get("data", {})

    slots = []
    for _, horarios in data_slots.items():
        for h in horarios:
            start = h["start"]
            end = h.get("end")

            label = datetime.fromisoformat(
                start.replace("Z", "")
            ).strftime("%H:%M")

            slots.append({
                "start": start,
                "end": end,
                "label": label,
            })

    return {"slots": slots}

def normalizar_slot_start(slot_start: str) -> str:
    """
    Converte:
    2026-02-10T07:40:00.000-03:00
    para:
    2026-02-10T10:40:00Z
    """
    dt = datetime.fromisoformat(slot_start)
    dt_utc = dt.astimezone(pytz.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

def agendar_servico(nome_servico: str, data: str, hora: str, nome: str, phone:str) -> Dict:
    HEADERS["cal-api-version"] = "2024-08-13"

    servico = resolver_event_type(nome_servico)
    disponibilidade = buscar_horarios_disponiveis(servico, data)

    slot = next(
        (s for s in disponibilidade["slots"] if s["label"] == hora),
        None,
    )

    if not slot:
        raise RuntimeError("Horário indisponível")

    payload = {
        "eventTypeId": servico["eventTypeId"],
        "start": slot["start"],
        "attendee": {
            "name": nome,
            "timeZone": TIMEZONE,
            "phoneNumber": phone,
        },
        "metadata": {"origem": "teste"},
        "location": {"type": "address"},
    }

    HEADERS["cal-api-version"] = "2024-08-13"

    r = requests.post(
        f"{CAL_BASE_URL}/v2/bookings",
        json=payload,
        headers=HEADERS
    )

    if r.status_code not in (200, 201):
        raise RuntimeError(r.text)

    return r.json()

def remarcar_servico(booking_uid: str, nova_data:str, nova_hora:str, nome_servico: str) -> Dict:
    HEADERS["cal-api-version"] = "2024-08-13"

    servico = resolver_event_type(nome_servico)
    
    disponibilidade = buscar_horarios_disponiveis(servico, nova_data)

    slot = next(
        (s for s in disponibilidade["slots"] if s["label"] == nova_hora),
        None,
    )

    if not slot:
        raise RuntimeError("Horário indisponível")
    
    start_utc = normalizar_slot_start(slot["start"])

    HEADERS["cal-api-version"] = "2024-08-13"
    
    payload = {
        "start": start_utc,
    }

    r = requests.post(
        f"{CAL_BASE_URL}/v2/bookings/{booking_uid}/reschedule",
        headers=HEADERS,
        json=payload
    )

    if r.status_code not in (200, 201):
        raise RuntimeError(r.text)

    return r.json()

def cancelar_servico(booking_uid: str) -> Dict:
    HEADERS["cal-api-version"] = "2024-08-13"

    payload = {
    "cancellationReason": "Cancelamento via AIA - Assistente Virtual  "
    }


    r = requests.post(
        f"{CAL_BASE_URL}/v2/bookings/{booking_uid}/cancel",
        headers=HEADERS,
        json=payload
    )

    if r.status_code not in (200, 204):
        raise RuntimeError(r.text)

    return {"status": "cancelado"}