#!/usr/bin/env python3
"""
GAYA_telegram.py - VERSÃO CORRIGIDA
"""
import os
import time
from gaya_db import GayaDatabase
from excel_processor import ExcelProcessor

# Inicializar após os imports
db = GayaDatabase(DB_PATH)
excel_processor = ExcelProcessor()
import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import sys
import os
import time  # ✅ ADICIONADO
import sqlite3  # ✅ ADICIONADO

# ... (resto dos imports e configurações existentes)

class GAYATelegramBot:
    def __init__(self):
        # ... (código existente do __init__)
        
    # ... (mantenha TODOS os métodos existentes: _comando_start, _comando_help, etc)

    async def _processar_arquivo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa arquivos Excel - VERSÃO SIMPLIFICADA E CORRIGIDA"""
        user = update.effective_user
        
        try:
            # Verificar se é documento
            if not update.message.document:
                await update.message.reply_text("🤔 Não recebi um arquivo.")
                return
            
            nome_arquivo = update.message.document.file_name
            logger.info(f"📎 Arquivo recebido: {nome_arquivo}")
            
            # Só aceita Excel por enquanto
            extensao = os.path.splitext(nome_arquivo)[1].lower()
            if extensao not in ['.xlsx', '.xls']:
                await update.message.reply_text(
                    "❌ *Só aceito Excel por enquanto* (.xlsx, .xls)\n"
                    "Envie um arquivo Excel como o exemplo que você mostrou!",
                    parse_mode='Markdown'
                )
                return
            
            # 1️⃣ AVISAR INÍCIO DO PROCESSAMENTO
            await update.message.reply_text(
                f"📊 *Processando {nome_arquivo}...*\n\n"
                "⌛ Isso pode levar alguns segundos...",
                parse_mode='Markdown'
            )
            
            # 2️⃣ BAIXAR ARQUIVO
            file = await update.message.document.get_file()
            file_path = f"/tmp/{nome_arquivo}"
            await file.download_to_drive(file_path)
            
            # PAUSA PARA PROCESSAMENTO
            time.sleep(2)
            
            # 3️⃣ PROCESSAR EXCEL - IMPORT DINÂMICO
            try:
                from excel_processor import ExcelProcessor
                processor = ExcelProcessor()
                transportes = processor.processar_excel(file_path)
            except ImportError as e:
                logger.error(f"❌ Erro ao importar processor: {e}")
                await update.message.reply_text(
                    "❌ *Módulo de processamento não encontrado!*\n"
                    "Verifique se o arquivo excel_processor.py está na mesma pasta.",
                    parse_mode='Markdown'
                )
                return
            
            if not transportes:
                await update.message.reply_text(
                    "❌ *Não consegui extrair dados* do arquivo.\n"
                    "Verifique se é igual ao exemplo que você mostrou!\n"
                    f"*Dica:* A planilha deve ter a aba 'TRK_TRANS_DTL'",
                    parse_mode='Markdown'
                )
                # Limpar arquivo mesmo com erro
                if os.path.exists(file_path):
                    os.remove(file_path)
                return
            
            # PAUSA PARA BANCO DE DADOS
            time.sleep(1)
            
            # 4️⃣ SALVAR NO BANCO - IMPORT DINÂMICO
            try:
                from gaya_db import db
                salvos = 0
                for transporte in transportes:
                    if db.salvar_transporte(transporte):
                        salvos += 1
                    
                    # PAUSA ENTRE CADA REGISTRO (importante para RAM baixa)
                    if salvos % 5 == 0:
                        time.sleep(0.3)
                
                # 5️⃣ CONTAR TOTAL NO BANCO
                total_banco = db.contar_transportes()
                
            except ImportError as e:
                logger.error(f"❌ Erro ao importar banco: {e}")
                await update.message.reply_text(
                    "❌ *Erro no banco de dados!*\n"
                    "Verifique se o arquivo gaya_db.py está na mesma pasta.",
                    parse_mode='Markdown'
                )
                return
            
            # 6️⃣ LIMPAR ARQUIVO TEMPORÁRIO
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # 7️⃣ RESPONDER COM RESUMO SIMPLES
            resumo = f"""
✅ *ARQUIVO PROCESSADO COM SUCESSO!*

📊 *Estatísticas:*
• {len(transportes)} transportes encontrados no arquivo
• {salvos} salvos no banco de dados
• {total_banco} transportes totais no sistema

🏭 *Clientes principais:*
{self._extrair_clientes(transportes)}

🚛 *Tipos de veículo:*
{self._extrair_veiculos(transportes)}

*Use /fretes para consultar os dados!*
            """.strip()
            
            await update.message.reply_text(resumo, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Erro geral no processamento: {e}")
            # Tentar limpar arquivo temporário em caso de erro
            try:
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
            
            await update.message.reply_text(
                "❌ *Erro no processamento!*\n\n"
                "Detalhes técnicos (para debug):\n"
                f"`{str(e)[:200]}...`",
                parse_mode='Markdown'
            )

    def _extrair_clientes(self, transportes):
        """Extrai clientes únicos para o resumo"""
        try:
            clientes = set()
            for t in transportes[:10]:  # Aumentei para 10
                if t.get('customer_name'):
                    clientes.add(t['customer_name'])
            clientes_lista = list(clientes)[:5]  # Mostra até 5
            if clientes_lista:
                return "\n".join([f"• {c}" for c in clientes_lista])
            else:
                return "• Nenhum cliente identificado"
        except Exception as e:
            logger.error(f"Erro ao extrair clientes: {e}")
            return "• Erro ao extrair clientes"

    def _extrair_veiculos(self, transportes):
        """Extrai veículos únicos para o resumo"""
        try:
            veiculos = set()
            for t in transportes[:10]:
                if t.get('vehicle_type'):
                    veiculos.add(t['vehicle_type'])
            veiculos_lista = list(veiculos)[:5]
            if veiculos_lista:
                return "\n".join([f"• {v}" for v in veiculos_lista])
            else:
                return "• Nenhum veículo identificado"
        except Exception as e:
            logger.error(f"Erro ao extrair veículos: {e}")
            return "• Erro ao extrair veículos"

    # ... (mantenha TODOS os outros métodos existentes: _handle_callback, etc)

def main():
    """Função principal"""
    try:
        bot = GAYATelegramBot()
        bot.run()
    except Exception as e:
        logger.error(f"❌ Erro fatal no bot Telegram: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
