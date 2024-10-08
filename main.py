from fastapi import FastAPI
from fastapi.responses import JSONResponse
import yfinance as yf
import pandas as pd
from ta import trend, momentum, volatility
import json
from datetime import datetime
import asyncio

app = FastAPI()

# Lista actualizada de símbolos del IBEX 35
ibex35_symbols = [
    'TEF.MC', 'IBE.MC', 'ITX.MC', 'SAN.MC', 'BBVA.MC', 'CABK.MC', 'CLNX.MC',
    'ENG.MC', 'FER.MC', 'GRF.MC', 'IAG.MC', 'MAP.MC', 'MRL.MC', 'REP.MC',
    'TRE.MC', 'VIS.MC', 'ACX.MC', 'AMS.MC', 'AENA.MC', 'ALM.MC', 'CIE.MC',
    'COL.MC', 'ELE.MC', 'ENR.MC', 'MEL.MC', 'PHM.MC', 'RED.MC', 'SGRE.MC',
    'SOL.MC', 'NTGY.MC', 'SAB.MC'
]

CACHE_FILE = 'ibex35_analysis.json'

def obtener_datos_actuales(symbol, period='6mo', interval='1d'):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        if data.empty:
            print(f"No se encontraron datos para {symbol}.")
            return None
        return data
    except Exception as e:
        print(f"Error al obtener datos para {symbol}: {e}")
        return None

def analizar_accion_semana_siguiente(symbol):
    data = obtener_datos_actuales(symbol)
    if data is None or len(data) < 60:
        return None

    # Aplicar los indicadores técnicos
    data['EMA_50'] = trend.EMAIndicator(close=data['Close'], window=50).ema_indicator()
    data['RSI_14'] = momentum.RSIIndicator(close=data['Close'], window=14).rsi()
    data['MACD'] = trend.MACD(close=data['Close']).macd()
    data['MACD_Signal'] = trend.MACD(close=data['Close']).macd_signal()
    data['Bollinger_Low'] = volatility.BollingerBands(close=data['Close'], window=20).bollinger_lband()
    data['Stochastic_K'] = momentum.StochasticOscillator(high=data['High'], low=data['Low'], close=data['Close'], window=14).stoch()

    # Análisis Konkorde (compras manos fuertes y débiles)
    data['Volume_Mean'] = data['Volume'].rolling(window=20).mean()
    data['Manos_Fuertes'] = (data['Close'] > data['EMA_50']) & (data['Volume'] > data['Volume_Mean'])
    data['Manos_Débiles'] = (data['Close'] < data['EMA_50']) & (data['Volume'] > data['Volume_Mean'])

    ultimo = data.iloc[-1]

    señales = []
    puntuación = 0

    if not pd.isna(ultimo['EMA_50']) and ultimo['Close'] > ultimo['EMA_50']:
        señales.append('EMA_50 Alcista')
        puntuación += 1
    if ultimo['RSI_14'] < 30:
        señales.append('RSI_14 Sobrevendido')
        puntuación += 1
    elif ultimo['RSI_14'] > 70:
        señales.append('RSI_14 Sobrecomprado')
    if ultimo['MACD'] > ultimo['MACD_Signal']:
        señales.append('MACD Alcista')
        puntuación += 1
    if ultimo['Close'] < ultimo['Bollinger_Low']:
        señales.append('Precio por Debajo de Bollinger Low')
        puntuación += 1
    if ultimo['Stochastic_K'] < 20:
        señales.append('Stochastic Oscillator Sobrevendido')
        puntuación += 1
    if ultimo['Manos_Fuertes']:
        señales.append('Compra por Manos Fuertes')
        puntuación += 1
    if ultimo['Manos_Débiles']:
        señales.append('Compra por Manos Débiles')

    subir = puntuación >= 3

    return {
        'Símbolo': symbol,
        'Precio_Actual': round(ultimo['Close'], 2),
        'EMA_50': round(ultimo['EMA_50'], 2) if not pd.isna(ultimo['EMA_50']) else None,
        'RSI_14': round(ultimo['RSI_14'], 2),
        'MACD': round(ultimo['MACD'], 2),
        'MACD_Signal': round(ultimo['MACD_Signal'], 2),
        'Bollinger_Low': round(ultimo['Bollinger_Low'], 2),
        'Stochastic_K': round(ultimo['Stochastic_K'], 2),
        'Manos_Fuertes': bool(ultimo['Manos_Fuertes']),
        'Manos_Débiles': bool(ultimo['Manos_Débiles']),
        'Señales': señales,
        'Puntuación_Señal': puntuación,
        'Predicción_Subida_3%': subir
    }

async def actualizar_datos():
    print("Iniciando actualización de datos...")
    resultados = []
    for symbol in ibex35_symbols:
        resultado = analizar_accion_semana_siguiente(symbol)
        if resultado:
            resultados.append(resultado)
    
    with open(CACHE_FILE, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'data': resultados
        }, f)
    print("Actualización de datos completada.")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(actualizar_periodicamente())

async def actualizar_periodicamente():
    while True:
        await actualizar_datos()
        # Espera hasta la próxima medianoche
        now = datetime.now()
        next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run.replace(day=next_run.day + 1)
        seconds_until_next_run = (next_run - now).total_seconds()
        print(f"Próxima actualización en {seconds_until_next_run} segundos.")
        await asyncio.sleep(seconds_until_next_run)

@app.get("/analisis")
async def analisis_ibex35():
    try:
        with open(CACHE_FILE, 'r') as f:
            cached_data = json.load(f)
            print(f"Datos cacheados devueltos. Timestamp: {cached_data['timestamp']}")
            return JSONResponse(content=cached_data)
    except FileNotFoundError:
        print("Archivo de caché no encontrado. Generando nuevos datos...")
        await actualizar_datos()
        with open(CACHE_FILE, 'r') as f:
            return JSONResponse(content=json.load(f))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
