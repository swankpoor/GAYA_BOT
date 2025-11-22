import requests
import json
import logging
import os
import time
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Importa a nova ferramenta de consulta
from gaya_db_query_tool import TOOL_SCHEMA, TOOL_FUNCTIONS

# -------------------------------------------------------------------
# LOGGING CONFIG
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s: %(message)s"
)
logger = logging.getLogger("GAYA_API")

# -------------------------------------------------------------------
# OLLAMA CONFIG
# -------------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

# -------------------------------------------------------------------
# FASTAPI CONFIG
# -------------------------------------------------------------------
app = FastAPI(title="GAYA - API do LLM com Function Calling")

# -------------------------------------------------------------------
# MODEL
# -------------------------------------------------------------------
class Message(BaseModel):
    user_id: int
    username: Optional[str] = "Usuário Desconhecido"
    text: str


# ===================================================================
#  FUNÇÕES PRINCIPAIS
# ===================================================================

def _call_ollama_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Chama a API do Ollama com segurança e logs completos."""

    logger.info("⏳ Aguardando 1 segundo antes de enviar requisição ao LLM...")
    time.sleep(1)

    logger.info("📤 Enviando requisição ao Ollama...")
    logger.debug(f"Payload enviado ao LLM: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, stream=False)
        response.raise_for_status()
        result = response.json()
        logger.info("📥 Resposta recebida do LLM com sucesso.")
        return result

    except Exception as e:
        logger.error(f"❌ ERRO ao comunicar com Ollama: {e}")
        return {"error": str(e)}



def _get_llm_response(prompt: str, tools_schema: List[Dict[str, Any]]) -> Dict[str, Any]:
    """1ª chamada ao LLM para decidir se deve usar Tool."""

    logger.info("⏳ Aguardando 1 segundo antes da preparação da 1ª chamada ao LLM...")
    time.sleep(1)

    logger.info("🧠 Preparando 1ª chamada ao LLM (decisão de tool)...")

    tool_keywords = ["quantos", "cargas", "fretes", "total", "status"]
    needs_tool = any(k in prompt.lower() for k in tool_keywords)

    system_message = {
        "role": "system",
        "content": (
            "Você é a GAYA, IA logística debochada e eficiente. "
            "Analise o prompt e decida se precisa chamar a ferramenta. "
        )
    }

    user_message = {"role": "user", "content": prompt}

    messages = [system_message]

    if needs_tool:
        logger.warning("⚠️ FORÇANDO tool_call desde a 1ª chamada!")
        messages.append(user_message)
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "function": {"name": "consultar_status_geral_db", "arguments": {}}
            }]
        })
        tools_for_payload = None
    else:
        messages.append(user_message)
        tools_for_payload = tools_schema

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "options": {"temperature": 0.7},
        "tools": tools_for_payload,
        "stream": False
    }

    return _call_ollama_api(payload)



def _process_function_call(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Interpreta o resultado do LLM e executa a tool se solicitada."""

    logger.info("⏳ Pausa de 1 segundo antes de interpretar resposta da LLM...")
    time.sleep(1)

    logger.info("🔍 Interpretando retorno do LLM para detectar tool_call...")

    # Caso normal do LLM pedindo a função
    if "actions" in response and response["actions"]:
        tool_call = response["actions"][0]
        tool_name = tool_call["function"]["name"]
        args = tool_call["function"].get("arguments", {})

        logger.info(f"🤖 LLM solicitou a Tool: {tool_name}")

        if tool_name in TOOL_FUNCTIONS:
            try:
                logger.info("⏳ Pausa de 1 segundo antes de executar a Tool...")
                time.sleep(1)

                result = TOOL_FUNCTIONS[tool_name](**args)

                logger.info("✅ Tool executada com sucesso.")
                return {"tool_name": tool_name, "result": result}
            except Exception as e:
                logger.error(f"❌ Erro executando Tool: {e}")
                return {"tool_name": tool_name, "result": {"error": str(e)}}

    return None



def _get_final_response_after_tool(prompt, tool_name, tool_output, tools_schema):
    """2ª chamada ao LLM: gerar resposta final humana + debochada."""

    logger.info("⏳ Pausa de 1 segundo antes da 2ª chamada ao LLM...")
    time.sleep(1)

    logger.info("📤 Preparando 2ª chamada ao LLM para gerar resposta final...")

    messages = [
        {
            "role": "system",
            "content": (
                "Você é a GAYA, IA logística debochada. "
                "Use o resultado da ferramenta para montar uma resposta final clara, humana e útil. "
                "NÃO exponha JSON."
            )
        },
        {"role": "user", "content": prompt},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"function": {"name": tool_name, "arguments": {}}}]
        },
        {
            "role": "tool",
            "content": json.dumps(tool_output)
        }
    ]

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "options": {"temperature": 0.7},
        "stream": False
    }

    return _call_ollama_api(payload)



# ===================================================================
# ROTA PRINCIPAL
# ===================================================================

@app.post("/mensagem")
async def handle_message(message: Message, request: Request):

    logger.info("⏳ Pausa de 1 segundo antes de iniciar processamento da mensagem...")
    time.sleep(1)

    logger.info(f"GAYA_API: Mensagem recebida → {message.username}: {message.text}")

    user_prompt = message.text
    tools_list = [TOOL_SCHEMA]

    tool_keywords = ["quantos", "cargas", "fretes", "total", "status"]
    needs_forced_tool = any(k in user_prompt.lower() for k in tool_keywords)

    # ---------------------------
    # 1ª CHAMADA AO LLM
    # ---------------------------
    llm_response = _get_llm_response(user_prompt, tools_list)

    if "error" in llm_response:
        return {"response": f"❌ ERRO LLM: {llm_response['error']}"}

    # ---------------------------
    # PROCESSA TOOL_CALL
    # ---------------------------
    tool_data = _process_function_call(llm_response)

    # fallback do FORCE
    if needs_forced_tool and not tool_data:
        logger.warning("⚠️ FORÇANDO execução direta da Tool no fallback!")
        tool_name = "consultar_status_geral_db"
        tool_data = {
            "tool_name": tool_name,
            "result": TOOL_FUNCTIONS[tool_name]()
        }

    # ---------------------------
    # 2ª CHAMADA AO LLM
    # ---------------------------
    if tool_data:
        final_response = _get_final_response_after_tool(
            user_prompt,
            tool_data["tool_name"],
            tool_data["result"],
            tools_list
        )

        if "error" in final_response:
            return {"response": f"❌ ERRO na resposta final: {final_response['error']}"}

        return {"response": final_response.get("response", "⚠️ LLM não retornou texto.")}

    # ---------------------------
    # RESPOSTA DIRETA (sem tool)
    # ---------------------------
    return {"response": llm_response.get("response", "⚠️ Resposta vazia.")}
