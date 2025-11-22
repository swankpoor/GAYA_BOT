import time
import json
import logging
import requests

logger = logging.getLogger("GAYA_LLM_ROUTER")


# ============================================================
# CONFIGURAÇÕES DO OLLAMA
# ============================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3.2:1b"   # modelo leve e rápido, ideal para CPU fraca


# ============================================================
# FUNÇÃO PRINCIPAL DE PROCESSAMENTO COM O LLM
# ============================================================

def processar_com_llm(pergunta: str, ferramentas: list):
    """
    Envia a pergunta e o contexto de ferramentas ao modelo LLM local (Ollama).
    Interpreta se a IA deseja usar uma tool ou responder diretamente.
    
    Retorna:
      {
         "usar_tool": "nome_da_tool"  ou  None,
         "resposta": "texto da resposta"
      }
    """

    time.sleep(1)

    mensagem_sistema = f"""
Você é a Gaya, uma IA especializada em logística, transporte e análise de dados.
Se precisar consultar o banco de dados, peça para usar uma ferramenta do tipo: usar_tool: nome_da_tool.
Ferramentas disponíveis: {json.dumps(ferramentas)}
Se não precisar, responda diretamente em português natural.
IMPORTANTE:
Sempre responda em JSON válido com:
{{
  "usar_tool": null OU "nome_da_tool",
  "resposta": "texto"
}}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": mensagem_sistema + "\n\nPergunta do usuário: " + pergunta,
        "temperature": 0.2,
        "stream": False
    }

    logger.debug(f"🔧 Enviando payload para Ollama: {payload}")
    time.sleep(1)

    try:
        resposta = requests.post(OLLAMA_URL, json=payload, timeout=120)

        if resposta.status_code != 200:
            logger.error(f"Erro do Ollama: {resposta.text}")
            return {"usar_tool": None, "resposta": "Erro ao consultar IA."}

        dados = resposta.json().get("response", "").strip()
        logger.debug(f"🧠 Resposta RAW da LLM: {dados}")

        # Tentar interpretar o JSON enviado pela IA
        try:
            dados_json = json.loads(dados)
        except json.JSONDecodeError:
            logger.error("❌ A LLM retornou algo que não é JSON válido.")
            return {"usar_tool": None, "resposta": dados}

        return dados_json

    except Exception as e:
        logger.error(f"❌ Falha ao consultar o Ollama: {e}")
        return {"usar_tool": None, "resposta": "Erro ao consultar o modelo local."}
