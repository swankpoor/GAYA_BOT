import sqlite3
import requests
import logging
import json
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from typing import Dict, List, Any

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configurações
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL = "openrouter/auto"  # AUTO ROUTER - escolhe o melhor modelo
DATABASE_PATH = 'transportes.db'

# Inicialização do banco de dados
def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Tabela principal de transportes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transportes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chassis TEXT UNIQUE,
            cargo_id TEXT,
            origem TEXT,
            destino TEXT,
            status TEXT,
            data_criacao DATE,
            valor_frete DECIMAL(10,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela para aprendizado - armazena "conhecimento" do bot
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent TEXT,  # Intenção aprendida
            pattern TEXT,  # Padrão de pergunta
            sql_query TEXT,  # Consulta SQL associada
            description TEXT,  # Descrição do que faz
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de schema para o bot entender a estrutura
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS database_schema (
            table_name TEXT,
            column_name TEXT,
            data_type TEXT,
            description TEXT
        )
    ''')
    
    # Inserir dados de exemplo se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM transportes")
    if cursor.fetchone()[0] == 0:
        from datetime import datetime, timedelta
        import random
        
        sample_data = [
            ('CHS001', 'CARGO001', 'São Paulo', 'Rio de Janeiro', 'ativo', 
             '2024-01-15', 1500.00),
            ('CHS002', 'CARGO002', 'Curitiba', 'Porto Alegre', 'ativo', 
             '2024-01-16', 1800.50),
            ('CHS003', 'CARGO003', 'Belo Horizonte', 'Brasília', 'inativo', 
             '2024-01-10', 2200.75),
            ('CHS004', 'CARGO004', 'São Paulo', 'Salvador', 'ativo', 
             '2024-01-18', 3200.00),
            ('CHS005', 'CARGO005', 'Rio de Janeiro', 'Fortaleza', 'ativo', 
             '2024-01-17', 2800.25),
        ]
        
        cursor.executemany('''
            INSERT INTO transportes (chassis, cargo_id, origem, destino, status, data_criacao, valor_frete)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sample_data)
    
    # Inserir schema information
    cursor.execute("SELECT COUNT(*) FROM database_schema")
    if cursor.fetchone()[0] == 0:
        schema_info = [
            ('transportes', 'id', 'INTEGER', 'ID único do transporte'),
            ('transportes', 'chassis', 'TEXT', 'Número do chassis do veículo'),
            ('transportes', 'cargo_id', 'TEXT', 'ID da carga transportada'),
            ('transportes', 'origem', 'TEXT', 'Cidade de origem do transporte'),
            ('transportes', 'destino', 'TEXT', 'Cidade de destino do transporte'),
            ('transportes', 'status', 'TEXT', 'Status: ativo/inativo/cancelado'),
            ('transportes', 'data_criacao', 'DATE', 'Data de criação do registro'),
            ('transportes', 'valor_frete', 'DECIMAL', 'Valor do frete em reais'),
        ]
        
        cursor.executemany('''
            INSERT INTO database_schema (table_name, column_name, data_type, description)
            VALUES (?, ?, ?, ?)
        ''', schema_info)
    
    conn.commit()
    conn.close()
    logging.info("✅ Banco de dados e tabelas de conhecimento inicializados!")

# Obter schema completo do banco
def get_database_schema():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Obter todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    schema = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        schema[table_name] = [
            {
                'name': col[1],
                'type': col[2],
                'nullable': not col[3],
                'pk': col[5]
            }
            for col in columns
        ]
    
    conn.close()
    return schema

# Executar consulta SQL segura
def execute_safe_query(query: str, params: tuple = ()) -> Dict[str, Any]:
    """
    Executa consulta SQL de forma segura, apenas permitindo SELECT
    e validando a consulta
    """
    try:
        # Validar que é uma consulta SELECT (por segurança)
        if not query.strip().upper().startswith('SELECT'):
            return {
                'success': False,
                'error': 'Apenas consultas SELECT são permitidas',
                'data': None
            }
        
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Para retornar dicionários
        cursor = conn.cursor()
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Converter para lista de dicionários
        data = [dict(row) for row in results]
        
        conn.close()
        
        return {
            'success': True,
            'data': data,
            'row_count': len(data)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': None
        }

