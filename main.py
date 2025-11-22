import time
import logging
from fastapi import FastAPI
from pydantic import BaseModel

from gaya_db_tool import TOOL_FUNCTIONS, TOOL_SCHEMA
from gaya_llm_router import processar_com_llm   # você ainda vai colar esse arquivo quando eu te enviar

# =====================================================
# CONFIGURAÇÃO DE LOG
# =====================================================

logger = logging.getLogger("GAYA_API")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - GAYA_API - %(levelname)s: %(message)s"))
logger.addHandler(handler)

# =====================================================
# FASTAPI
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

    logger.info(f"📥 Recebi mensagem de {msg.username}: {msg.text}")
    time.sleep(1)   # pequena pausa para não engasgar a máquina

    # -------------------------------------------------------------------------
    # 1) PEDIDO PARA A LLM INTERPRETAR A PERGUNTA
    # -------------------------------------------------------------------------
    logger.info("🧠 Enviando para a LLM interpretar pergunta...")
    time.sleep(1)

    llm_result = processar_com_llm(
        pergunta=msg.text,
        ferramentas=[TOOL_SCHEMA]     # LLM sabe que existe a ferramenta consultar_status_geral_db
    )

    logger.debug(f"🔍 LLM retornou: {llm_result}")
    time.sleep(1)

    # -------------------------------------------------------------------------
    # 2) VERIFICAR SE A LLM PEDIU ALGUMA FERRAMENTA
    # -------------------------------------------------------------------------

    if llm_result.get("usar_tool"):
        nome_tool = llm_result["usar_tool"]
        logger.warning(f"⚙️ LLM solicitou ferramenta: {nome_tool}")
        time.sleep(1)

        if nome_tool in TOOL_FUNCTIONS:

            logger.info(f"🚀 Executando ferramenta '{nome_tool}'...")
            time.sleep(1)

            resultado_tool = TOOL_FUNCTIONS[nome_tool]()

            logger.info(f"📊 Retorno da ferramenta: {resultado_tool}")
            time.sleep(1)

            # -----------------------------------------------------------------
            # 3) GERAR RESPOSTA FINAL DA LLM APÓS EXECUÇÃO DA TOOL
            # -----------------------------------------------------------------
            logger.info("🧠 Montando resposta final com o resultado da ferramenta...")
            time.sleep(1)

            resposta_final = processar_com_llm(
                pergunta=f"Monte uma resposta natural usando estes dados: {resultado_tool}",
                ferramentas=[]   # agora sem ferramentas
            )

            logger.info(f"💬 Resposta final pronta: {resposta_final.get('resposta')}")
            return {"response": resposta_final.get("resposta")}

        else:
            logger.error(f"❌ A LLM pediu uma ferramenta inexistente: {nome_tool}")
            return {"response": "Erro interno: ferramenta desconhecida."}

    # -------------------------------------------------------------------------
    # 4) SE NÃO PRECISAR DE TOOL, RESPONDE DIRETO
    # -------------------------------------------------------------------------
    logger.info("💬 A LLM respondeu sem precisar de ferramentas.")
    time.sleep(1)

    return {"response": llm_result.get("resposta")}
