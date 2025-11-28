# database_manager.py - VERSÃO COMPLETA PARA SALVAR DADOS ESTRUTURADOS
import sqlite3
import logging
from typing import List, Dict, Any
import json
from datetime import datetime

logger = logging.getLogger('GAYA_DB')

def init_db(db_path: str = 'transportes.db'):
    """Inicializa o banco de dados com estrutura para dados analisados"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tabela para armazenar os dados estruturados da análise
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analises_planilhas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_arquivo TEXT UNIQUE,
                data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_registros INTEGER,
                lts_unicos INTEGER,
                chassis_unicos INTEGER,
                inconsistencias_detectadas INTEGER,
                acessorios_identificados TEXT,
                dados_estruturados JSON,
                analise_consistencia JSON,
                analise_acessorios JSON
            )
        """)
        
        # Tabela para inconsistências (para consultas rápidas)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inconsistencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analise_id INTEGER,
                tipo_inconsistencia TEXT,
                descricao TEXT,
                criticidade TEXT,
                registros_afetados TEXT,
                FOREIGN KEY (analise_id) REFERENCES analises_planilhas (id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ Banco de dados inicializado para dados analisados")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {e}")

def salvar_analise_planilha(resultado_analise: Dict[str, Any], db_path: str = 'transportes.db') -> bool:
    """Salva o resultado completo da análise no banco de dados"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Inserir análise principal
        cursor.execute("""
            INSERT OR REPLACE INTO analises_planilhas (
                nome_arquivo, total_registros, lts_unicos, chassis_unicos,
                inconsistencias_detectadas, acessorios_identificados,
                dados_estruturados, analise_consistencia, analise_acessorios
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            resultado_analise["planilha_metadata"]["nome_arquivo"],
            resultado_analise["planilha_metadata"]["total_registros"],
            resultado_analise["analise_consistencia"]["lts_unicos"],
            resultado_analise["analise_consistencia"]["chassis_unicos"],
            resultado_analise["analise_consistencia"]["inconsistencias_detectadas"],
            json.dumps(resultado_analise["analise_acessorios"]["acessorios_identificados"]),
            json.dumps(resultado_analise["dados_estruturados"]),
            json.dumps(resultado_analise["analise_consistencia"]),
            json.dumps(resultado_analise["analise_acessorios"])
        ))
        
        analise_id = cursor.lastrowid
        
        # Salvar inconsistências individualmente para consultas rápidas
        for inconsistencia in resultado_analise["analise_consistencia"]["inconsistencias"]:
            cursor.execute("""
                INSERT INTO inconsistencias (analise_id, tipo_inconsistencia, descricao, criticidade, registros_afetados)
                VALUES (?, ?, ?, ?, ?)
            """, (
                analise_id,
                inconsistencia["tipo"],
                inconsistencia["descricao"],
                inconsistencia["criticidade"],
                json.dumps(inconsistencia["registros_afetados"])
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Análise salva no banco. ID: {analise_id}, Inconsistências: {len(resultado_analise['analise_consistencia']['inconsistencias'])}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar análise no banco: {e}")
        return False

def obter_ultima_analise(db_path: str = 'transportes.db') -> Dict[str, Any]:
    """Obtém a última análise salva no banco"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM analises_planilhas 
            ORDER BY data_processamento DESC 
            LIMIT 1
        """)
        
        analise = cursor.fetchone()
        conn.close()
        
        if analise:
            return {
                "id": analise[0],
                "nome_arquivo": analise[1],
                "data_processamento": analise[2],
                "total_registros": analise[3],
                "lts_unicos": analise[4],
                "chassis_unicos": analise[5],
                "inconsistencias_detectadas": analise[6],
                "acessorios_identificados": json.loads(analise[7]),
                "dados_estruturados": json.loads(analise[8]),
                "analise_consistencia": json.loads(analise[9]),
                "analise_acessorios": json.loads(analise[10])
            }
        return None
        
    except Exception as e:
        logger.error(f"Erro ao obter última análise: {e}")
        return None

def obter_todas_inconsistencias(db_path: str = 'transportes.db') -> List[Dict[str, Any]]:
    """Obtém todas as inconsistências da última análise"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT i.*, a.nome_arquivo 
            FROM inconsistencias i
            JOIN analises_planilhas a ON i.analise_id = a.id
            ORDER BY a.data_processamento DESC
        """)
        
        inconsistencias = []
        for row in cursor.fetchall():
            inconsistencias.append({
                "id": row[0],
                "analise_id": row[1],
                "tipo": row[2],
                "descricao": row[3],
                "criticidade": row[4],
                "registros_afetados": json.loads(row[5]),
                "nome_arquivo": row[6]
            })
        
        conn.close()
        return inconsistencias
        
    except Exception as e:
        logger.error(f"Erro ao obter inconsistências: {e}")
        return []

# Manter funções existentes para compatibilidade
def contar_transportes(db_path: str = 'transportes.db') -> int:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transportes")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Erro ao contar transportes: {e}")
        return 0

def verificar_chassis_repetidos(db_path: str = 'transportes.db') -> List[tuple]:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT chassis, COUNT(*) FROM transportes GROUP BY chassis HAVING COUNT(*) > 1")
        repetidos = cursor.fetchall()
        conn.close()
        return repetidos if repetidos else []
    except Exception as e:
        logger.error(f"Erro ao verificar chassis repetidos: {e}")
        return []
