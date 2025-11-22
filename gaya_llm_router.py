import time
import json
import logging
import requests
import re

logger = logging.getLogger("GAYA_LLM_ROUTER")

# ============================================================
# CONFIGURAÇÕES DO OLLAMA
# ============================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3.1"   # leve e ideal para tua máquina


# ============================================================
# FUNÇÃO PRINCIPAL DE PROCESSAMENTO COM O LLM
# ============================================================

def processar_com_llm(pergunta: str, ferramentas: list):
    """
    Envia pergunta ao modelo local e interpreta JSON estruturado.
    Retorna sempre:
    {
        "usar_tool": str ou None,
        "args": dict,
        "resposta": str
    }
    """

    time.sleep(1)
    mensagem_sistema = f"""
Você é a Gaya, uma IA especializada em logística, transporte e análise de dados.

Quando for responder, você DEVE retornar apenas JSON puro, SEM explicações, no formato:

{
  "usar_tool": null ou "consultar_fretes",
  "resposta": "texto em português"
}

Se a pergunta precisar consultar o banco de dados, responda assim:

{
  "usar_tool": "consultar_fretes",
  "query": "status_geral"
}

Ferramentas disponíveis: {json.dumps(ferramentas)}

Nunca responda fora de JSON.
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": mensagem_sistema + "\n\nPergunta do usuário: " + pergunta,
        "temperature": 0.1,
        "stream": False
    }

    logger.debug(f"🔧 Payload enviado ao modelo: {payload}")
    time.sleep(1)

    try:
        resposta = requests.post(OLLAMA_URL, json=payload, timeout=120)

        if resposta.status_code != 200:
            logger.error(f"Erro do Ollama: {resposta.text}")
            return {"usar_tool": None, "args": {}, "resposta": "Erro ao consultar IA."}

        dados_raw = resposta.json().get("response", "").strip()
        logger.debug(f"🧠 RAW do modelo: {dados_raw}")

        # Remove possíveis blocos ```json ... ```
        dados_raw = re.sub(r"```json|```", "", dados_raw).strip()

        try:
            dados_json = json.loads(dados_raw)
        except json.JSONDecodeError:
            logger.error("❌ JSON inválido retornado pela LLM.")
            return {"usar_tool": None, "args": {}, "resposta": dados_raw}

        # Garantias de estrutura
        return {
            "usar_tool": dados_json.get("usar_tool"),
            "args": dados_json.get("args", {}),
            "resposta": dados_json.get("resposta", "")
        }

    except Exception as e:
        logger.error(f"❌ Falha ao consultar o Ollama: {e}")
        return {"usar_tool": None, "args": {}, "resposta": "Erro ao consultar o modelo local."}
