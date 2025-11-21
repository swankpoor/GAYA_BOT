import sqlite3
import logging
import os
from datetime import datetime

logger = logging.getLogger('GAYA_DB_TOOL')

# Define o nome do arquivo do banco de dados SQLite
DB_FILE = os.path.join(os.path.dirname(__file__), "gaya_data.db")

def _init_db():
    """Inicializa o banco de dados com dados mockados para teste."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Cria a tabela fretes, se não existir
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fretes (
                id INTEGER PRIMARY KEY,
                origem TEXT NOT NULL,
                destino TEXT NOT NULL,
                status TEXT NOT NULL,
                peso_kg REAL,
                valor REAL,
                data_cadastro TEXT
            );
        """)

        # Verifica se a tabela está vazia e insere dados mockados
        cursor.execute("SELECT COUNT(*) FROM fretes")
        if cursor.fetchone()[0] == 0:
            fretes_mock = [
                ('São Paulo', 'Rio de Janeiro', 'Aguardando', 1500.50, 850.00, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ('Belo Horizonte', 'Salvador', 'Em Rota', 800.00, 1200.00, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ('Curitiba', 'Porto Alegre', 'Entregue', 2200.75, 950.00, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ('São Paulo', 'Curitiba', 'Aguardando', 1000.00, 700.00, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ('Rio de Janeiro', 'São Paulo', 'Em Rota', 500.00, 500.00, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            ]
            for frete in fretes_mock:
                cursor.execute(
                    "INSERT INTO fretes (origem, destino, status, peso_kg, valor, data_cadastro) VALUES (?, ?, ?, ?, ?, ?)",
                    frete
                )
            conn.commit()
            logger.info("Banco de dados GAYA inicializado com dados mockados de fretes.")
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao inicializar o banco de dados: {e}")
    finally:
        if conn:
            conn.close()

# Inicializa o BD ao carregar o módulo
_init_db()


def consultar_status_geral_db():
    """
    Função de ferramenta para o LLM. 
    Consulta o banco de dados da GAYA para obter o status atual de fretes,
    contando o total de fretes e o status de cada um.
    
    Retorna uma string JSON detalhando o status atual.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. Contar total de fretes
        cursor.execute("SELECT COUNT(*) FROM fretes")
        total_fretes = cursor.fetchone()[0]
        
        # 2. Contar fretes por status
        cursor.execute("SELECT status, COUNT(*) FROM fretes GROUP BY status")
        status_counts = dict(cursor.fetchall())
        
        # 3. Calcular valor total
        cursor.execute("SELECT SUM(valor) FROM fretes")
        valor_total = cursor.fetchone()[0] or 0.0

        # Formata o resultado em JSON para ser lido pelo LLM
        return {
            "total_fretes": total_fretes,
            "fretes_por_status": status_counts,
            "valor_total_bruto": round(valor_total, 2),
            "data_ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except sqlite3.Error as e:
        logger.error(f"Erro na consulta ao banco de dados: {e}")
        return {"erro": f"Não foi possível consultar o banco de dados: {e}"}
    finally:
        if conn:
            conn.close()

# Dicionário mapeando a função Python ao seu SCHEMA (importante para o LLM)
TOOL_SCHEMA = {
    "name": "consultar_status_geral_db",
    "description": "Ferramenta essencial para responder perguntas sobre o número total de fretes, cargas, pedidos, status de logística e informações financeiras atuais armazenadas no banco de dados da GAYA.",
    "parameters": {
        "type": "object",
        "properties": {} # Não recebe argumentos, é uma consulta geral
    }
}

# Dicionário que mapeia o nome da função (string) para o objeto da função (referência)
TOOL_FUNCTIONS = {
    "consultar_status_geral_db": consultar_status_geral_db
}

logger.info("✅ Ferramenta de consulta DB carregada.")
