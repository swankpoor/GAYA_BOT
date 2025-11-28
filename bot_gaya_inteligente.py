# bot_gaya_inteligente.py
import logging
import os
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Importar todos os módulos modularizados
from planilha_analyzer import PlanilhaAnalyzer
from gaya_llm_router import processar_com_llm
from database_manager import (
    init_db, contar_transportes, verificar_chassis_repetidos,
    obter_transportes_por_periodo, obter_transportes_por_status,
    obter_transportes_por_origem_destino, obter_dados_chassis
)
from intelligent_responses import interpretar_pergunta

# Carregar variáveis do arquivo .env
load_dotenv()

# Configuração
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_PATH = 'transportes.db'

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('GAYA_BOT')

# Inicializar analyzer
planilha_analyzer = PlanilhaAnalyzer()

# 🆕 HANDLER DE DOCUMENTOS COM ANÁLISE INTELIGENTE
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa arquivos Excel com análise inteligente"""
    document = update.message.document
    user = update.message.from_user
    
    # Verificar se é um arquivo Excel
    if not document.file_name.lower().endswith(('.xlsx', '.xls')):
        await update.message.reply_text("❌ Por favor, envie um arquivo Excel (.xlsx ou .xls)")
        return
    
    logger.info(f"📊 Recebida planilha: {document.file_name} de {user.first_name}")
    
    processing_msg = await update.message.reply_text("🔍 **Analisando planilha inteligentemente...**")
    
    try:
        # Baixar o arquivo
        file = await context.bot.get_file(document.file_id)
        file_path = f"temp_{document.file_name}"
        await file.download_to_drive(file_path)
        
        # 🎯 ANÁLISE INTELIGENTE COM PLANILHA_ANALYZER
        resultado_analise = planilha_analyzer.analisar_planilha(file_path)
        
        # Limpar arquivo temporário
        os.remove(file_path)
        
        # Processar resultado da análise
        if resultado_analise["resumo"]["status"] == "erro":
            await context.bot.edit_message_text(
                chat_id=processing_msg.chat_id,
                message_id=processing_msg.message_id,
                text=f"❌ **Erro na análise:** {resultado_analise['resumo']['mensagem']}"
            )
            return
        
        # 🎯 AQUI FUTURAMENTE: SALVAR NO BANCO COM OS DADOS ESTRUTURADOS
        # Por enquanto, apenas mostramos a análise
        
        # Preparar resposta detalhada
        total_registros = resultado_analise["planilha_metadata"]["total_registros"]
        inconsistencias = resultado_analise["analise_consistencia"]["inconsistencias_detectadas"]
        acessorios_identificados = resultado_analise["analise_acessorios"]["acessorios_identificados"]
        
        mensagem = f"""
✅ **Análise Inteligente Concluída!**

📊 **Resumo da Planilha:**
• 📈 Registros processados: {total_registros}
• 🏷️ LTs únicos: {resultado_analise['analise_consistencia']['lts_unicos']}
• 🔑 Chassis únicos: {resultado_analise['analise_consistencia']['chassis_unicos']}
• ⚠️ Inconsistências: {inconsistencias}

🔧 **Acessórios Identificados:**
{', '.join(acessorios_identificados) if acessorios_identificados else '• Nenhum acessório crítico identificado'}

📋 **Status de Qualidade:**
{'🟢 **DADOS CONSISTENTES**' if inconsistencias == 0 else '🟡 **VERIFICAR INCONSISTÊNCIAS**'}

