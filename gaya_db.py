import sqlite3
import logging
import os
from datetime import datetime

logger = logging.getLogger('GAYA_DB')

class GayaDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Cria tabela para transportes se não existir"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transportes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    load_number TEXT,
                    chassis TEXT,
                    destination_city TEXT,
                    destination_state TEXT,
                    customer_name TEXT,
                    planned_ship_date TEXT,
                    vehicle_type TEXT,
                    driver_name TEXT,
                    created_at TEXT,
                    file_source TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Tabela transportes inicializada!")
            
        except Exception as e:
            logger.error(f"❌ Erro no banco: {e}")
    
    def salvar_transporte(self, dados):
        """Salva um transporte no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO transportes 
                (load_number, chassis, destination_city, destination_state, 
                 customer_name, planned_ship_date, vehicle_type, driver_name,
                 created_at, file_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados.get('load_number', ''),
                dados.get('chassis', ''),
                dados.get('destination_city', ''),
                dados.get('destination_state', ''),
                dados.get('customer_name', ''),
                dados.get('planned_ship_date', ''),
                dados.get('vehicle_type', ''),
                dados.get('driver_name', ''),
                datetime.now().isoformat(),
                dados.get('file_source', 'telegram')
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar: {e}")
            return False
    
    def contar_transportes(self):
        """Conta quantos transportes temos no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM transportes")
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"❌ Erro ao contar: {e}")
            return 0

# Instância global
db = GayaDatabase('/root/gaya-assistente/dados/gaya.db')
