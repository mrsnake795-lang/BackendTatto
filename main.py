import os
import requests
import re
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
EMAILJS_USER_ID = os.getenv("EMAILJS_USER_ID")
EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID")
EMAILJS_TEMPLATE_ID = os.getenv("EMAILJS_TEMPLATE_ID")
EMAILJS_PRIVATE_KEY = os.getenv("EMAILJS_PRIVATE_KEY")

if not all([EMAILJS_USER_ID, EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, EMAILJS_PRIVATE_KEY]):
    raise ValueError("Variáveis de ambiente do EmailJS não configuradas corretamente.")

@app.get('/years-experience')
async def calculate_years_experience() -> int:
    start = 2020
    now = datetime.now().year
    return now - start

@app.get('/api/instagram-feed')
async def get_instagram_feed() -> Dict[str, Any]:
    if not INSTAGRAM_ACCESS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token do Instagram não configurado."
        )

    url = (
        f"https://graph.instagram.com/me/media?"
        f"fields=id,caption,media_type,media_url,permalink,thumbnail_url&"
        f"access_token={INSTAGRAM_ACCESS_TOKEN}"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar feed do Instagram: {str(e)}"
        )

@app.post('/api/send-email')
async def send_email(request: Request):
    try:
        form_data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Corpo do pedido inválido: {str(e)}")

    if not form_data.get("user_name"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome é obrigatório.")

    if not form_data.get("message"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mensagem é obrigatória.")

    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    user_email = form_data.get("user_email", "")

    if not form_data.get("user_mobile") and not user_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pelo menos um contacto (telemóvel ou email) é obrigatório.")

    if user_email and not re.match(email_pattern, user_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email inválido.")

    payload = {
        "service_id": EMAILJS_SERVICE_ID,
        "template_id": EMAILJS_TEMPLATE_ID,
        "user_id": EMAILJS_USER_ID,
        "accessToken": EMAILJS_PRIVATE_KEY,
        "template_params": {
            "user_name": form_data.get("user_name", "")[:100],
            "user_mobile": form_data.get("user_mobile", "")[:30],
            "user_email": user_email,
            "message": form_data.get("message", "")[:2000]
        }
    }

    try:
        response = requests.post(
            "https://api.emailjs.com/api/v1.0/email/send",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        print(f"Resposta Completa: {response.text}")
        response.raise_for_status()
        return {"status": "success", "message": "E-mail enviado com sucesso!"}
    except requests.exceptions.HTTPError as err:
        print(f"Erro HTTP do EmailJS: {err}")
        print(f"Resposta: {response.text}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao enviar e-mail: {response.text}")
    except Exception as e:
        print(f"Erro: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao enviar e-mail: {str(e)}")