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
Você é Gaya, uma IA especialista em logística, transporte e análise de dados.
Você SEMPRE responde em JSON P U R O, sem texto fora do JSON.

Formato OBRIGATÓRIO da resposta:
{{
  "usar_tool": null OU "nome_da_tool",
  "args": {{ ... }},
  "resposta": "texto final aqui"
}}

REGRAS IMPORTANTES:
- Nunca escreva nada fora do JSON.
- Nunca escreva comentários.
- Nunca escreva explicações antes ou depois do JSON.
- Se decidir usar uma ferramenta, preencha "usar_tool" com o nome dela.
- SEMPRE inclua "args": se não houver argumentos, envie args: {{}}
- Ferramentas disponíveis: {json.dumps(ferramentas)}
- Para consultar o banco de dados use: "consultar_fretes"
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
