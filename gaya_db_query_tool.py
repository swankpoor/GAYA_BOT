import sqlite3
import logging
import os
import time
from datetime import datetime
from threading import Lock

# ==========================================================
#  CONFIGURAÇÃO DE LOG
# ==========================================================
logger = logging.getLogger("GAYA_DB_TOOL")
logger.setLevel(logging.DEBUG)

# ==========================================================
#  ARQUIVOS E LOCK GLOBAL DO BD
# ==========================================================
DB_FILE = os.path.join(os.path.dirname(__file__), "gaya_data.db")
_db_lock = Lock()

# ==========================================================
#  UTILIDADES
# ==========================================================
def _pause(sec=1):
    """Pausa controlada para garantir tempo de processamento em máquinas fracas."""
    time.sleep(sec)


def _get_connection():
    """Retorna conexão segura com controle de LOCK."""
    _pause(0.2)
    conn = sqlite3.connect(DB_FILE, timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================================
#  INICIALIZAÇÃO DO BANCO
# ==========================================================
def init_db():
    with _db_lock:
        try:
            logger.info("Inicializando banco de dados GAYA...")
            _pause(1)

            conn = _get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fretes (
                    id INTEGER PRIMARY KEY,
                    origem TEXT NOT NULL,
                    destino TEXT NOT NULL,
                    status TEXT NOT NULL,
                    peso_kg REAL,
                    valor REAL,
                    data_cadastro TEXT
                );
                """
            )

            cursor.execute("SELECT COUNT(*) FROM fretes")
            if cursor.fetchone()[0] == 0:
                logger.warning("Banco vazio — inserindo dados mockados...")
                fretes_mock = [
                    ("São Paulo", "Rio de Janeiro", "Aguardando", 1500.5, 850.0, datetime.now().isoformat()),
                    ("Belo Horizonte", "Salvador", "Em Rota", 800.0, 1200.0, datetime.now().isoformat()),
                    ("Curitiba", "Porto Alegre", "Entregue", 2200.75, 950.0, datetime.now().isoformat()),
                    ("São Paulo", "Curitiba", "Aguardando", 1000.0, 700.0, datetime.now().isoformat()),
                    ("Rio de Janeiro", "São Paulo", "Em Rota", 500.0, 500.0, datetime.now().isoformat()),
                ]

                cursor.executemany(
                    "INSERT INTO fretes (origem, destino, status, peso_kg, valor, data_cadastro) VALUES (?, ?, ?, ?, ?, ?)",
                    fretes_mock,
                )
                conn.commit()
                logger.info("Dados mockados inseridos.")

            conn.close()
            _pause(0.5)
            logger.info("Banco pronto para uso.")

        except Exception as e:
            logger.error(f"Erro ao iniciar o banco: {e}")


# ==========================================================
#  CONSULTA INTELIGENTE (TOOL PRINCIPAL)
# ==========================================================
def consultar_fretes(query: str = "status_geral", status: str = None):
    """
    Função inteligente para consulta de fretes.

    query pode ser:
      • status_geral
      • total
      • total_por_status
      • listar_por_status
      • valor_total
      • mais_caro
    """

    _pause(0.5)

    with _db_lock:
        try:
            conn = _get_connection()
            cursor = conn.cursor()

            if query == "status_geral":
                cursor.execute("SELECT COUNT(*) FROM fretes")
                total = cursor.fetchone()[0]

                cursor.execute("SELECT status, COUNT(*) FROM fretes GROUP BY status")
                por_status = dict(cursor.fetchall())

                cursor.execute("SELECT SUM(valor) FROM fretes")
                valor_total = cursor.fetchone()[0] or 0.0

                result = {
                    "total_fretes": total,
                    "fretes_por_status": por_status,
                    "valor_total_bruto": round(valor_total, 2),
                    "timestamp": datetime.now().isoformat(),
                }

            elif query == "total":
                cursor.execute("SELECT COUNT(*) FROM fretes")
                result = {"total_fretes": cursor.fetchone()[0]}

            elif query == "total_por_status":
                cursor.execute("SELECT status, COUNT(*) FROM fretes GROUP BY status")
                result = {"fretes_por_status": dict(cursor.fetchall())}

            elif query == "listar_por_status":
                if not status:
                    return {"erro": "status não fornecido"}
                cursor.execute("SELECT * FROM fretes WHERE status = ?", (status,))
                linhas = [dict(row) for row in cursor.fetchall()]
                result = {"status": status, "fretes": linhas}

            elif query == "valor_total":
                cursor.execute("SELECT SUM(valor) FROM fretes")
                result = {"valor_total": cursor.fetchone()[0] or 0.0}

            elif query == "mais_caro":
                cursor.execute(
                    "SELECT * FROM fretes ORDER BY valor DESC LIMIT 1"
                )
                row = cursor.fetchone()
                result = {"frete_mais_caro": dict(row) if row else None}

            else:
                result = {"erro": "query inválida"}

            conn.close()
            _pause(0.3)
            return result

        except Exception as e:
            logger.error(f"Erro na consulta: {e}")
            return {"erro": str(e)}


# ==========================================================
#  TOOL SCHEMA PARA O LLM
# ==========================================================
TOOL_SCHEMA = {
    "name": "consultar_fretes",
    "description": "Consulta inteligente do banco GAYA. Suporta status geral, contagens, totais, listagem por status e frete mais caro.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Tipo da consulta: status_geral, total, total_por_status, listar_por_status, valor_total, mais_caro",
            },
            "status": {
                "type": "string",
                "description": "Status desejado quando query='listar_por_status'",
            },
        },
        "required": ["query"],
    },
}

TOOL_FUNCTIONS = {
    "consultar_fretes": consultar_fretes,
}

# Inicializa banco ao carregar
init_db()

logger.info("Tool de BD inteligente carregada com sucesso.")
