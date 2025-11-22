import logging
import time

# Configurações gerais da GAYA
CONFIG = {
    "PROCESSING_DELAY": 1.0,  # segundos de pausa entre etapas importantes
    "LLM_MODEL": "gpt-4o-mini",  # modelo leve padrão
    "DEBUG_MODE": True,
}

def pause(label="Pausa"):
    """
    Faz uma pausa controlada para dar tempo ao servidor/LLM.
    """
    delay = CONFIG["PROCESSING_DELAY"]
    logging.getLogger("GAYA_CORE").debug(f"[⏳ {label}] Aguardando {delay}s para processamento...")
    time.sleep(delay)

