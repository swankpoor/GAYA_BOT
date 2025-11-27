#!/usr/bin/env python3
import logging
import requests
import sqlite3
import os
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# CONFIGURAÇÃO
TELEGRAM_TOKEN = "8257705817:AAGmQCwF4Bu9sO6zi4KVzX1qf9OjeE2WWPo"
DB_PATH = '/root/gaya-assistente/dados/gaya.db'

# Importar nossos módulos
try:
    from gaya_db import GayaDatabase
    from excel_processor import ExcelProcessor
    db = GayaDatabase(DB_PATH)
    excel_processor = ExcelProcessor()
    logging.info("✅ Módulos carregados com sucesso!")
except ImportError as e:
    logging.error(f"❌ Erro ao carregar módulos: {e}")
    db = None
    excel_processor = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Olá! Eu sou a GAYA - Assistente Logística!\n\n"
        "📊 Agora eu posso processar planilhas Excel!\n\n"
        "Envie uma planilha Excel e eu extraio os dados automaticamente."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa arquivos Excel"""
    if not update.message.document:
        await update.message.reply_text("🤔 Não recebi um arquivo.")
        return
    
    file_name = update.message.document.file_name
    logging.info(f"📎 Arquivo recebido: {file_name}")
    
    # Verificar se é Excel
    if not file_name.lower().endswith(('.xlsx', '.xls')):
        await update.message.reply_text("❌ Por favor, envie um arquivo Excel (.xlsx ou .xls)")
        return
    
    await update.message.reply_text(f"📊 Processando {file_name}...")
    
    try:
        # Baixar arquivo
        file = await update.message.document.get_file()
        file_path = f"/tmp/{file_name}"
        await file.download_to_drive(file_path)
        
        # Processar Excel
        if excel_processor:
            transportes = excel_processor.processar_excel(file_path)
            
            if transportes and db:
                salvos = 0
                for transporte in transportes:
                    if db.salvar_transporte(transporte):
                        salvos += 1
                
                total_banco = db.contar_transportes()
                
                resumo = f"""
✅ ARQUIVO PROCESSADO!

📊 Resultados:
• {len(transportes)} transportes encontrados
• {salvos} salvos no banco
• {total_banco} transportes totais

Ótimo trabalho! 🚛
                """.strip()
                
                await update.message.reply_text(resumo)
            else:
                await update.message.reply_text("❌ Não consegui extrair dados do arquivo.")
        
        # Limpar arquivo
        os.remove(file_path)
        
    except Exception as e:
        logging.error(f"❌ Erro: {e}")
        await update.message.reply_text(f"❌ Erro no processamento: {str(e)[:100]}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens de texto"""
    user_message = update.message.text.lower()
    
    if any(word in user_message for word in ['fretes', 'cargas', 'transporte']):
        if db:
            total = db.contar_transportes()
            await update.message.reply_text(f"📦 Tenho {total} transportes no banco de dados!")
        else:
            await update.message.reply_text("📦 Banco de dados não disponível.")
    else:
        await update.message.reply_text("🤖 Envie uma planilha Excel ou digite /start")

def main():
    logging.info("🤖 Iniciando Bot Telegram GAYA...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    logging.info("✅ Bot iniciado! Aguardando mensagens...")
    application.run_polling()

if __name__ == '__main__':
    main()
