import json
import re
import time
from typing import Dict, List
import requests

BASE_API_URL = "https://generativelanguage.googleapis.com/v1beta"
MODELO_PRINCIPAL = "gemini-3.8-flash"


class _ModeloIndisponivelError(Exception):
    """Exceção interna para acionar retry ou fallback para outro modelo."""


def _chamar_modelo(modelo: str, prompt: str, api_key: str) -> List[Dict]:
    url = f"{BASE_API_URL}/models/{modelo}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1024,
            "responseMimeType": "application/json",
        },
    }

    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=(10, 60),
        )
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
        raise _ModeloIndisponivelError(f"Timeout ao chamar {modelo}") from exc

    if response.status_code == 200:
        data = response.json()
        texto_resposta = data["candidates"][0]["content"]["parts"][0]["text"]
        texto_limpo = re.sub(r"^```json\s*|\s*```$", "", texto_resposta.strip())
        tarefas = json.loads(texto_limpo)

        if not isinstance(tarefas, list):
            raise ValueError("A API não retornou uma lista válida de tarefas.")
        return tarefas

    if response.status_code in (404, 429, 500, 502, 503, 504):
        raise _ModeloIndisponivelError(
            f"Modelo {modelo} indisponível (HTTP {response.status_code})"
        )

    raise RuntimeError(
        f"Erro na API REST (HTTP {response.status_code}): {response.text[:250]}"
    )


def _buscar_modelos_fallback(api_key: str, excluir: str) -> List[str]:
    """Consulta a API REST para descobrir modelos Gemini atuais ativos na chave."""
    try:
        resp = requests.get(f"{BASE_API_URL}/models?key={api_key}", timeout=10)
        if resp.status_code != 200:
            return []

        modelos_validos = []
        termos_ignorados = (
            "embedding",
            "imagen",
            "veo",
            "tts",
            "aqa",
            "robotics",
            "1.0",
            "1.5",
            "2.0",
            "2.5",
        )

        for item in resp.json().get("models", []):
            nome = item.get("name", "").replace("models/", "")
            metodos = item.get("supportedGenerationMethods", [])
            if (
                "generateContent" in metodos
                and "gemini" in nome.lower()
                and nome != excluir
                and not any(t in nome.lower() for t in termos_ignorados)
            ):
                modelos_validos.append(nome)

        # Prioriza variantes flash/lite atuais
        modelos_validos.sort(
            key=lambda m: (0 if ("flash" in m or "lite" in m) else 1, m)
        )
        return modelos_validos[:6]
    except Exception:
        return []


def extrair_tarefas_via_rest(notas_reuniao: str, api_key: str) -> List[Dict]:
    """Consome a API REST do Gemini com retry e fallback automático entre modelos."""
    if not api_key or not api_key.strip():
        raise ValueError("Chave de API não informada. Configure a GEMINI_API_KEY na barra lateral.")

    chave = api_key.strip()
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

    ultimo_erro = None

    # 1. Tenta o modelo principal (com 1 retry rápido em caso de pico momentâneo)
    for tentativa in range(1, 3):
        try:
            return _chamar_modelo(MODELO_PRINCIPAL, prompt, chave)
        except _ModeloIndisponivelError as exc:
            ultimo_erro = exc
            if tentativa < 2:
                time.sleep(2)

    # 2. Aciona fallback automático apenas entre modelos atuais da conta
    for modelo_alt in _buscar_modelos_fallback(chave, excluir=MODELO_PRINCIPAL):
        try:
            return _chamar_modelo(modelo_alt, prompt, chave)
        except _ModeloIndisponivelError as exc:
            ultimo_erro = exc
            continue

    raise RuntimeError(
        f"Os modelos da API gratuita estão temporariamente sobrecarregados ({ultimo_erro}). "
        "Aguarde alguns segundos e clique novamente."
    )
