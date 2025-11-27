import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger('GAYA_EXCEL')

class ExcelProcessor:
    def processar_excel(self, file_path):
        """Processa arquivo Excel e extrai dados básicos"""
        try:
            # Pausa para não sobrecarregar RAM
            import time
            time.sleep(2)
            
            # Lê a planilha específica
            df = pd.read_excel(file_path, sheet_name='TRK_TRANS_DTL')
            
            transportes = []
            
            # Processa linha por linha (seguro para RAM baixa)
            for index, row in df.iterrows():
                if index % 10 == 0:  # Pausa a cada 10 linhas
                    time.sleep(0.5)
                
                transporte = {
                    'load_number': str(row.get('Load No', '')).strip(),
                    'chassis': str(row.get('Serial Number', '')).strip(),
                    'destination_city': str(row.get('Destination City', '')).strip(),
                    'destination_state': str(row.get('Destination State', '')).strip(),
                    'customer_name': str(row.get('Destination Name', '')).strip(),
                    'planned_ship_date': self._formatar_data(row.get('Planned Ship Date')),
                    'vehicle_type': str(row.get('Vehicle Type', '')).strip(),
                    'driver_name': str(row.get('Driver Name', '')).strip()
                }
                
                # Só adiciona se tiver dados válidos
                if transporte['load_number'] or transporte['chassis']:
                    transportes.append(transporte)
            
            logger.info(f"📊 Extraídos {len(transportes)} transportes do Excel")
            return transportes
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar Excel: {e}")
            return []
    
    def _formatar_data(self, data):
        """Tenta formatar a data"""
        try:
            if pd.isna(data):
                return ""
            return str(data)
        except:
            return ""
