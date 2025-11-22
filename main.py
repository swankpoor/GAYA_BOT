import time
import logging
from fastapi import FastAPI
from pydantic import BaseModel

from gaya_db_tool import TOOL_FUNCTIONS, TOOL_SCHEMA
from gaya_llm_router import processar_com_llm


# =====================================================
# CONFIGURAÇÃO DE LOG
# =====================================================

logger = logging.getLogger("GAYA_API")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - GAYA_API - %(levelname)s: %(message)s"))
logger.addHandler(handler)


# =====================================================
# FASTAPI APP
# =====================================================

app = FastAPI(title="Gaya AI API")


class Mensagem(BaseModel):
    text: str
    username: str
    user_id: int


# =====================================================
# ENDPOINT PRINCIPAL /mensagem
# =====================================================

@app.post("/mensagem")
async def receber_mensagem(msg: Mensagem):
    logger.info(f"📥 Mensagem recebida de {msg.username}: {msg.text}")
    time.sleep(1)

    # -------------------------------------------------------------------------
    # 1) CHAMADA AO MODELO PARA INTERPRETAÇÃO
    # -------------------------------------------------------------------------

    logger.info("🧠 Enviando para LLM interpretar...")
    time.sleep(1)

    llm_result = processar_com_llm(
        pergunta=msg.text,
        ferramentas=[TOOL_SCHEMA]   # lista de tools disponíveis
    )

    logger.debug(f"🔍 Resposta inicial da LLM: {llm_result}")
    time.sleep(1)

    # -------------------------------------------------------------------------
    # 2) SE A LLM SOLICITAR UMA TOOL
    # -------------------------------------------------------------------------

    tool_solicitada = llm_result.get("usar_tool")

    if tool_solicitada:
        logger.warning(f"⚙️ A LLM pediu a tool: {tool_solicitada}")
        time.sleep(1)

        # Tool existe?
        if tool_solicitada in TOOL_FUNCTIONS:

            logger.info(f"🚀 Executando ferramenta '{tool_solicitada}'...")
            time.sleep(1)

            resultado_tool = TOOL_FUNCTIONS[tool_solicitada]()
            logger.info(f"📊 Retorno da ferramenta: {resultado_tool}")
            time.sleep(1)

            # ---------------------------------------------------------------
            # 3) GERA A RESPOSTA FINAL BASEADA NOS DADOS DO BANCO
            # ---------------------------------------------------------------

            logger.info("🧠 Pedindo para a LLM montar a resposta final...")
            time.sleep(1)

            resposta_final = processar_com_llm(
                pergunta=f"Use estes dados e gere uma resposta natural, clara e útil: {resultado_tool}",
                ferramentas=[]   # agora não pode chamar ferramentas
            )

            resposta_texto = resposta_final.get("resposta")
            logger.info(f"💬 Resposta final enviada: {resposta_texto}")

            return {"response": resposta_texto}

        else:
            logger.error(f"❌ Tool inexistente solicitada: {tool_solicitada}")
            return {"response": "Erro: a IA pediu uma ferramenta inexistente."}

    # -------------------------------------------------------------------------
    # 3) SE NÃO PEDIU TOOL → RESPOSTA DIRETA
    # -------------------------------------------------------------------------

    logger.info("💬 A LLM respondeu diretamente.")
    time.sleep(1)

    return {"response": llm_result.get("resposta")}
