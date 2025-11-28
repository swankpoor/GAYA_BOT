#!/usr/bin/env python3
import logging
import requests
import sqlite3
import os
import time
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# CONFIGURAÇÃO
TELEGRAM_TOKEN = "8257705817:AAGmQCwF4Bu9sO6zi4KVzX1qf9OjeE2WWPo"
DB_PATH = '/root/gaya-assistente/dados/gaya.db'
OLLAMA_URL = "http://localhost:11434/api/generate"
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Importar nossos módulos
from gaya_db import GayaDatabase
from excel_processor import ExcelProcessor

# Inicializar
db = GayaDatabase(DB_PATH)
excel_processor = ExcelProcessor()

# Controle de custos
custo_total = 0.0

def executar_consulta_sql(consulta):
    """Executa consulta SQL no banco e retorna resultados"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(consulta)
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        
        # Formatar resultados
        if colunas and resultados:
            formatted = []
            for linha in resultados:
                linha_dict = dict(zip(colunas, linha))
                formatted.append(linha_dict)
            return formatted
        return resultados
        
    except Exception as e:
        logging.error(f"Erro SQL: {e}")
        return None

def consultar_openrouter(pergunta, dados_banco=None, usar_sql=False):
    """Consulta OpenRouter com acesso ao banco de dados"""
    global custo_total
    
    try:
        # Preparar contexto
        if usar_sql and dados_banco:
            contexto = f"""
DADOS DO BANCO (resultado de consulta SQL):
{json.dumps(dados_banco, indent=2, ensure_ascii=False)}

PERGUNTA: {pergunta}

INSTRUÇÕES:
- Analise os dados do banco acima
- Responda em português de forma clara e útil
- Seja específico com números e estatísticas
- Dê insights práticos para logística
"""
        else:
            contexto = f"""
DADOS ESTATÍSTICOS DO BANCO:
{dados_banco}

PERGUNTA: {pergunta}

INSTRUÇÕES:
- Analise os dados estatísticos acima  
- Responda em português de forma clara e útil
- Seja específico com números e estatísticas
- Dê insights práticos para logística
"""

        payload = {
            "model": "google/gemini-flash-1.5-8b",  # Modelo econômico e rápido
            "messages": [
                {
                    "role": "system",
                    "content": "Você é a GAYA, especialista em logística e análise de dados de transporte. Sua função é analisar dados de banco de dados e fornecer insights úteis para operações logísticas."
                },
                {
                    "role": "user", 
                    "content": contexto
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.3
        }

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            
            # Calcular custo aproximado (estimativa)
            tokens_entrada = data.get('usage', {}).get('prompt_tokens', 0)
            tokens_saida = data.get('usage', {}).get('completion_tokens', 0)
            custo_consulta = (tokens_entrada * 0.00000015) + (tokens_saida * 0.0000006)  # Preço aproximado do modelo
            custo_total += custo_consulta
            
            logging.info(f"💰 Custo desta consulta: ${custo_consulta:.6f}")
            logging.info(f"💰 Custo total acumulado: ${custo_total:.6f}")
            
            return data['choices'][0]['message']['content']
        else:
            logging.error(f"Erro OpenRouter: {response.text}")
            return None
            
    except Exception as e:
        logging.error(f"Erro ao consultar OpenRouter: {e}")
        return None

def consultar_ollama(pergunta, contexto_dados):
    """Consulta Ollama local para perguntas simples"""
    try:
        prompt = f"""
Você é a GAYA, especialista em logística.

CONTEXTO:
{contexto_dados}

PERGUNTA: {pergunta}

