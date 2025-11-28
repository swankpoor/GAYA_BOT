# gaya_llm_router.py - VERSÃO QUE CONSULTA BANCO REAL
import logging
from database_manager import obter_ultima_analise, obter_todas_inconsistencias

logger = logging.getLogger('GAYA_LLM')

def processar_com_llm(mensagem: str) -> str:
    """Processa mensagens consultando o banco de dados REAL"""
    try:
        logger.info(f"Processando pergunta com LLM: {mensagem}")
        
        mensagem_lower = mensagem.lower()
        
        # CONSULTA: Todas as inconsistências
        if any(palavra in mensagem_lower for palavra in ['inconsistencias', 'inconsistências', 'inconsistencias', 'erros', 'problemas']):
            inconsistencias = obter_todas_inconsistencias()
            
            if not inconsistencias:
                return "✅ **Nenhuma inconsistência encontrada no banco de dados.**"
            
            resposta = "🔍 **TODAS AS INCONSISTÊNCIAS DETECTADAS:**\n\n"
            
            for i, inc in enumerate(inconsistencias, 1):
                resposta += f"**{i}. {inc['descricao']}**\n"
                resposta += f"   • Criticidade: {inc['criticidade']}\n"
                resposta += f"   • Arquivo: {inc['nome_arquivo']}\n\n"
            
            resposta += f"📊 **Total: {len(inconsistencias)} inconsistências**\n\n"
            resposta += "💡 **Recomendações:**\n"
            resposta += "• Verifique os chassis nos LTs mencionados\n"
            resposta += "• Corrija as duplicidades no sistema JD\n"
            resposta += "• Reenvie a planilha após correções"
            
            return resposta
        
        # CONSULTA: Status da última análise
        elif any(palavra in mensagem_lower for palavra in ['status', 'análise', 'analise', 'ultima', 'última']):
            ultima_analise = obter_ultima_analise()
            
            if not ultima_analise:
                return "📭 **Nenhuma análise encontrada no banco.**\n\nEnvie uma planilha para análise."
            
            resposta = f"""📊 **STATUS DA ÚLTIMA ANÁLISE:**

📁 **Arquivo:** {ultima_analise['nome_arquivo']}
⏰ **Processada em:** {ultima_analise['data_processamento']}

📈 **ESTATÍSTICAS:**
• Registros processados: {ultima_analise['total_registros']}
• LTs únicos: {ultima_analise['lts_unicos']}
• Chassis únicos: {ultima_analise['chassis_unicos']}
• Inconsistências: {ultima_analise['inconsistencias_detectadas']}

🔧 **ACESSÓRIOS IDENTIFICADOS:**
{', '.join(ultima_analise['acessorios_identificados']) or 'Nenhum'}

💾 **Dados armazenados no banco para consultas.**"""
            
            return resposta
        
        # CONSULTA: Acessórios
        elif any(palavra in mensagem_lower for palavra in ['acessorios', 'acessórios', 'gabina', 'balao', 'pneu']):
            ultima_analise = obter_ultima_analise()
            
            if not ultima_analise:
                return "📭 **Nenhuma análise encontrada.** Envie uma planilha."
            
            acessorios = ultima_analise['acessorios_identificados']
            total_com_acessorios = ultima_analise['analise_acessorios'].get('registros_com_acessorios', 0)
            
            resposta = f"""🔧 **RELATÓRIO DE ACESSÓRIOS:**

📊 **Estatísticas:**
• Total de registros: {ultima_analise['total_registros']}
• Registros com acessórios: {total_com_acessorios}
• Acessórios identificados: {len(acessorios)}

🛠️ **ACESSÓRIOS ENCONTRADOS:**
"""
            for acessorio in acessorios:
                resposta += f"• {acessorio}\n"
            
            if acessorios:
                resposta += f"\n💡 **Acessórios críticos detectados:** {', '.join(acessorios)}"
            else:
                resposta += "\nℹ️ **Nenhum acessório crítico identificado**"
            
            return resposta
        
        # Resposta padrão com opções baseadas no banco
        else:
            ultima_analise = obter_ultima_analise()
            
            if ultima_analise:
                base_resposta = f"""🤖 **GAYA Bot - Sistema Inteligente**

💬 Sua pergunta: "{mensagem}"

📊 **Base de dados atual:**
• Última análise: {ultima_analise['nome_arquivo']}
• {ultima_analise['total_registros']} registros processados
• {ultima_analise['inconsistencias_detectadas']} inconsistências detectadas

🎯 **Posso ajudar com:**
• Listar todas as inconsistências
• Mostrar status da análise
• Relatório de acessórios
• Estatísticas dos dados

💡 **Pergunte:**
"mostre todas as inconsistências"
"status da análise" 
"quais acessórios foram encontrados"
"resumo dos dados" """
            else:
                base_resposta = f"""🤖 **GAYA Bot - Sistema Inteligente**

💬 Sua pergunta: "{mensagem}"

📭 **Nenhum dado no banco.** 

💡 **Envie uma planilha Excel** para:
• Análise inteligente
• Detecção de inconsistências
• Identificação de acessórios
• Armazenamento no banco"""

            return base_resposta
            
    except Exception as e:
        logger.error(f"Erro no LLM Router: {e}")
        return "🤖 **GAYA Bot - Sistema em Desenvolvimento**\n\nErro ao processar sua pergunta. Tente novamente."
