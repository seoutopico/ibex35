from fastapi import FastAPI
import yfinance as yf
from datetime import datetime, timedelta

app = FastAPI()

# Lista de algunas empresas del IBEX 35
IBEX35_COMPANIES = [
    "TEF.MC", "SAN.MC", "IBE.MC", "ITX.MC", "BBVA.MC",
    "REP.MC", "FER.MC", "AMS.MC", "ELE.MC", "NTGY.MC",
    "AENA.MC", "ACS.MC", "ACX.MC", "ALM.MC", "ANA.MC",
    "BKT.MC", "CABK.MC", "CLNX.MC", "COL.MC", "ENG.MC",
    "GRF.MC", "MEL.MC", "MTS.MC", "PHM.MC", "RED.MC",
    "SGRE.MC", "SAB.MC", "TL5.MC", "VIS.MC", "MAP.MC",
    "SOL.MC", "ROVI.MC", "SPS.MC", "LOG.MC", "CIE.MC"
]


@app.get("/")
async def saludo(query: str):
    return {"mensaje": f"Hola, {query}"}

@app.get("/ibex35")
async def get_ibex35_historical():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    data = {}
    for ticker in IBEX35_COMPANIES:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        
        data[ticker] = {
            "nombre": stock.info.get('longName', 'N/A'),
            "historico": hist['Close'].to_dict()
        }
    
    return data
