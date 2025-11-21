#!/usr/bin/env python3
"""
GAYA - Bot Telegram com Personalidade
Integração completa com a API GAYA
Personalidade: Educada, Debochada e Firme
"""

import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import sys
import os

# Adicionar o diretório atual ao path para importar outros módulos GAYA
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuração de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger('GAYA_TELEGRAM')

class GAYATelegramBot:
    def __init__(self):
        # 🔑 CONFIGURAÇÕES (Preferir variáveis de ambiente em produção)
        # OBS: Mantive o token hardcoded para sua conveniência neste ambiente de teste,
        # mas use os.getenv() em produção.
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "8257705817:AAGmQCwF4Bu9sO6zi4KVzX1qf9OjeE2WWPo")
        self.api_url = os.getenv("API_URL", "http://localhost:5000")
        self.admin_user_id = os.getenv("ADMIN_USER_ID", "51981369614")

        # 👨‍💻 Info do Criador
        self.criador_info = {
            'nome': 'Leonardo Silva',
            'telefone': '+55 (51) 98136-9614', 
            'email': 'leolfs@yahoo.com.br',
            'desde': '2024-11-22'
        }

        # Inicializar aplicação Telegram
        self.application = Application.builder().token(self.telegram_token).build()

        self._setup_handlers()
        logger.info("🤖 Bot Telegram GAYA inicializado!")

    def _setup_handlers(self):
        """Configura todos os handlers do bot"""

        # Comandos
        self.application.add_handler(CommandHandler("start", self._comando_start))
        self.application.add_handler(CommandHandler("help", self._comando_help))
        self.application.add_handler(CommandHandler("fretes", self._comando_fretes))
        self.application.add_handler(CommandHandler("sobre", self._comando_sobre))
        self.application.add_handler(CommandHandler("admin", self._comando_admin))

        # Mensagens de texto
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._processar_mensagem))

        # Callbacks de botões
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))

        # Arquivos (planilhas, etc)
        self.application.add_handler(MessageHandler(
            filters.Document.ALL, 
            self._processar_arquivo
        ))

    async def _comando_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Boas vindas"""
        user = update.effective_user
        mensagem = f"""
🤖 *Olá, {user.first_name}! Eu sou a GAYA!*

*Sua Assistente Logística Inteligente* 🚛

💡 *O que posso fazer por você:*
• Consultar fretes disponíveis
• Gerenciar motoristas e veículos  
• Processar planilhas e documentos
• Calcular rotas e custos
• E muito mais!

📋 *Comandos disponíveis:*
/fretes - Ver fretes disponíveis
/sobre - Sobre mim e meu criador
/help - Ajuda e instruções

