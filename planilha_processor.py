import pandas as pd
import sqlite3
import logging
import os
from typing import Dict, Any

def processar_planilha_excel(file_path: str, db_path: str = 'transportes.db') -> Dict[str, Any]:
    """Processa arquivo Excel e importa para o banco - MÓDULO SEPARADO"""
    try:
        # Ler a planilha
        df = pd.read_excel(file_path)
        logging.info(f"📈 Planilha lida: {len(df)} registros")
        
        # Mapear colunas
        mapeamento_colunas = {
            'chassis': ['chassis', 'chassi', 'numero_chassis'],
            'cargo_id': ['cargo_id', 'id_carga', 'carga'],
            'origem': ['origem', 'cidade_origem', 'de'],
            'destino': ['destino', 'cidade_destino', 'para'],
            'status': ['status', 'situacao', 'estado'],
            'valor_frete': ['valor_frete', 'frete', 'valor', 'preco']
        }
        
        # Normalizar nomes das colunas
        df.columns = [col.lower().strip() for col in df.columns]
        colunas_mapeadas = {}
        
        for coluna_padrao, alternativas in mapeamento_colunas.items():
            for alt in alternativas:
                if alt in df.columns:
                    colunas_mapeadas[coluna_padrao] = alt
                    break
        
        # Verificar colunas obrigatórias
        colunas_obrigatorias = ['chassis', 'cargo_id', 'origem', 'destino']
        for col in colunas_obrigatorias:
            if col not in colunas_mapeadas:
                return {'sucesso': False, 'erro': f'Coluna {col} não encontrada na planilha'}
        
        # Conectar ao banco
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        novos = 0
        atualizados = 0
        erros = 0
        
        # Processar cada linha
        for index, row in df.iterrows():
            try:
                # Extrair dados
                chassis = str(row[colunas_mapeadas['chassis']]).strip()
                cargo_id = str(row[colunas_mapeadas['cargo_id']]).strip()
                origem = str(row[colunas_mapeadas['origem']]).strip()
                destino = str(row[colunas_mapeadas['destino']]).strip()
                
                # Campos opcionais
                status = str(row[colunas_mapeadas.get('status', 'status')]).strip() if colunas_mapeadas.get('status') in row else 'ativo'
                valor_frete = float(row[colunas_mapeadas.get('valor_frete', 'valor_frete')]) if colunas_mapeadas.get('valor_frete') in row else 0.0
                
                # Verificar se já existe
                cursor.execute("SELECT id FROM transportes WHERE chassis = ?", (chassis,))
                existe = cursor.fetchone()
                
                if existe:
                    # Atualizar
                    cursor.execute('''
                        UPDATE transportes 
                        SET cargo_id=?, origem=?, destino=?, status=?, valor_frete=?
                        WHERE chassis=?
                    ''', (cargo_id, origem, destino, status, valor_frete, chassis))
                    atualizados += 1
                else:
                    # Inserir novo
                    cursor.execute('''
                        INSERT INTO transportes (chassis, cargo_id, origem, destino, status, valor_frete, data_criacao)
                        VALUES (?, ?, ?, ?, ?, ?, date('now'))
                    ''', (chassis, cargo_id, origem, destino, status, valor_frete))
                    novos += 1
                    
            except Exception as e:
                logging.error(f"Erro na linha {index}: {e}")
                erros += 1
        
        conn.commit()
        
        # Contar total no banco
        cursor.execute("SELECT COUNT(*) FROM transportes")
        total_banco = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'sucesso': True,
            'total_registros': len(df),
            'novos': novos,
            'atualizados': atualizados,
            'erros': erros,
            'total_banco': total_banco
        }
        
    except Exception as e:
        logging.error(f"Erro geral processamento Excel: {e}")
        return {'sucesso': False, 'erro': str(e)}