RESPONDA em português de forma clara e útil:
"""
        
        response = requests.post(
            OLLAMA_URL,
            json={
                'model': 'llama3.2:1b',
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.3}
            },
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()['response']
        return None
        
    except Exception as e:
        logging.error(f"Erro Ollama: {e}")
        return None

def decidir_melhor_ia(pergunta, dados_banco):
    """Decide qual IA usar baseado na complexidade da pergunta"""
    pergunta_lower = pergunta.lower()
    
    # Perguntas simples - usar Ollama
    perguntas_simples = [
        'quantos', 'total', 'contar', 'estatística', 'resumo',
        'quantos transportes', 'quantos fretes', 'quantas cargas'
    ]
    
    if any(palavra in pergunta_lower for palavra in perguntas_simples):
        logging.info("🤖 Usando Ollama (pergunta simples)")
        return consultar_ollama(pergunta, dados_banco)
    else:
        # Perguntas complexas - usar OpenRouter
        logging.info("🚀 Usando OpenRouter (pergunta complexa)")
        return consultar_openrouter(pergunta, dados_banco)

def obter_dados_estatisticos():
    """Obtém estatísticas básicas do banco"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM transportes")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT destination_city, COUNT(*) FROM transportes WHERE destination_city != '' GROUP BY destination_city ORDER BY COUNT(*) DESC LIMIT 5")
        top_cidades = cursor.fetchall()
        
        cursor.execute("SELECT customer_name, COUNT(*) FROM transportes WHERE customer_name != '' GROUP BY customer_name ORDER BY COUNT(*) DESC LIMIT 5")
        top_clientes = cursor.fetchall()
        
        cursor.execute("SELECT vehicle_type, COUNT(*) FROM transportes WHERE vehicle_type != '' GROUP BY vehicle_type ORDER BY COUNT(*) DESC LIMIT 5")
        top_veiculos = cursor.fetchall()
        
        conn.close()
        
        return f"""
ESTATÍSTICAS:
• Total de transportes: {total}
• Principais cidades: {', '.join([f'{cidade}({qtd})' for cidade, qtd in top_cidades])}
• Principais clientes: {', '.join([f'{cliente}({qtd})' for cliente, qtd in top_clientes])}
• Tipos de veículos: {', '.join([f'{veiculo}({qtd})' for veiculo, qtd in top_veiculos])}
"""
    except Exception as e:
        logging.error(f"Erro ao obter estatísticas: {e}")
        return "Dados estatísticos não disponíveis."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global custo_total
    await update.message.reply_text(
        f"🤖 Olá! Eu sou a GAYA - Assistente Logística Avançada!\n\n"
        f"🧠 Agora com IA avançada (OpenRouter + Ollama)!\n"
        f"💾 Acesso direto ao banco de dados\n"
        f"💰 Custo atual: ${custo_total:.6f}\n\n"
        f"Pergunte sobre:\n"
        f"• Estatísticas de transportes\n"
        f"• Análise de rotas e clientes\n"
        f"• Insights logísticos\n"
        f"• E muito mais!"
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa arquivos Excel"""
    if not update.message.document:
        await update.message.reply_text("🤔 Não recebi um arquivo.")
        return
    
    file_name = update.message.document.file_name
    logging.info(f"📎 Arquivo recebido: {file_name}")
    
    if not file_name.lower().endswith(('.xlsx', '.xls')):
        await update.message.reply_text("❌ Envie um arquivo Excel (.xlsx ou .xls)")
        return
    
    await update.message.reply_text(f"📊 Processando {file_name}...")
    
    try:
        file = await update.message.document.get_file()
        file_path = f"/tmp/{file_name}"
        await file.download_to_drive(file_path)
        
        if excel_processor:
            transportes = excel_processor.processar_excel(file_path)
            
            if transportes and db:
                salvos = 0
                for transporte in transportes:
                    if db.salvar_transporte(transporte):
                        salvos += 1
                
                total_banco = db.contar_transportes()
                
                # Usar OpenRouter para análise avançada
                contexto = f"""
NOVOS DADOS PROCESSADOS:
• Arquivo: {file_name}
• Transportes encontrados: {len(transportes)}
• Salvos no banco: {salvos}
• Total no sistema: {total_banco}
"""
                pergunta = "Analise esses novos dados de transporte e forneça um relatório executivo em português com insights logísticos"
                resposta = consultar_openrouter(pergunta, contexto)
                
                if resposta:
                    mensagem = f"""
✅ ARQUIVO PROCESSADO!

{resposta}

📊 Estatísticas do processamento:
• {len(transportes)} transportes extraídos
• {salvos} registros salvos
• {total_banco} transportes totais
"""
                else:
                    mensagem = f"""
✅ ARQUIVO PROCESSADO!

📊 Resultados:
• {len(transportes)} transportes encontrados
• {salvos} salvos no banco  
• {total_banco} transportes totais

(Análise avançada temporariamente indisponível)
"""
                
                await update.message.reply_text(mensagem)
            else:
                await update.message.reply_text("❌ Não consegui extrair dados do arquivo.")
        
        os.remove(file_path)
        
    except Exception as e:
        logging.error(f"❌ Erro: {e}")
        await update.message.reply_text(f"❌ Erro: {str(e)[:100]}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens com IA avançada"""
    user_message = update.message.text
    logging.info(f"📨 Pergunta: {user_message}")
    
    await update.message.reply_text("🧠 Consultando banco de dados e analisando...")
    
    try:
        # Obter dados estatísticos
        dados_estatisticos = obter_dados_estatisticos()
        
        # Decidir qual IA usar e obter resposta
        resposta = decidir_melhor_ia(user_message, dados_estatisticos)
        
        if resposta:
            # Adicionar informação de custo se foi OpenRouter
            if "OpenRouter" in logging.__dict__.get('_cache', {}):
                global custo_total
                resposta += f"\n\n💡 Custo total acumulado: ${custo_total:.6f}"
            
            await update.message.reply_text(f"🤖 GAYA: {resposta}")
        else:
            await update.message.reply_text("❌ Não consegui processar sua pergunta. Tente reformular.")
        
    except Exception as e:
        logging.error(f"Erro na análise: {e}")
        await update.message.reply_text("❌ Erro ao analisar. Tente novamente.")

def main():
    logging.info("🚀 Iniciando Bot GAYA Avançado (OpenRouter + Ollama)...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    logging.info("✅ Bot Avançado iniciado! Aguardando mensagens...")
    application.run_polling()

if __name__ == '__main__':
    main()