*Mande uma mensagem ou use os comandos acima!*
        """.strip()

        keyboard = [
            [InlineKeyboardButton("📦 Ver Fretes", callback_data="ver_fretes")],
            [InlineKeyboardButton("ℹ️ Sobre a GAYA", callback_data="sobre_gaya")],
            [InlineKeyboardButton("📊 Enviar Planilha", callback_data="enviar_planilha")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            mensagem,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _comando_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help - Ajuda"""
        mensagem = """
🆘 *Ajuda da GAYA - Comandos Disponíveis*

📋 *Comandos Principais:*
/start - Iniciar conversa
/fretes - Listar fretes disponíveis
/sobre - Informações sobre mim

📊 *Envio de Arquivos:*
Você pode me enviar:
• Planilhas Excel (.xlsx, .csv)
• Documentos PDF
• Arquivos JSON e XML
*Eu processarei automaticamente!*

💬 *Conversa Natural:*
Pode me perguntar coisas como:
• "Quais fretes tem para São Paulo?"
• "Preciso de um frete urgente"
• "Mostre motoristas disponíveis"

🎭 *Minha Personalidade:*
Sou *educada*, mas com um toque de *deboche* saudável, e *firme* quando preciso ser!

*Precisa de mais ajuda? É só perguntar!*
        """.strip()

        await update.message.reply_text(mensagem, parse_mode='Markdown')

    async def _comando_fretes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /fretes - Listar fretes (Usado em comandos diretos)"""
        try:
            response = requests.get(f"{self.api_url}/fretes_test")

            if response.status_code == 200:
                dados = response.json()
                fretes = dados.get('fretes', [])

                if not fretes:
                    mensagem = "📭 *Nenhum frete disponível no momento.*\n\nVolte mais tarde ou me envie uma planilha com novos fretes! 😊"
                    await update.message.reply_text(mensagem, parse_mode='Markdown')
                    return

                mensagem = "🚛 *Fretes Disponíveis:*\n\n"

                for i, frete in enumerate(fretes[:10], 1):  # Limitar a 10 fretes
                    mensagem += f"*{i}. {frete['origem']} → {frete['destino']}*\n"
                    mensagem += f"   📏 {frete['distancia_km']}km\n"
                    mensagem += f"   💰 R$ {frete['preco']:.2f}\n"
                    mensagem += f"   ⏱️ {frete['tempo_estimado']}\n"

                    if frete.get('urgente'):
                        mensagem += f"   🚨 *URGENTE*\n"

                    mensagem += "\n"

                if len(fretes) > 10:
                    mensagem += f"\n*... e mais {len(fretes) - 10} fretes!*"

                keyboard = [
                    [InlineKeyboardButton("🔄 Atualizar", callback_data="ver_fretes")],
                    [InlineKeyboardButton("📊 Enviar Mais Fretes", callback_data="enviar_planilha")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    mensagem,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

            else:
                await update.message.reply_text(
                    "❌ *Ops!* Tive um problema para buscar os fretes.\n\n"
                    "Meus circuitos estão dando uma de caminhão em estrada de terra... 🛻💨\n"
                    "Tente novamente em alguns instantes!",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"❌ Erro no comando fretes: {e}")
            await update.message.reply_text(
                "😅 *Parece que encontrei um buraco na estrada digital!*\n\n"
                "Recalculando rota... Tente novamente em alguns instantes! 🗺️🔧",
                parse_mode='Markdown'
            )

    async def _comando_sobre(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /sobre - Informações sobre a GAYA"""
        mensagem = f"""
🤖 *GAYA - Assistente Logística Inteligente*

*Sobre Mim:*
Sou uma IA especializada em logística, desenvolvida para revolucionar o transporte de cargas. 
Minha missão é tornar as operações logísticas mais eficientes e inteligentes!

👨‍💻 *Meu Criador:*
*Nome:* {self.criador_info['nome']}
*Contato:* {self.criador_info['telefone']}
*Email:* {self.criador_info['email']}
*Desde:* {self.criador_info['desde']}

🎯 *Minha Expertise:*
• Gestão de fretes e rotas
• Análise de dados logísticos  
• Processamento de documentos
• Otimização de operações

🎭 *Personalidade:*
Sou *educada* (sempre!), com um toque de *deboche* inteligente, e *firme* quando a situação exige. 
Afinal, logística sem personalidade é como caminhão sem motorista! 😄

*Como posso ajudar sua operação hoje?*
        """.strip()

        await update.message.reply_text(mensagem, parse_mode='Markdown')

    async def _comando_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /admin - Acesso administrativo"""
        user = update.effective_user

        # Verificar se é o admin
        if str(user.id) != self.admin_user_id:
            mensagem = """
❌ *Acesso Restrito!*

Desculpe, mas esta área é apenas para administradores. 
Parece que você não tem as credenciais necessárias... 

*Dica:* Talvez meu criador possa ajudá-lo? 😉
            """.strip()
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            return

        mensagem = """
🔐 *Painel Administrativo GAYA*

*Estatísticas do Sistema:*
📊 Fretes: Em desenvolvimento
👥 Usuários: Em desenvolvimento  
🚛 Motoristas: Em desenvolvimento

*Funcionalidades Admin:*
• Gerenciar usuários
• Visualizar logs
• Configurar sistema
• Backup de dados