# Consulta inteligente ao OpenRouter com Auto Router
def ask_gaya_intelligent(pergunta: str, contexto_db: Dict = None) -> Dict[str, Any]:
    """
    Consulta o OpenRouter com Auto Router para interpretar a pergunta
    e gerar SQL ou resposta inteligente
    """
    try:
        # Obter schema do banco
        schema = get_database_schema()
        
        # Preparar contexto completo
        contexto_completo = {
            "schema_banco": schema,
            "pergunta_usuario": pergunta,
            "contexto_adicional": contexto_db or {},
            "instrucoes": """
            Você é o GAYA - Assistente Inteligente de Banco de Dados de Transportes.
            
            SUAS CAPACIDADES:
            1. ANALISAR a pergunta do usuário e o schema do banco
            2. GERAR consultas SQL válidas para responder à pergunta
            3. INTERPRETAR resultados e explicar em português claro
            4. SUGERIR análises relacionadas
            5. IDENTIFICAR quando não é possível responder
            
            FORMATO DE RESPOSTA (JSON):
            {
                "sql_query": "SELECT... ou null",
                "explanation": "Explicação da resposta",
                "suggestions": ["sugestão1", "sugestão2"],
                "can_answer": true/false,
                "needs_clarification": "o que precisa ser esclarecido"
            }
            
            REGRAS:
            - Use apenas SELECT, não modifique dados
            - Sempre explique o que fez
            - Se não tiver certeza, peça esclarecimento
            - Sugira análises relacionadas úteis
            """
        }
        
        prompt = f"""
        CONTEXTO DO BANCO DE DADOS:
        {json.dumps(contexto_completo, indent=2, ensure_ascii=False)}
        
        PERGUNTA DO USUÁRIO: {pergunta}
        
        Analise a pergunta, gere SQL se apropriado, e responda no formato JSON especificado.
        """
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENROUTER_MODEL,  # AUTO ROUTER
                "messages": [
                    {
                        "role": "system",
                        "content": "Você é o GAYA - Assistente Inteligente de Banco de Dados. Sempre responda em JSON conforme o formato especificado."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            },
            timeout=45
        )
        response.raise_for_status()
        
        content = response.json()['choices'][0]['message']['content']
        
        # Tentar parsear JSON da resposta
        try:
            # Extrair JSON da resposta (pode vir com texto around)
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                resposta_json = json.loads(json_match.group())
            else:
                resposta_json = json.loads(content)
                
            return {
                'success': True,
                'response': resposta_json,
                'raw_content': content
            }
            
        except json.JSONDecodeError:
            # Se não conseguir parsear JSON, criar resposta padrão
            return {
                'success': True,
                'response': {
                    'sql_query': None,
                    'explanation': content,
                    'suggestions': [],
                    'can_answer': True,
                    'needs_clarification': None
                },
                'raw_content': content
            }
            
    except Exception as e:
        logging.error(f"Erro OpenRouter: {e}")
        return {
            'success': False,
            'error': str(e),
            'response': None
        }

# Salvar conhecimento aprendido
def save_learned_knowledge(intent: str, pattern: str, sql_query: str, description: str):
    """Salva um novo padrão aprendido pelo bot"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bot_knowledge (intent, pattern, sql_query, description)
            VALUES (?, ?, ?, ?)
        ''', (intent, pattern, sql_query, description))
        
        conn.commit()
        conn.close()
        logging.info(f"💾 Novo conhecimento salvo: {intent}")
        
    except Exception as e:
        logging.error(f"Erro ao salvar conhecimento: {e}")

# Handler principal de mensagens
async def handle_intelligent_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.message.from_user.id
    
    logging.info(f"🧠 Pergunta inteligente: {user_message}")
    
    # Feedback imediato
    processing_message = await update.message.reply_text("🔍 GAYA está analisando sua pergunta...")
    
    # Consultar GAYA inteligente
    gaya_response = ask_gaya_intelligent(user_message)
    
    if not gaya_response['success']:
        await context.bot.edit_message_text(
            chat_id=processing_message.chat_id,
            message_id=processing_message.message_id,
            text="❌ Erro ao processar sua pergunta. Tente novamente."
        )
        return
    
    resposta = gaya_response['response']
    
    # Processar baseado na resposta do GAYA
    if resposta.get('can_answer', False) and resposta.get('sql_query'):
        # Executar a consulta SQL gerada
        sql_result = execute_safe_query(resposta['sql_query'])
        
        if sql_result['success']:
            # Formatar resultados
            if sql_result['row_count'] > 0:
                resultado_texto = format_query_results(sql_result['data'])
                
                mensagem_final = f"""
