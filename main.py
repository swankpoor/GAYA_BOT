import requests
import json
import logging
import os
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Importa a nova ferramenta de consulta
from gaya_db_query_tool import TOOL_SCHEMA, TOOL_FUNCTIONS

# --- Configuração de Logging ---
# Configuração base para mostrar logs no terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s: %(message)s')
logger = logging.getLogger('GAYA_API')

# --- Configuração do LLM (Ollama) ---
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:1b') # Seu modelo mais leve

# --- Configuração do FastAPI ---
app = FastAPI(title="GAYA - API do LLM com Function Calling")

# --- Modelo de Dados ---
class Message(BaseModel):
    user_id: int
    username: Optional[str] = "Usuário Desconhecido"
    text: str

# --- Funções de Comunicação com Ollama ---

def _call_ollama_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Função auxiliar para chamar a API do Ollama."""
    url = f"{OLLAMA_HOST}/api/generate"
    try:
        response = requests.post(url, json=payload, stream=False)
        response.raise_for_status() # Lança exceção para status ruins (4xx, 5xx)
        
        # O Ollama, por padrão, retorna JSONs em cada linha, mas 
        # para a API /generate com stream=False ele retorna o objeto completo.
        # Precisamos parsear a resposta completa
        full_response = response.json()
        
        # O campo 'response' contém o texto final ou o JSON da chamada de função
        return full_response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de comunicação com Ollama: {e}")
        # Retorna um formato de erro que o loop principal possa gerenciar
        return {"error": f"Erro de comunicação com LLM: {e}"}

def _get_llm_response(prompt: str, tools_schema: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Envia o prompt e o schema das ferramentas ao Ollama.
    
    CORREÇÃO: Este método agora detecta palavras-chave e, se houver, 
    usa um histórico de conversação pré-preenchido para *forçar* o modelo a 
    reconhecer a intenção de usar a ferramenta na primeira chamada.
    
    Isso é necessário porque modelos menores (1b) podem ignorar o `systemInstruction`.
    """
    
    # 1. Palavras-chave para forçar o uso da ferramenta
    tool_keywords = ["quantos", "cargas", "fretes", "total", "status"]
    
    # 2. Verifica se o prompt contém alguma palavra-chave (case-insensitive)
    needs_tool = any(kw in prompt.lower() for kw in tool_keywords)
    
    # --- Criação do Histórico (messages) ---
    
    # Sistema: Instrução de personalidade e objetivo
    system_message = {
        "role": "system",
        "content": (
            "Você é a GAYA, uma IA de logística com personalidade debochada e firme, "
            "mas extremamente eficiente. Sua missão é auxiliar o usuário com informações "
            "de fretes e cargas. "
            "Sua tarefa é analisar o prompt do usuário e decidir se a ferramenta deve ser usada."
        )
    }
    
    # Usuário: O prompt original
    user_message = {
        "role": "user",
        "content": prompt
    }

    messages = [system_message]
    
    if needs_tool:
        logger.warning("FORÇANDO: LLM será forçado a solicitar a tool 'consultar_status_geral_db'...")
        
        # Para forçar o LLM a chamar a função, criamos um histórico artificial
        # onde o "assistant" *já* solicitou a chamada da função.
        # Na verdade, a API do Ollama irá interpretar isso como um pedido de 
        # Função Chamada para dar prosseguimento.
        
        # Adiciona a mensagem do usuário
        messages.append(user_message)
        
        # Simula que o assistente já decidiu e chamou a função
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "function": {
                        "name": "consultar_status_geral_db",
                        "arguments": {}
                    }
                }
            ]
        })
        
        # O payload para o LLM na verdade será apenas o histórico, sem o 'tools'
        # Isso faz o LLM entrar no modo "executar a tool e dar a resposta final"
        tools_list_for_payload = None 
        
    else:
        # Se não precisar de tool, faz a chamada normal para obter a resposta direta
        messages.append(user_message)
        tools_list_for_payload = tools_schema

    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "options": {
            "temperature": 0.7 
        },
        "tools": tools_list_for_payload, # Inclui o schema se não estiver forçando
        "stream": False 
    }
    
    return _call_ollama_api(payload)

