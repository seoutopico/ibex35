from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import yfinance as yf
import pandas as pd
from ta import trend, momentum, volatility
from datetime import datetime, timedelta
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

# Caché y tiempo de la última actualización
cache_data = None
last_update = None

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
    
      # Fechas de los datos consultados
    start_date = data.index[0].strftime('%Y-%m-%d')
    end_date = data.index[-1].strftime('%Y-%m-%d')

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

    return f"""
Símbolo: {symbol}
Fecha del análisis: Desde {start_date} hasta {end_date}
Precio Actual: {round(ultimo['Close'], 2)}
EMA_50: {round(ultimo['EMA_50'], 2) if not pd.isna(ultimo['EMA_50']) else 'N/A'}
RSI_14: {round(ultimo['RSI_14'], 2)}
MACD: {round(ultimo['MACD'], 2)}
MACD_Signal: {round(ultimo['MACD_Signal'], 2)}
Bollinger_Low: {round(ultimo['Bollinger_Low'], 2)}
Stochastic_K: {round(ultimo['Stochastic_K'], 2)}
Manos Fuertes: {'Sí' if ultimo['Manos_Fuertes'] else 'No'}
Manos Débiles: {'Sí' if ultimo['Manos_Débiles'] else 'No'}
Señales: {', '.join(señales)}
Puntuación Señal: {puntuación}
Predicción Subida 3%: {'Sí' if subir else 'No'}
"""

async def actualizar_cache():
    global cache_data, last_update
    resultados = []
    for symbol in ibex35_symbols:
        resultado = analizar_accion_semana_siguiente(symbol)
        if resultado:
            resultados.append(resultado)
    
    # Actualiza la caché con los nuevos resultados
    cache_data = '\n\n'.join(resultados)
    last_update = datetime.now()

async def actualizar_cache_periodicamente():
    while True:
        now = datetime.now()
        next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run + timedelta(days=1)
        seconds_until_next_run = (next_run - now).total_seconds()
        await asyncio.sleep(seconds_until_next_run)
        await actualizar_cache()

@app.on_event("startup")
async def startup_event():
    # Inicia la tarea para actualizar la caché a medianoche
    asyncio.create_task(actualizar_cache_periodicamente())

@app.get("/analisis", response_class=PlainTextResponse)
async def analisis_ibex35():
    global cache_data, last_update
    # Si no hay caché o han pasado más de 24 horas, actualiza
    if cache_data is None or (datetime.now() - last_update).total_seconds() > 86400:
        await actualizar_cache()
    return cache_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