💡 **Próximos passos:**
• Use /dados para consultar o banco
• Pergunte sobre transportes específicos
• Verifique chassis repetidos com /chassis
"""
        
        # Adicionar detalhes de inconsistências se houver
        if inconsistencias > 0:
            mensagem += "\n\n🔍 **Inconsistências Detectadas:**"
            for inc in resultado_analise["analise_consistencia"]["inconsistencias"][:3]:  # Mostrar apenas as 3 primeiras
                mensagem += f"\n• {inc['descricao']}"
            
            if len(resultado_analise["analise_consistencia"]["inconsistencias"]) > 3:
                mensagem += f"\n• ... e mais {len(resultado_analise['analise_consistencia']['inconsistencias']) - 3}"
        
        await context.bot.edit_message_text(
            chat_id=processing_msg.chat_id,
            message_id=processing_msg.message_id,
            text=mensagem
        )
        
    except Exception as e:
        logger.error(f"Erro ao processar documento: {str(e)}")
        await context.bot.edit_message_text(
            chat_id=processing_msg.chat_id,
            message_id=processing_msg.message_id,
            text=f"❌ **Erro inesperado:** {str(e)}"
        )

# 🆕 HANDLER INTELIGENTE PARA MENSAGENS DE TEXTO
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler inteligente para mensagens de texto usando LLM"""
    user_message = update.message.text
    user = update.message.from_user
    
    logger.info(f"💬 Mensagem de {user.first_name}: {user_message}")
    
    # Comandos simples
    if user_message.lower() in ['/start', 'start', 'inicio', 'ola', 'oi']:
        await update.message.reply_text("""
🤖 **GAYA Bot - Sistema Inteligente Modular**

🎯 **Comandos disponíveis:**
/start - Iniciar bot
/planilha - Ajuda sobre planilhas  
/dados - Status do banco de dados
/chassis - Verificar chassis repetidos

💡 **Envie uma planilha Excel** para análise inteligente ou faça perguntas sobre os transportes!
""")
        return
    
    if user_message.lower() in ['/dados', 'dados', 'status']:
        try:
            total = contar_transportes(DATABASE_PATH)
            repetidos = verificar_chassis_repetidos(DATABASE_PATH)
            
            mensagem = f"""
📊 **Status do Banco de Dados:**

• 📈 Total de transportes: {total}
• 🔍 Chassis repetidos: {len(repetidos)}
• 💾 Arquivo: {DATABASE_PATH}

💡 **Perguntas possíveis:**
"Quantos transportes para São Paulo?"
"Mostre os fretes em trânsito"
"Quais chassis repetidos?"
"""
            await update.message.reply_text(mensagem)
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao acessar banco: {str(e)}")
        return
    
    if user_message.lower() in ['/chassis', 'chassis', 'repetidos']:
        try:
            repetidos = verificar_chassis_repetidos(DATABASE_PATH)
            if not repetidos:
                await update.message.reply_text("✅ Nenhum chassis repetido encontrado!")
            else:
                mensagem = "🔍 **Chassis Repetidos:**\n"
                for chassis, count in repetidos[:10]:  # Mostrar apenas os 10 primeiros
                    mensagem += f"• {chassis}: {count} vezes\n"
                
                if len(repetidos) > 10:
                    mensagem += f"• ... e mais {len(repetidos) - 10} chassis"
                
                await update.message.reply_text(mensagem)
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao verificar chassis: {str(e)}")
        return
    
    # 🎯 PROCESSAMENTO INTELIGENTE COM LLM ROUTER
    try:
        processing_msg = await update.message.reply_text("🤔 **Processando sua pergunta...**")
        
        # Usar LLM Router para processar a mensagem
        resposta_llm = processar_com_llm(user_message)
        
        await context.bot.edit_message_text(
            chat_id=processing_msg.chat_id,
            message_id=processing_msg.message_id,
            text=resposta_llm
        )
        
    except Exception as e:
        logger.error(f"Erro no processamento LLM: {str(e)}")
        await update.message.reply_text("""
🤖 **GAYA Bot - Sistema em Desenvolvimento**

💡 No momento, estou aprendendo a processar:
• Análise de planilhas Excel
• Consultas ao banco de dados
• Perguntas sobre transportes

📊 **Tente estes comandos:**
/planilha - Ajuda com planilhas
/dados - Status do banco
/chassis - Chassis repetidos

🎯 **Ou envie uma planilha Excel** para análise inteligente!
""")

# 🆕 COMANDO DE AJUDA PARA PLANILHA
async def show_help_planilha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra ajuda sobre o formato da planilha"""
    ajuda_texto = """
