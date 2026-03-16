import json
import pandas as pd
from bs4 import BeautifulSoup
from openai import OpenAI
from collections import defaultdict
import time
from datetime import datetime
from dotenv import load_dotenv
import os

# 1. Configuración de Cliente
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("No se encontró la GROQ_API_KEY en el archivo .env")

client = OpenAI(
    api_key=GROQ_API_KEY, 
    base_url="https://api.groq.com/openai/v1"
)

SYSTEM_PROMPT = """Eres un analista senior de soporte de Golden Social Suite. Tu misión es extraer tickets técnicos detallados.

CONTEXTO DE LAS APLICACIONES:
- ALERT: Monitoreo en tiempo real, colectas, keywords, dashboards y filtros.
- SCAN: Analítica, macrosegmentación y análisis de sentimientos.
- KUNTUR: Gestión de menciones, métricas e impacto y límites de planes.

REGLAS MECÁNICAS DE IDENTIDAD Y CIERRE:
1. Emisor del Reporte: Usa ÚNICAMENTE el nombre que aparece en el campo 'usuario' del JSON. Copia exacta.
2. CONTEXTO: Detalla la falla técnica y errores mencionados.
3. RESOLUCIÓN (CRÍTICO): Debes analizar el chat HASTA EL FINAL. La resolución es la explicación técnica final o la acción definitiva que solucionó el problema. No te detengas en la primera respuesta si hay más intervenciones posteriores que aclaran la causa (ej. 'refrescamiento de reflections' o 'descarga de cuenta').
4. CATEGORÍA: Problema, Explicación o Sugerencia.
5. SUB-CATEGORÍA: Muy específica y descriptiva.
6. NOMBRE DEL PRODUCTO: Alert, Scan o Kuntur.
7. RESUELTO POR: El nombre de la persona que dio la solución técnica DEFINITIVA. Si varios técnicos participaron, prioriza al que dio la explicación final que cerró el caso.
8. FECHAS: Formato 'DD Month YYYY HH:MM'. La 'Fecha de Resolución' debe ser la hora del último mensaje de éxito o agradecimiento definitivo.
9. ESTADO: 'Cerrado' si el usuario confirma éxito o agradece al final del hilo. 'Pendiente' si no hay resolución clara.
10. PRIORIDAD: Alta, Media o Baja.

CAMPOS REQUERIDOS EN JSON: 'Categoría (Ticket)', 'Subcategoría', 'Emisor del Reporte', 'Fecha de creación (Ticket)', 'Nombre del Producto', 'Estado (Ticket)', 'Contexto', 'Resolución', 'Fecha de Resolución', 'Resuelto por', 'Prioridad'.

Responde estrictamente en un objeto JSON con la llave "tickets"."""

def translate_date_to_spanish(date_str):
    if not date_str or pd.isna(date_str): return date_str
    months = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }
    for eng, esp in months.items():
        date_str = date_str.replace(eng, esp)
    return date_str

def extract_messages_by_day_normalized(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    messages_by_day = defaultdict(list)
    current_date = ""
    ultimo_usuario_real = "Desconocido"
    history = soup.find('div', class_='history')
    for div in history.find_all('div', recursive=False):
        if 'service' in div.get('class', []):
            date_text = div.get_text(strip=True)
            meses = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            if any(m in date_text for m in meses):
                current_date = date_text
            continue
        if 'default' in div.get('class', []):
            from_name_div = div.find('div', class_='from_name')
            raw_user = from_name_div.get_text(strip=True) if from_name_div else "Usuario Continuo"
            if raw_user != "Usuario Continuo": ultimo_usuario_real = raw_user
            time_div = div.find('div', class_='date')
            time = time_div.get_text(strip=True) if time_div else ""
            text_div = div.find('div', class_='text')
            content = text_div.get_text(separator=" ", strip=True) if text_div else "[Sin texto]"
            if current_date:
                messages_by_day[current_date].append({"hora": time, "usuario": ultimo_usuario_real, "contenido": content})
    return messages_by_day

def process_day_batch(day_data, date_label):
    chat_fragment = json.dumps(day_data, ensure_ascii=False)
    prompt = f"Analiza el chat del {date_label}. Identifica intervención final y cierre definitivo.\n\nCHAT:\n{chat_fragment}"
    
    retries = 3
    while retries > 0:
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            if "429" in str(e): # Rate limit
                print(f"   ! Límite alcanzado. Esperando 20s... (Reintentos: {retries})")
                time.sleep(20)
                retries -= 1
            else:
                raise e
    return {"tickets": []}

# --- EJECUCIÓN ---
print("--- CARGANDO ARCHIVO ---")
daily_messages = extract_messages_by_day_normalized('messages.html')
dias_list = [d for d in daily_messages.keys() if daily_messages[d]]

print(f"\nSe encontraron {len(dias_list)} días con mensajes.")
for i, d in enumerate(dias_list):
    print(f"{i+1}. {d}")

rango = input("\nSelecciona el rango (ej. 1-5 o 10-20): ")
start, end = map(int, rango.split('-'))
dias_seleccionados = dias_list[start-1:end]

raw_tickets = []
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iniciando procesamiento...")

for idx, day in enumerate(dias_seleccionados):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Procesando día {start + idx}: {day}...", end=" ", flush=True)
    try:
        res = process_day_batch(daily_messages[day], day)
        tickets_dia = res.get("tickets", [])
        raw_tickets.extend(tickets_dia)
        print(f"OK ({len(tickets_dia)} tickets)")
        time.sleep(2) # Delay para evitar 429
    except Exception as e:
        print(f"ERROR: {e}")

if raw_tickets:
    df = pd.DataFrame(raw_tickets)
    df = df.drop_duplicates(subset=['Fecha de creación (Ticket)', 'Contexto'])
    
    # 1. Renombrar y crear columnas faltantes
    df['Empresa'] = df['Emisor del Reporte']
    df['ID de Ticket'] = [f"{1001+i}" for i in range(len(df))]
    
    # 2. Traducir fechas a español
    df['Fecha de creación (Ticket)'] = df['Fecha de creación (Ticket)'].apply(translate_date_to_spanish)
    df['Fecha de Resolución'] = df['Fecha de Resolución'].apply(translate_date_to_spanish)
    
    # 3. Orden de columnas solicitado
    column_order = [
        'Categoría (Ticket)', 'Subcategoría', 'Empresa', 'Fecha de creación (Ticket)', 
        'Nombre del Producto', 'Estado (Ticket)', 'ID de Ticket', 'Resolución', 
        'Fecha de Resolución', 'Resuelto por', 'Prioridad', 'Contexto'
    ]
    
    # Asegurar que todas las columnas existan
    for col in column_order:
        if col not in df.columns: df[col] = ""
        
    df = df[column_order]
    
    filename = f"Reporte_Tickets_{start}_{end}.xlsx"
    df.to_excel(filename, index=False)
    print(f"\nPROCESO FINALIZADO. Archivo generado: {filename}")
else:
    print("\nNo se generaron tickets.")