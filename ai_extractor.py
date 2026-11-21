import json
import re
from typing import Dict, List
import requests

GEMINI_REST_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)


def extrair_tarefas_via_rest(notas_reuniao: str, api_key: str) -> List[Dict]:
    """Consome a API REST do Gemini para converter notas livres em uma lista JSON de tarefas."""
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
            "responseMimeType": "application/json",
        },
    }

    response = requests.post(
        f"{GEMINI_REST_URL}?key={api_key.strip()}",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=25,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Erro na API REST (HTTP {response.status_code}): {response.text[:250]}"
        )

    data = response.json()
    texto_resposta = data["candidates"][0]["content"]["parts"][0]["text"]

    # Limpeza preventiva caso venha cercado por blocos markdown
    texto_limpo = re.sub(r"^```json\s*|\s*```$", "", texto_resposta.strip())
    tarefas = json.loads(texto_limpo)

    if not isinstance(tarefas, list):
        raise ValueError("A API não retornou uma lista válida de tarefas.")

    return tarefas
