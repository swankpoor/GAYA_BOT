# gaya_db_query_tool.py - VERSÃO SIMPLIFICADA
import sqlite3
import logging
import os
import time
from datetime import datetime

logger = logging.getLogger('GAYA_DB')

# Configuração do banco
DB_FILE = "gaya_data.db"

def init_db():
    """Inicializa o banco de dados"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Tabela para armazenar dados dos arquivos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arquivos_processados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_arquivo TEXT NOT NULL,
                dados_json TEXT NOT NULL,
                usuario_id TEXT,
                data_processamento TEXT,
                resumo_ia TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ Banco de dados inicializado")
        
    except Exception as e:
        logger.error(f"❌ Erro no banco: {e}")

def salvar_dados_arquivo(nome_arquivo, dados, usuario_id, resumo_ia=""):
    """Salva dados do arquivo no banco"""
    try:
        time.sleep(0.5)  # Pausa para RAM
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO arquivos_processados 
            (nome_arquivo, dados_json, usuario_id, data_processamento, resumo_ia)
            VALUES (?, ?, ?, ?, ?)
        """, (
            nome_arquivo,
            str(dados),  # Converter para string por enquanto
            str(usuario_id),
            datetime.now().isoformat(),
            resumo_ia
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Dados salvos: {nome_arquivo}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar: {e}")
        return False
