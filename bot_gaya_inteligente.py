import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Importar módulos
from planilha_processor import processar_planilha_excel
# from database_manager import init_db, contar_transportes, etc... (vamos criar depois)
# from intelligent_responses import handle_intelligent_message (vamos criar depois)

# Carregar variáveis do arquivo .env
load_dotenv()

# Configuração
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_PATH = 'transportes.db'

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 🆕 HANDLER DE DOCUMENTOS (AGORA SIMPLES)
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa arquivos Excel enviados pelo usuário - VERSÃO MODULAR"""
    document = update.message.document
    user = update.message.from_user
    
    # Verificar se é um arquivo Excel
    if document.file_name.endswith(('.xlsx', '.xls')):
        logging.info(f"📊 Recebida planilha: {document.file_name} de {user.first_name}")
        
        processing_msg = await update.message.reply_text("📥 **Baixando e processando sua planilha...**")
        
        try:
            # Baixar o arquivo
            file = await context.bot.get_file(document.file_id)
            file_path = f"temp_{document.file_name}"
            await file.download_to_drive(file_path)
            
            # 🎯 CHAMADA MODULAR - Processar a planilha (módulo externo)
            resultado = processar_planilha_excel(file_path, DATABASE_PATH)
            
            # Limpar arquivo temporário
            os.remove(file_path)
            
            # Resposta amigável
            if resultado['sucesso']:
                mensagem = f"""
✅ **Planilha processada com sucesso!**

📊 **Resumo:**
• Registros processados: {resultado['total_registros']}
• Novos transportes: {resultado['novos']}
• Atualizações: {resultado['atualizados']}
• Erros: {resultado['erros']}

💾 **Banco atualizado!** Agora temos {resultado['total_banco']} transportes.

💡 **Pergunte agora:**
• "Quantos transportes temos?"
• "Mostre os fretes mais recentes"
• "Temos chassis repetidos?"
                """
            else:
                mensagem = f"❌ **Erro ao processar:** {resultado['erro']}"
            
            await context.bot.edit_message_text(
                chat_id=processing_msg.chat_id,
                message_id=processing_msg.message_id,
                text=mensagem
            )
            
        except Exception as e:
            logging.error(f"Erro processando planilha: {e}")
            await context.bot.edit_message_text(
                chat_id=processing_msg.chat_id,
                message_id=processing_msg.message_id,
                text=f"❌ **Erro ao processar planilha:** {str(e)}"
            )
    
    else:
        await update.message.reply_text("📄 Envie uma planilha Excel (.xlsx ou .xls) para importar os dados.")

# 🆕 COMANDO DE AJUDA PARA PLANILHA
async def show_help_planilha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra ajuda sobre o formato da planilha"""
    ajuda_texto = """
📊 **Formato da Planilha para Importação**

**🏷️ Colunas Obrigatórias:**
• `chassis` - Número do chassis (texto único)
• `cargo_id` - ID da carga (texto)
• `origem` - Cidade de origem (texto)
• `destino` - Cidade de destino (texto)

**📝 Colunas Opcionais:**
• `status` - Status (padrão: "ativo")
• `valor_frete` - Valor do frete (número)

**💡 Exemplo:**
| chassis | cargo_id | origem    | destino   | status | valor_frete |
|---------|----------|-----------|-----------|--------|-------------|
| CHS006  | CARGO006 | São Paulo | Recife    | ativo  | 1950.00     |

**🚀 Como usar:**
1. Prepare sua planilha no formato acima
2. Envie o arquivo Excel para este chat
3. Aguarde o processamento
4. Consulte os dados com perguntas normais!
    """
    await update.message.reply_text(ajuda_texto)

# 🆕 HANDLER SIMPLES PARA MENSAGENS (POR ENQUANTO)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler básico para mensagens de texto"""
    user_message = update.message.text
    
    if user_message.lower() in ['/start', 'start', 'inicio']:
        await update.message.reply_text("🤖 **GAYA Bot Modular**\n\nEnvie uma planilha Excel ou use /planilha para ajuda.")
    else:
        await update.message.reply_text("📝 Estou processando sua mensagem... (Sistema modular em desenvolvimento)")

# FUNÇÃO MAIN LIMPA
def main():
    # Criar aplicação
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Handlers (AGORA LIMPOS)
    application.add_handler(CommandHandler("start", handle_message))
    application.add_handler(CommandHandler("planilha", show_help_planilha))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Iniciar
    logging.info("🚀 Iniciando GAYA Bot Modular...")
    application.run_polling()
    logging.info("✅ GAYA Modular iniciado!")

if __name__ == '__main__':
    main()