📊 **Formato da Planilha para Análise Inteligente**

**🏷️ Colunas Principais (mapeamento automático):**
• `Load No` - LT (identificador da carga)
• `Serial Number` - Chassis (identificador único)
• `Rail Head` - Origem do frete
• `Destination City` - Cidade de destino
• `Destination State` - Estado de destino

**🔧 Campos Críticos para Análise:**
• `Accessory` - Acessórios (GABINA DUAL, DUALF ARR, BALAO, etc.)
• `Load Order` - Ordem de carregamento
• `Vehicle Name` - Tipo de veículo
• `Planned Ship Date` - Data de embarque
• `Delivery Date` - Data de entrega

**💡 Sistema de Verificação Automática:**
✅ Detecção de chassis em múltiplos LTs
✅ Identificação de acessórios críticos  
✅ Validação de ordem de carregamento
✅ Análise de consistência temporal

**🚀 Como usar:**
1. Exporte sua planilha do sistema JD
2. Envie o arquivo Excel para este chat
3. Aguarde a análise inteligente
4. Receba insights automáticos!
"""
    await update.message.reply_text(ajuda_texto)

# 🆕 COMANDO PARA STATUS DO SISTEMA
async def show_system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra status do sistema modular"""
    status_texto = """
🔄 **GAYA Bot - Status do Sistema Modular**

**✅ Módulos Carregados:**
• 🤖 Bot Principal
• 🔍 Analisador de Planilhas
• 🧠 Roteador LLM
• 💾 Gerenciador de Banco
• 💬 Respostas Inteligentes

**📊 Estatísticas do Banco:**
"""
    try:
        total = contar_transportes(DATABASE_PATH)
        repetidos = verificar_chassis_repetidos(DATABASE_PATH)
        status_texto += f"• Transportes: {total}\n"
        status_texto += f"• Chassis repetidos: {len(repetidos)}\n"
    except Exception as e:
        status_texto += f"• ❌ Erro no banco: {str(e)}\n"
    
    status_texto += """
**🎯 Funcionalidades Ativas:**
✅ Upload e análise de planilhas
✅ Consultas inteligentes ao banco
✅ Detecção de inconsistências
✅ Sistema modular expandível

**🔮 Próximas Atualizações:**
• Armazenamento de JSON estruturado
• Histórico de alterações por chassis
• Otimização de cargas
• Roteirização inteligente
"""
    await update.message.reply_text(status_texto)

# FUNÇÃO PRINCIPAL LIMPA E SEGURA
def main():
    """Função principal com tratamento de erros robusto"""
    try:
        # Verificar token
        if not TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN não encontrado no arquivo .env")
            return
        
        # Inicializar banco de dados
        logger.info("💾 Inicializando banco de dados...")
        init_db(DATABASE_PATH)
        
        # Criar aplicação
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # 🎯 HANDLERS ORGANIZADOS
        application.add_handler(CommandHandler("start", handle_message))
        application.add_handler(CommandHandler("planilha", show_help_planilha))
        application.add_handler(CommandHandler("dados", handle_message))
        application.add_handler(CommandHandler("chassis", handle_message))
        application.add_handler(CommandHandler("status", show_system_status))
        
        # Handlers para mensagens
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        
        # 🚀 INICIAR BOT
        logger.info("🤖 Iniciando GAYA Bot Modular Inteligente...")
        print("=" * 50)
        print("🎯 GAYA BOT - SISTEMA MODULAR INTELLIGENTE")
        print("📊 Versão: 2.0 (Análise Inteligente)")
        print("🔧 Módulos: Planilha Analyzer + LLM Router + Database")
        print("=" * 50)
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Erro crítico ao iniciar bot: {str(e)}")
        print(f"❌ ERRO: {str(e)}")
        print("💡 Verifique:")
        print("   • Arquivo .env com TELEGRAM_BOT_TOKEN")
        print("   • Conexão com internet")
        print("   • Dependências instaladas (pip install -r requirements.txt)")

if __name__ == '__main__':
    main()