✅ **Resultado da Análise:**

{resposta['explanation']}

📊 **Dados Encontrados:**
{resultado_texto}

💡 **Sugestões:**
{format_suggestions(resposta.get('suggestions', []))}
                """
            else:
                mensagem_final = f"""
📭 **Análise Concluída:**

{resposta['explanation']}

_Nenhum dado encontrado com os critérios especificados._

💡 **Sugestões:**
{format_suggestions(resposta.get('suggestions', []))}
                """
        else:
            mensagem_final = f"""
⚠️ **Análise com Limitações:**

{resposta['explanation']}

❌ _Erro na consulta: {sql_result['error']}_

💡 **Sugestões:**
{format_suggestions(resposta.get('suggestions', []))}
            """
    
    elif resposta.get('needs_clarification'):
        # Pedir esclarecimento
        mensagem_final = f"""
🤔 **Preciso de mais informações:**

{resposta['needs_clarification']}

{resposta.get('explanation', '')}

💡 **Sugestões:**
{format_suggestions(resposta.get('suggestions', []))}
        """
    
    else:
        # Resposta direta sem SQL
        mensagem_final = f"""
💭 **Análise do GAYA:**

{resposta.get('explanation', 'Não foi possível gerar uma resposta específica.')}

💡 **Sugestões:**
{format_suggestions(resposta.get('suggestions', []))}
        """
    
    # Enviar resposta final
    await context.bot.edit_message_text(
        chat_id=processing_message.chat_id,
        message_id=processing_message.message_id,
        text=mensagem_final
    )

# Funções auxiliares
def format_query_results(data: List[Dict]) -> str:
    """Formata os resultados da consulta para exibição"""
    if not data:
        return "Nenhum resultado encontrado."
    
    # Limitar a 10 registros para não sobrecarregar
    display_data = data[:10]
    
    resultado = ""
    for i, row in enumerate(display_data, 1):
        resultado += f"\n{i}. " + " | ".join([f"{k}: {v}" for k, v in row.items()])
    
    if len(data) > 10:
        resultado += f"\n\n... e mais {len(data) - 10} registros"
    
    return resultado

def format_suggestions(suggestions: List[str]) -> str:
    """Formata as sugestões do GAYA"""
    if not suggestions:
        return "• Tente fazer perguntas mais específicas sobre seus dados"
    
    return "\n".join([f"• {sug}" for sug in suggestions])

# Comando start melhorado
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🧠 **GAYA - Assistente Inteligente de Dados**

Eu sou um bot verdadeiramente inteligente que entende perguntas em linguagem natural sobre seu banco de dados de transportes.

🔧 **O que posso fazer:**
• Responder perguntas complexas sobre seus dados
• Gerar análises e relatórios automáticos
• Identificar padrões e insights
• Aprender com suas necessidades

💡 **Exemplos do que perguntar:**
_"Quantos transportes ativos temos?"_
_"Quais são os fretes mais caros?"_
_"Mostre transportes com chassis repetidos"_
_"Qual a origem com mais transportes?"_
_"Analise o valor médio dos fretes por status"_

🚀 **Faça qualquer pergunta sobre seus dados!**
    """
    await update.message.reply_text(welcome_text)

# Comando para ver schema
async def show_schema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o schema do banco para o usuário"""
    schema = get_database_schema()
    
    schema_text = "📋 **Estrutura do Banco de Dados:**\n\n"
    for table, columns in schema.items():
        schema_text += f"**Tabela: {table}**\n"
        for col in columns:
            schema_text += f"  • {col['name']} ({col['type']})\n"
        schema_text += "\n"
    
    await update.message.reply_text(schema_text)

# Main
def main():
    # Inicializar banco com conhecimento
    init_db()
    
    # Criar aplicação
    # No final do arquivo:
    application = Application.builder().token("8257705817:AAGmQCwF4Bu9sO6zi4KVzX1qf9OjeE2WWPo").build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("schema", show_schema))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_intelligent_message))
    
    # Iniciar
    logging.info("🧠 Iniciando GAYA - Assistente Inteligente...")
    application.run_polling()
    logging.info("✅ GAYA iniciado! Aguardando perguntas inteligentes...")

if __name__ == '__main__':
    main()
