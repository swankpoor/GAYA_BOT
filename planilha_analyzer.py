# planilha_analyzer.py
import pandas as pd
import logging
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime
import re

logger = logging.getLogger('GAYA_ANALYZER')

class PlanilhaAnalyzer:
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.mapeamento_campos = self._definir_mapeamento()
        self.verificacoes_criticas = self._definir_verificacoes()
    
    def _definir_mapeamento(self) -> Dict[str, str]:
        """Define o mapeamento completo dos campos da planilha"""
        return {
            # Identificadores Únicos
            "Rail Head": "origem_frete",
            "Customer": "cliente", 
            "Carrier Code": "transportadora",
            "Planned Ship Date": "data_embarque_planejada",
            "Planned Ship Time": "hora_embarque_planejada",
            "Sales Order": "ordem_venda",
            "Load No": "lt",
            "JD Quote": "cotacao_jd",
            "Destination Code": "codigo_destino",
            "Destination City": "cidade_destino",
            "Destination State": "estado_destino",
            "Destination Name": "nome_destino",
            "Material": "codigo_material",
            "Material Description": "descricao_material",
            "Serial Number": "chassis",
            "Vehicle Name": "tipo_veiculo",
            "Vehicle Type": "codigo_veiculo",
            "Accessory": "acessorios",
            "Special Instructions": "instrucoes_especiais",
            "AMS": "ams",
            "RTK": "rtk",
            "Toll Number": "numero_pedagio",
            "Plate Truck": "placa_cavalo",
            "Axel Truck": "eixos_cavalo",
            "Plate Trailer": "placa_carreta",
            "Axel Trailer": "eixos_carreta",
            "Driver Name": "motorista",
            "Driver Document": "cpf_motorista",
            "Route Name": "rota",
            "Load Order": "ordem_carregamento",
            "Delivery Date": "data_entrega",
            "Delivery Time": "hora_entrega"
        }
    
    def _definir_verificacoes(self) -> Dict[str, Dict]:
        """Define as verificações críticas de consistência"""
        return {
            "chassis_lt_incompativel": {
                "descricao": "Mesmo chassis aparece em LTs diferentes",
                "criticidade": "ALTA",
                "acao": "Bloquear importação até correção"
            },
            "lt_chassis_duplicado": {
                "descricao": "Mesmo LT tem chassis duplicados no mesmo envio",
                "criticidade": "ALTA", 
                "acao": "Alertar para verificação"
            },
            "destino_inconsistente": {
                "descricao": "Código e nome de destino não correspondem",
                "criticidade": "MEDIA",
                "acao": "Validar com base histórica"
            },
            "data_entrega_anterior_embarque": {
                "descricao": "Data de entrega anterior ao embarque",
                "criticidade": "ALTA",
                "acao": "Corrigir datas"
            },
            "ordem_carregamento_invalida": {
                "descricao": "Ordem de carregamento fora de sequência ou duplicada",
                "criticidade": "MEDIA",
                "acao": "Reordenar automaticamente"
            },
            "acessorios_criticos_nao_identificados": {
                "descricao": "Acessórios críticos como GABINA DUAL não identificados corretamente",
                "criticidade": "MEDIA",
                "acao": "Revisar campo de acessórios"
            }
        }
    
    def analisar_planilha(self, file_path: str) -> Dict[str, Any]:
        """
        Analisa a planilha de forma inteligente e retorna JSON estruturado
        com verificações de consistência
        """
        try:
            logger.info(f"🔍 Iniciando análise inteligente da planilha: {file_path}")
            
            # 1. Ler dados brutos da planilha
            dados_brutos = self._ler_planilha(file_path)
            if not dados_brutos:
                return self._criar_resposta_erro("Erro ao ler planilha")
            
            # 2. Mapear e estruturar os dados
            dados_estruturados = self._estruturar_dados(dados_brutos)
            
            # 3. Realizar verificações de consistência
            analise_consistencia = self._verificar_consistencia(dados_estruturados)
            
            # 4. Analisar acessórios críticos
            analise_acessorios = self._analisar_acessorios(dados_estruturados)
            
            # 5. Preparar resposta final
            return self._preparar_resposta_final(
                file_path, dados_estruturados, analise_consistencia, analise_acessorios
            )
            
        except Exception as e:
            logger.error(f"Erro na análise da planilha: {str(e)}")
            return self._criar_resposta_erro(f"Erro na análise: {str(e)}")
    
    def _ler_planilha(self, file_path: str) -> pd.DataFrame:
        """Lê a planilha Excel e retorna DataFrame"""
        try:
            df = pd.read_excel(file_path)
            logger.info(f"📊 Planilha lida: {len(df)} registros, {len(df.columns)} colunas")
            return df
        except Exception as e:
            logger.error(f"Erro ao ler planilha: {str(e)}")
            return None
    
    def _estruturar_dados(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Estrutura os dados conforme mapeamento"""
        dados_estruturados = []
        
        for index, row in df.iterrows():
            registro = {}
            
            # Mapear cada campo
            for coluna_original, campo_mapeado in self.mapeamento_campos.items():
                if coluna_original in row:
                    valor = row[coluna_original]
                    
                    # Tratamento específico para alguns campos
                    if pd.isna(valor):
                        valor = None
                    elif campo_mapeado in ['acessorios', 'instrucoes_especiais']:
                        valor = str(valor) if valor else ""
                    
                    registro[campo_mapeado] = valor
            
            # Adicionar metadados
            registro['_linha_planilha'] = index + 2  # +2 porque Excel começa na 1 e header na 1
            registro['_processado_em'] = datetime.now().isoformat()
            
            dados_estruturados.append(registro)
        
        logger.info(f"✅ Dados estruturados: {len(dados_estruturados)} registros")
        return dados_estruturados
    
    def _verificar_consistencia(self, dados: List[Dict]) -> Dict[str, Any]:
        """Realiza verificações críticas de consistência nos dados"""
        inconsistências = []
        alertas = []
        
        # Agrupar por LT e Chassis para verificações
        lt_chassis_map = {}
        chassis_lt_map = {}
        
        for registro in dados:
            lt = registro.get('lt')
            chassis = registro.get('chassis')
            
            if lt and chassis:
                # Verificar se chassis aparece em múltiplos LTs
                if chassis in chassis_lt_map and chassis_lt_map[chassis] != lt:
                    inconsistências.append({
                        "tipo": "chassis_lt_incompativel",
                        "descricao": f"Chassis {chassis} aparece no LT {chassis_lt_map[chassis]} e no LT {lt}",
                        "criticidade": "ALTA",
                        "registros_afetados": [chassis_lt_map[chassis], lt]
                    })
                else:
                    chassis_lt_map[chassis] = lt
                
                # Verificar se LT tem chassis duplicados
                if lt in lt_chassis_map:
                    if chassis in lt_chassis_map[lt]:
                        inconsistências.append({
                            "tipo": "lt_chassis_duplicado", 
                            "descricao": f"LT {lt} tem chassis {chassis} duplicado",
                            "criticidade": "ALTA",
                            "registros_afetados": [lt]
                        })
                    else:
                        lt_chassis_map[lt].append(chassis)
                else:
                    lt_chassis_map[lt] = [chassis]
            
            # Verificar ordem de carregamento
            ordem = registro.get('ordem_carregamento')
            if ordem and not isinstance(ordem, (int, float)):
                try:
                    registro['ordem_carregamento'] = int(ordem)
                except:
                    alertas.append(f"Ordem de carregamento inválida: {ordem}")
        
        return {
            "inconsistencias_detectadas": len(inconsistências),
            "inconsistencias": inconsistências,
            "alertas": alertas,
            "total_registros_verificados": len(dados),
            "lts_unicos": len(lt_chassis_map),
            "chassis_unicos": len(chassis_lt_map)
        }
    
    def _analisar_acessorios(self, dados: List[Dict]) -> Dict[str, Any]:
        """Analisa os acessórios críticos (GABINA DUAL, DUALF ARR, BALAO, etc.)"""
        acessorios_identificados = set()
        registros_com_acessorios = 0
        acessorios_por_registro = []
        
        padroes_acessorios = {
            'GABINA DUAL': r'gabina.*dual|dual.*gabina',
            'DUALF ARR': r'dualf.*arr|arr.*dualf', 
            'BALAO': r'balao',
            'PNEU ARROZEIRO': r'arrozeiro|arr',
            'GABINA SIMPLES': r'gabina',
            'LARGURA': r'\d+mm',
            'COMPRIMENTO': r'\d+\.?\d*[ml]'
        }
        
        for registro in dados:
            acessorios = registro.get('acessorios', '')
            if acessorios and str(acessorios).strip():
                registros_com_acessorios += 1
                acessorios_registro = {}
                
                for tipo, padrao in padroes_acessorios.items():
                    if re.search(padrao, str(acessorios), re.IGNORECASE):
                        acessorios_identificados.add(tipo)
                        acessorios_registro[tipo] = True
                
                if acessorios_registro:
                    acessorios_por_registro.append({
                        'chassis': registro.get('chassis'),
                        'lt': registro.get('lt'),
                        'acessorios_originais': acessorios,
                        'acessorios_identificados': list(acessorios_registro.keys())
                    })
        
        return {
            "acessorios_identificados": list(acessorios_identificados),
            "registros_com_acessorios": registros_com_acessorios,
            "total_registros": len(dados),
            "detalhes_acessorios": acessorios_por_registro
        }
    
    def _preparar_resposta_final(self, file_path: str, dados_estruturados: List[Dict], 
                               analise_consistencia: Dict, analise_acessorios: Dict) -> Dict[str, Any]:
        """Prepara a resposta final com todos os dados analisados"""
        return {
            "planilha_metadata": {
                "nome_arquivo": file_path.split('/')[-1],
                "data_processamento": datetime.now().isoformat(),
                "total_registros": len(dados_estruturados),
                "versao_analise": "1.0"
            },
            "dados_estruturados": dados_estruturados,
            "analise_consistencia": analise_consistencia,
            "analise_acessorios": analise_acessorios,
            "resumo": {
                "status": "sucesso" if analise_consistencia["inconsistencias_detectadas"] == 0 else "alertas",
                "mensagem": "Planilha analisada com sucesso" if analise_consistencia["inconsistencias_detectadas"] == 0 else "Planilha analisada com alertas",
                "total_alertas": analise_consistencia["inconsistencias_detectadas"] + len(analise_consistencia["alertas"])
            }
        }
    
    def _criar_resposta_erro(self, mensagem: str) -> Dict[str, Any]:
        """Cria resposta de erro padronizada"""
        return {
            "planilha_metadata": {
                "nome_arquivo": "unknown",
                "data_processamento": datetime.now().isoformat(),
                "total_registros": 0,
                "versao_analise": "1.0"
            },
            "dados_estruturados": [],
            "analise_consistencia": {
                "inconsistencias_detectadas": 0,
                "inconsistencias": [],
                "alertas": [mensagem],
                "total_registros_verificados": 0
            },
            "analise_acessorios": {
                "acessorios_identificados": [],
                "registros_com_acessorios": 0,
                "total_registros": 0,
                "detalhes_acessorios": []
            },
            "resumo": {
                "status": "erro",
                "mensagem": mensagem,
                "total_alertas": 1
            }
        }


# Função de conveniência para uso rápido
def analisar_planilha(file_path: str, db_manager=None) -> Dict[str, Any]:
    """
    Função simples para análise rápida de planilha
    """
    analyzer = PlanilhaAnalyzer(db_manager)
    return analyzer.analisar_planilha(file_path)


# Teste rápido se executado diretamente
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        resultado = analisar_planilha(sys.argv[1])
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        print("Uso: python planilha_analyzer.py <caminho_planilha>")
