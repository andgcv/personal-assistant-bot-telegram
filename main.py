import datetime
import json
import requests
import os
from flask import Flask, request

# --- CONFIGURACAO ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

# --- FLASK SETUP PARA COMANDOS ---
app = Flask(__name__)

PRIORIDADES_PATH = "prioridades.json"

# --- HELPERS ---
def ler_prioridades():
    if not os.path.exists(PRIORIDADES_PATH):
        return {}
    with open(PRIORIDADES_PATH, "r") as f:
        return json.load(f)

def guardar_prioridades(data, nova_prioridade):
    todas = ler_prioridades()
    if data not in todas:
        todas[data] = []
    todas[data].append(nova_prioridade)
    with open(PRIORIDADES_PATH, "w") as f:
        json.dump(todas, f, indent=2, ensure_ascii=False)

def reset_prioridades(data):
    todas = ler_prioridades()
    todas[data] = []
    with open(PRIORIDADES_PATH, "w") as f:
        json.dump(todas, f, indent=2, ensure_ascii=False)

def enviar_telegram(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": texto})

def enviar_audio(texto):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": texto,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.75
        }
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        with open("audio.mp3", "wb") as f:
            f.write(r.content)
        files = {'audio': open('audio.mp3', 'rb')}
        audio_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
        requests.post(audio_url, data={"chat_id": CHAT_ID}, files=files)

# --- GERACAO DE MENSAGEM ---
def gerar_mensagem_manha():
    hoje = datetime.date.today().isoformat()
    prioridades = ler_prioridades().get(hoje, [])
    dia_semana = datetime.datetime.now().strftime('%A').capitalize()
    saudacao = f"Bom dia, André. Hoje é {dia_semana}, {hoje}."
    if prioridades:
        corpo = "\n\nAqui está o teu plano para hoje:\n" + "\n".join(f"- {p}" for p in prioridades)
    else:
        corpo = "\n\nHoje ainda não definiste prioridades. Se quiseres, posso sugerir algo."
    return saudacao + corpo

def gerar_mensagem_noite():
    hoje = datetime.date.today().isoformat()
    prioridades = ler_prioridades().get(hoje, [])
    mensagem = f"Boa noite, André. Hoje planeaste:\n" + "\n".join(f"- {p}" for p in prioridades)
    if prioridades:
        mensagem += "\n\nSe não cumpriste tudo, não faz mal. Amanhã continuamos. Que tal pores uma dessas como foco principal de amanhã?"
    else:
        mensagem += "\n\nHoje não definiste prioridades, mas podes sempre recomeçar amanhã."
    return mensagem

# --- FLUXO AUTOMATICO ---
def rotina_manha():
    texto = gerar_mensagem_manha()
    enviar_telegram(texto)
    enviar_audio(texto)

def rotina_noite():
    texto = gerar_mensagem_noite()
    enviar_telegram(texto)
    enviar_audio(texto)

# --- TELEGRAM COMANDOS ---
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    mensagem = data.get("message", {}).get("text", "")

    if mensagem.startswith("/prioridade"):
        texto = mensagem.replace("/prioridade", "").strip()
        guardar_prioridades((datetime.date.today() + datetime.timedelta(days=1)).isoformat(), texto)
        enviar_telegram("Prioridade adicionada para amanhã ✅")

    elif mensagem.startswith("/ver"):
        data = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        prioridades = ler_prioridades().get(data, [])
        if prioridades:
            enviar_telegram("Prioridades para amanhã:\n" + "\n".join(f"- {p}" for p in prioridades))
        else:
            enviar_telegram("Ainda não há prioridades para amanhã.")

    elif mensagem.startswith("/reset"):
        data = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        reset_prioridades(data)
        enviar_telegram("Prioridades para amanhã apagadas.")

    elif mensagem.startswith("/hoje"):
        texto = gerar_mensagem_manha()
        enviar_telegram(texto)

    return "ok"

# --- MAIN ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