*Esta área está em desenvolvimento!*
        """.strip()

        keyboard = [
            [InlineKeyboardButton("📊 Estatísticas", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 Gerenciar Usuários", callback_data="admin_users")],
           [InlineKeyboardButton("⚙️ Configurações", callback_data="admin_config")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(mensagem, reply_markup=reply_markup, parse_mode='Markdown')

    async def _processar_mensagem(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens de texto normais, chamando a API do LLM"""
        user_message = update.message.text
        user = update.effective_user

        logger.info(f"📨 Mensagem de {user.first_name} ({user.id}): {user_message}")

        # Mostrar "digitando..."
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        try:
            # Chamar API GAYA - CORRIGIDO O PAYLOAD PARA CORRESPONDER AO MODELO FASTAPI
            payload = {
                'text': user_message, 
                'username': f"{user.first_name} (Telegram)",
                'user_id': user.id 
            }

            response = requests.post(
                f"{self.api_url}/mensagem",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                dados = response.json()
                resposta = dados.get('response', 'Desculpe, não consegui processar sua mensagem.')

                # Adicionar assinatura GAYA se não tiver emoji
                if not any(emoji in resposta for emoji in ['😊', '😎', '🚛', '🤖', '💁', '😅']):
                    resposta += "\n\n🤖 *GAYA* - Sempre à disposição!"

                await update.message.reply_text(resposta, parse_mode='Markdown')

            else:
                await update.message.reply_text(
                   "😅 *Ops!* Meus circuitos deram uma pausa para o café... ☕\n\n"
                   "Tente novamente em alguns instantes!",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {e}")
            await update.message.reply_text(
                "🛠️ *Problema técnico detectado!*\n\n"
                "Parece que encontrei um desvio na estrada digital... 🚧\n"
                "Meu criador já foi notificado! Tente novamente em alguns minutos.",
                parse_mode='Markdown'
            )

    async def _processar_arquivo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa arquivos enviados (Planilhas)"""
        user = update.effective_user
        if not update.message.document:
             await update.message.reply_text("🤔 Não consigo processar esta mensagem como arquivo.")
             return
             
        nome_arquivo = update.message.document.file_name

        logger.info(f"📎 Arquivo recebido de {user.first_name}: {nome_arquivo}")

        await update.message.reply_text(
            f"📊 *Processando {nome_arquivo}...*\n\n"
            "Deixe-me analisar esses dados logísticos! 🔍",
            parse_mode='Markdown'
        )

        try:
            # Verificar tipo de arquivo
            extensao = os.path.splitext(nome_arquivo)[1].lower()
            extensoes_suportadas = ['.xlsx', '.xls', '.csv', '.pdf', '.json', '.xml']

            if extensao not in extensoes_suportadas:
                await update.message.reply_text(
                    f"❌ *Tipo não suportado:* {extensao.upper()}\n"
                    "Tipos suportados: Excel, CSV, PDF, JSON, XML",
                    parse_mode='Markdown'
                )
                return

            # Baixar o arquivo
            file = await update.message.document.get_file()
            file_path = f"/tmp/{nome_arquivo}"
            await file.download_to_drive(file_path)

            # Chamar API para processar a planilha
            with open(file_path, 'rb') as f:
                # O Content-Type deve ser apropriado para planilhas/arquivos
                files = {'file': (nome_arquivo, f, 'application/octet-stream')}
                headers = {"X-API-Key": "gaya_dev_2024"}
                response = requests.post(f"{self.api_url}/upload/planilha", files=files, headers=headers)

            # Limpar arquivo temporário
            os.remove(file_path)

            if response.status_code == 200:
                resultado = response.json()
                await update.message.reply_text(
                    f"✅ *Planilha processada com sucesso!*\n\n"
                    f"📊 *{resultado.get('total_registros', 0)} registros* encontrados\n"
                    f"🚛 *{resultado.get('fretes_processados', 0)} fretes* adicionados\n"
                    f"💾 *Banco de dados* atualizado!\n\n"
                    f"Use `/fretes` para ver os novos fretes! 😊",
                    parse_mode='Markdown'
                )
            else:
                # Tenta pegar a mensagem de erro da API se existir
                try:
                    erro_api = response.json().get("detail", response.text)
                except:
                    erro_api = response.text
                    
                await update.message.reply_text(
                    "❌ *Erro no processamento da API!*\n\n"
                    f"A planilha não pôde ser processada. Resposta da API: {erro_api[:100]}...",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"❌ Erro ao processar arquivo: {e}")
            await update.message.reply_text(
                "❌ *Erro no processamento!*\n\n"
                "Problema técnico ao processar o arquivo. Tente novamente.",
                parse_mode='Markdown'
            )

    async def _callback_fretes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Versão para callback (botão) do comando fretes, edita a mensagem"""
        query = update.callback_query
        try:
            response = requests.get(f"{self.api_url}/fretes_test")

            if response.status_code == 200:
                dados = response.json()
                fretes = dados.get('fretes', [])

                if not fretes:
                    mensagem = "📭 *Nenhum frete disponível no momento.*\n\nVolte mais tarde! 😊"
                    keyboard = [[InlineKeyboardButton("🔙 Voltar ao Início", callback_data="start_menu")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(mensagem, reply_markup=reply_markup, parse_mode='Markdown')
                    return

                mensagem = "🚛 *Fretes Disponíveis:*\n\n"

                for i, frete in enumerate(fretes[:10], 1):
                    mensagem += f"*{i}. {frete['origem']} → {frete['destino']}*\n"
                    mensagem += f"   📏 {frete['distancia_km']}km\n"
                    mensagem += f"   💰 R$ {frete['preco']:.2f}\n"
                    mensagem += f"   ⏱️ {frete['tempo_estimado']}\n"

                    if frete.get('urgente'):
                        mensagem += f"   🚨 *URGENTE*\n"

                    mensagem += "\n"
                
                if len(fretes) > 10:
                    mensagem += f"*... e mais {len(fretes) - 10} fretes!*"

                keyboard = [
                    [InlineKeyboardButton("🔄 Atualizar", callback_data="ver_fretes")],
                    [InlineKeyboardButton("🔙 Voltar ao Início", callback_data="start_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(mensagem, reply_markup=reply_markup, parse_mode='Markdown')

            else:
                await query.edit_message_text("❌ Erro ao buscar fretes. Tente novamente.", parse_mode='Markdown')

        except Exception as e:
            logger.error(f"❌ Erro no callback fretes: {e}")
            await query.edit_message_text("😅 Erro temporário. Tente novamente!", parse_mode='Markdown')
            
    async def _callback_sobre(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Versão para callback (botão) do comando sobre"""
        query = update.callback_query
        
        mensagem = f"""
🤖 *GAYA - Assistente Logística Inteligente*

👨‍💻 *Meu Criador:*
*Nome:* {self.criador_info['nome']}
*Contato:* {self.criador_info['telefone']}
*Email:* {self.criador_info['email']}

*Como posso ajudar sua operação hoje?*
""".strip()
        
        keyboard = [[InlineKeyboardButton("🔙 Voltar ao Início", callback_data="start_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(mensagem, reply_markup=reply_markup, parse_mode='Markdown')

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manipula callbacks de botões inline - CORRIGIDO SEM REPETIÇÕES"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        
        # Lógica Limpa
        if callback_data == "ver_fretes" or callback_data == "atualizar_fretes":
            await self._callback_fretes(update, context) 
        elif callback_data == "sobre_gaya":
            await self._callback_sobre(update, context)
        elif callback_data == "start_menu":
             # Simula o comando /start no mesmo chat, editando a mensagem anterior
            await self._comando_start(update, context)
        elif callback_data == "enviar_planilha":
            await query.edit_message_text(
               "📤 *Pronto para receber sua planilha!*\n\n"
               "Agora é só enviar o arquivo (Excel, CSV, PDF, JSON ou XML) "
               "e eu farei a mágica acontecer! 🪄\n\n"
               "*Dica:* Certifique-se de que os dados estão organizados em colunas.",
               parse_mode='Markdown'
           )
        elif callback_data.startswith("admin_"):
            # Handler genérico para botões admin (em desenvolvimento)
            await query.edit_message_text(
                f"🚧 *Funcionalidade Admin* ({callback_data.split('_')[1].upper()}) em desenvolvimento. ",
                parse_mode='Markdown'
            )
        # Os comandos "fretes_gaya" foram removidos por serem redundantes

    def run(self):
        """Inicia o bot"""
        logger.info("✅ Bot Telegram GAYA iniciado! Aguardando mensagens...")
        self.application.run_polling(poll_interval=1)

def main():
    """Função principal"""
    try:
        bot = GAYATelegramBot()
        bot.run()
    except Exception as e:
        logger.error(f"❌ Erro fatal no bot Telegram: {e}")
        # Se ocorrer um erro fatal, o terminal não deve travar
        sys.exit(1)

if __name__ == '__main__':
    main()
