async def _processar_arquivo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa arquivos Excel - VERSÃO SIMPLIFICADA"""
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
        import time
        time.sleep(2)
        
        # 3️⃣ PROCESSAR EXCEL
        from excel_processor import ExcelProcessor
        processor = ExcelProcessor()
        transportes = processor.processar_excel(file_path)
        
        if not transportes:
            await update.message.reply_text(
                "❌ *Não consegui extrair dados* do arquivo.\n"
                "Verifique se é igual ao exemplo que você mostrou!",
                parse_mode='Markdown'
            )
            return
        
        # PAUSA PARA BANCO DE DADOS
        time.sleep(1)
        
        # 4️⃣ SALVAR NO BANCO
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
        
        # 6️⃣ LIMPAR ARQUIVO TEMPORÁRIO
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
        logger.error(f"❌ Erro geral: {e}")
        await update.message.reply_text(
            "❌ *Erro no processamento!*\n\n"
            "Detalhes técnicos (para debug):\n"
            f"`{str(e)[:100]}...`",
            parse_mode='Markdown'
        )

def _extrair_clientes(self, transportes):
    """Extrai clientes únicos para o resumo"""
    clientes = set()
    for t in transportes[:5]:  # Só os primeiros 5
        if t['customer_name']:
            clientes.add(t['customer_name'])
    return "\n".join([f"• {c}" for c in list(clientes)[:3]])

def _extrair_veiculos(self, transportes):
    """Extrai veículos únicos para o resumo"""
    veiculos = set()
    for t in transportes[:5]:
        if t['vehicle_type']:
            veiculos.add(t['vehicle_type'])
    return "\n".join([f"• {v}" for v in list(veiculos)[:3]])
