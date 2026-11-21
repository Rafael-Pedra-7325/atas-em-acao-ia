import json
import re
import time
from typing import Dict, List
import requests

GEMINI_REST_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.8-flash:generateContent"
)


def extrair_tarefas_via_rest(notas_reuniao: str, api_key: str) -> List[Dict]:
    """Consome a API REST do Gemini com retry e timeout resiliente para extrair tarefas em JSON."""
    if not api_key or not api_key.strip():
        raise ValueError("Chave de API não informada. Configure a GEMINI_API_KEY na barra lateral.")

    prompt = f"""
    Você é um assistente de gestão de projetos. Analise as anotações de reunião abaixo e extraia
    todas as tarefas acionáveis em um array JSON válido.

    Regras estritas:
    - Retorne APENAS um array JSON onde cada objeto tenha exatamente estas chaves:
      "descricao" (string objetiva da ação),
      "responsavel" (nome da pessoa responsável ou "A definir"),
      "prazo" (prazo mencionado ou "A definir"),
      "prioridade" ("Alta", "Média" ou "Baixa").
    - Não invente tarefas que não estejam implícitas ou explícitas no texto.

    Anotações da reunião:
    \"\"\"{notas_reuniao}\"\"\"
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1024,
            "responseMimeType": "application/json",
        },
    }

    url = f"{GEMINI_REST_URL}?key={api_key.strip()}"
    headers = {"Content-Type": "application/json"}

    ultima_excecao = None
    for tentativa in range(1, 3):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(10, 60),  # 10s para conectar, 60s para aguardar a resposta
            )

            if response.status_code == 200:
                data = response.json()
                texto_resposta = data["candidates"][0]["content"]["parts"][0]["text"]
                texto_limpo = re.sub(r"^```json\s*|\s*```$", "", texto_resposta.strip())
                tarefas = json.loads(texto_limpo)

                if not isinstance(tarefas, list):
                    raise ValueError("A API não retornou uma lista válida de tarefas.")

                return tarefas

            if response.status_code in (429, 500, 502, 503, 504) and tentativa < 2:
                time.sleep(2)
                continue

            raise RuntimeError(
                f"Erro na API REST (HTTP {response.status_code}): {response.text[:250]}"
            )

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            ultima_excecao = exc
            if tentativa < 2:
                time.sleep(2)
                continue
            raise RuntimeError(
                "A API do Gemini demorou mais que o esperado para responder. Tente novamente em instantes."
            ) from ultima_excecao

    return []