def _process_function_call(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Processa a resposta do Ollama para executar uma função, se solicitada."""
    
    # Verifica se o Ollama solicitou uma chamada de função
    # OBS: Quando *forçamos* a chamada no _get_llm_response, a função
    # que é executada é a do *nosso* código, e o resultado é passado
    # para a segunda chamada do LLM. O Ollama não retorna a tool_call neste caso forçado,
    # ele espera o resultado da tool.
    
    # Vamos adaptar a lógica aqui para o cenário forçado,
    # que é o último item da lista de mensagens.
    
    # Se a resposta do LLM na primeira chamada vier vazia ou sem action, 
    # e nós detectamos a necessidade de tool, precisamos simular o action aqui.
    
    if 'actions' in response and response['actions']:
        tool_call = response['actions'][0]
        tool_name = tool_call.get('function', {}).get('name')
        tool_args = tool_call.get('function', {}).get('arguments', {})
        
        logger.info(f"🤖 LLM solicitou chamada de função: {tool_name} com args: {tool_args}")

        if tool_name in TOOL_FUNCTIONS:
            # Encontra a função Python correspondente
            func = TOOL_FUNCTIONS[tool_name]
            
            try:
                # Executa a função Python (Tool)
                result = func(**tool_args)
                logger.info("✅ Ferramenta executada com sucesso.")
                return {
                    "tool_name": tool_name,
                    "result": result
                }
            except Exception as e:
                logger.error(f"❌ Erro ao executar função {tool_name}: {e}")
                return {
                    "tool_name": tool_name,
                    "result": {"error": f"Erro interno ao executar a ferramenta: {str(e)}"}
                }
        else:
            logger.error(f"❌ Função solicitada '{tool_name}' não mapeada.")
            # Continuar com resposta direta se o LLM alucinar uma tool
            return None 

    # Se não houve 'actions' na resposta do Ollama, mas o LLM deu uma resposta direta
    # (caso não tenha detectado a necessidade de tool), retornamos None para
    # que o fluxo caia na "Resposta Direta"
    return None

def _get_final_response_after_tool(
    prompt: str, 
    tool_name: str, 
    tool_output: Dict[str, Any],
    tools_schema: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Envia o resultado da função de volta ao LLM para gerar a resposta final."""

    # Prepara o histórico da conversa com o resultado da tool
    messages = [
        {
            "role": "system",
            "content": (
                "Você é a GAYA, uma IA de logística com personalidade debochada e firme, "
                "mas extremamente eficiente. Sua missão é auxiliar o usuário com informações "
                "de fretes e cargas. "
                "Use o resultado da ferramenta para gerar uma resposta final, relevante, "
                "debochada e útil para o usuário. NÃO inclua o JSON de saída da ferramenta "
                "na resposta final."
            )
        },
        {
            "role": "user",
            "content": prompt
        },
        {
            "role": "assistant",
            "content": None, 
            "tool_calls": [
                {
                    "function": {
                        "name": tool_name,
                        "arguments": {} 
                    }
                }
            ]
        },
        {
            "role": "tool",
            "content": json.dumps(tool_output) # O resultado da tool
        }
    ]

    # Novo payload com o histórico completo
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "options": {
            "temperature": 0.7 
        },
        "stream": False # Síncrono para resposta final
    }
    
    return _call_ollama_api(payload)


# --- Rota Principal ---

@app.post("/mensagem")
async def handle_message(message: Message, request: Request):
    """
    Rota principal que recebe a mensagem do Telegram e gerencia o ciclo
    de raciocínio do LLM com o Function Calling.
    """
    
    # 1. Loga a mensagem recebida
    username_log = message.username or f"Usuário ID: {message.user_id}"
    logger.info(f"GAYA_API: Recebi mensagem de {username_log} (Telegram): {message.text}")
    
    user_prompt = message.text
    tools_list = [TOOL_SCHEMA]
    
    # --- VERIFICAÇÃO DE CHAVE PARA O CÓDIGO FORÇADO ---
    tool_keywords = ["quantos", "cargas", "fretes", "total", "status"]
    needs_tool_forced = any(kw in user_prompt.lower() for kw in tool_keywords)
    # --------------------------------------------------

    # 2. Primeira chamada ao LLM: Decisão de Tool
    llm_response = _get_llm_response(user_prompt, tools_list)

    if 'error' in llm_response:
        return {"response": f"❌ ERRO LLM: {llm_response['error']}"}

    
    # 3. Processamento do Function Call (Se o LLM solicitou ou se foi forçado)
    
    tool_data = _process_function_call(llm_response)

    # Lógica de fallback para a execução forçada
    if needs_tool_forced and not tool_data:
        # Se detectamos a necessidade de tool, mas o LLM não explicitou a chamada (vazio ou resposta direta)
        # O _get_llm_response já preparou o histórico para forçar a chamada,
        # mas precisamos simular o resultado do _process_function_call
        
        tool_name = "consultar_status_geral_db"
        logger.info(f"⚙️ EXECUTANDO FORÇADO: Chamando a função {tool_name} diretamente...")

        if tool_name in TOOL_FUNCTIONS:
            func = TOOL_FUNCTIONS[tool_name]
            try:
                tool_output_forced = func()
                logger.info("✅ Ferramenta executada (Forçada) com sucesso.")
                tool_data = {
                    "tool_name": tool_name,
                    "result": tool_output_forced
                }
            except Exception as e:
                logger.error(f"❌ Erro ao executar função (Forçada) {tool_name}: {e}")
                tool_data = {
                    "tool_name": tool_name,
                    "result": {"error": f"Erro interno ao executar a ferramenta (Forçada): {str(e)}"}
                }


    if tool_data:
        # Se uma função foi chamada (seja pelo LLM, seja por detecção forçada)
        tool_name = tool_data['tool_name']
        tool_output = tool_data['result']

        # 4. Segunda Chamada ao LLM: Geração da Resposta Final
        final_response = _get_final_response_after_tool(
            user_prompt, 
            tool_name, 
            tool_output,
            tools_list
        )
        
        if 'error' in final_response:
            return {"response": f"❌ ERRO LLM na resposta final: {final_response['error']}"}
        
        final_text = final_response.get('response', 'GAYA está sem palavras (Resposta final vazia do LLM).')
        
        logger.info(f"✅ Geração final após Tool. Resposta: {final_text[:50]}...")
        return {"response": final_text}

    else:
        # 5. Resposta Direta (Se o LLM NÃO solicitou Tool E NÃO foi forçado)
        final_text = llm_response.get('response', 'GAYA está sem palavras (Resposta direta vazia do LLM).')
        logger.info(f"➡️ Resposta direta do LLM. Resposta: {final_text[:50]}...")
        return {"response": final_text}
