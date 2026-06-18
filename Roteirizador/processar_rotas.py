import pandas as pd
import json
import requests
import folium
import unicodedata
import math
import os
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# --- CONFIGURAÇÕES ---
ARQUIVO_EXCEL = "rotas.xlsx"
ARQUIVO_JSON_OFICIAL = "banco_bairros_oficial.json"
BASE_TIJUCAL = {"lat": -15.635673, "lon": -56.023234, "nome": "BASE (Tijucal)"}

# --- FUNÇÕES AUXILIARES ---

def normalizar_texto(texto):
    """Remove acentos e coloca em minúsculas para comparação."""
    if not isinstance(texto, str): return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()

def calcular_distancia(lat1, lon1, lat2, lon2):
    """Fórmula de Haversine para distância."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def resolver_tsp_nn(pontos):
    """Algoritmo Nearest Neighbor para ordenar a rota."""
    if not pontos: return []
    
    # Começa pela Base (assumindo que o primeiro ponto da lista já é a base ou será inserido)
    rota = [pontos[0]]
    visitados = {0}
    atual_idx = 0
    
    while len(rota) < len(pontos):
        melhor_dist = float('inf')
        proximo_idx = -1
        
        for i in range(len(pontos)):
            if i not in visitados:
                dist = calcular_distancia(
                    pontos[atual_idx]['lat'], pontos[atual_idx]['lon'],
                    pontos[i]['lat'], pontos[i]['lon']
                )
                if dist < melhor_dist:
                    melhor_dist = dist
                    proximo_idx = i
        
        if proximo_idx != -1:
            visitados.add(proximo_idx)
            rota.append(pontos[proximo_idx])
            atual_idx = proximo_idx
            
    return rota

# --- PROCESSAMENTO PRINCIPAL ---

def processar():
    # 1. Carregar Banco de Bairros (JSON)
    print("📂 Carregando banco de dados oficial...")
    db_bairros = {}
    if os.path.exists(ARQUIVO_JSON_OFICIAL):
        with open(ARQUIVO_JSON_OFICIAL, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            # Cria um índice normalizado para busca rápida
            for nome, dados in raw_data.items():
                db_bairros[normalizar_texto(nome)] = dados
    else:
        print("⚠️ Arquivo JSON não encontrado. Rode o script 'atualizar_base_bairros.py' primeiro.")
        return

    # 2. Ler Excel
    print(f"📊 Lendo {ARQUIVO_EXCEL}...")
    if not os.path.exists(ARQUIVO_EXCEL):
        print(f"⚠️ '{ARQUIVO_EXCEL}' não encontrado. Criando um arquivo de exemplo...")
        try:
            df_exemplo = pd.DataFrame({
                'Endereco': ['Av. Historiador Rubens de Mendonça', 'Rua 1', 'Av. Fernando Corrêa'],
                'Bairro': ['Bosque da Saúde', 'Boa Esperança', 'Coxipó'],
                'CEP': ['78050-000', '78068-375', '']
            })
            df_exemplo.to_excel(ARQUIVO_EXCEL, index=False)
            print(f"✅ Arquivo criado! Rode o script novamente para processar este exemplo.")
            return
        except Exception as e:
            print(f"❌ Erro ao criar arquivo de exemplo: {e}")
            return

    try:
        df = pd.read_excel(ARQUIVO_EXCEL, engine='openpyxl')
    except Exception as e:
        print(f"❌ Erro ao ler Excel: {e}")
        return

    # Configurar Geopy
    geolocator = Nominatim(user_agent="roteirizador_cuiaba_v1")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    resultados = []

    # 3. Iterar sobre as linhas
    print("🚀 Iniciando geocodificação (Fallback Triplo)...")
    
    for index, row in df.iterrows():
        endereco = str(row.get('Endereco', ''))
        bairro = str(row.get('Bairro', ''))
        cep = str(row.get('CEP', '')).replace('-', '').replace('.', '')
        
        lat, lon, fonte = None, None, None
        
        # --- PRIORIDADE 1: JSON OFICIAL ---
        bairro_norm = normalizar_texto(bairro)
        if bairro_norm in db_bairros:
            dados = db_bairros[bairro_norm]
            lat, lon = dados['lat'], dados['lon']
            fonte = "JSON (Oficial)"
            print(f"✅ [JSON] {bairro}")
            
        # --- PRIORIDADE 2: GEOPY (Endereço) ---
        if lat is None:
            query = f"{endereco} - {bairro}, Cuiabá, MT"
            try:
                loc = geocode(query)
                if loc:
                    lat, lon = loc.latitude, loc.longitude
                    fonte = "Geopy (Endereço)"
                    print(f"🔹 [Geopy] {endereco}")
            except: pass
            
        # --- PRIORIDADE 3: API CEP ---
        if lat is None and cep and len(cep) == 8:
            try:
                resp = requests.get(f"https://brasilapi.com.br/api/cep/v2/{cep}", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if 'location' in data and 'coordinates' in data['location']:
                        coords = data['location']['coordinates']
                        lat = float(coords.get('latitude'))
                        lon = float(coords.get('longitude'))
                        fonte = "API CEP"
                        print(f"🔸 [CEP] {cep}")
            except: pass
            
        if lat and lon:
            resultados.append({
                "nome": f"{endereco}, {bairro}",
                "lat": lat,
                "lon": lon,
                "fonte": fonte
            })
        else:
            print(f"❌ Não encontrado: {bairro}")

    # 4. Otimização (TSP)
    print("🔄 Otimizando rota...")
    # Adiciona a base no início para o cálculo
    lista_para_tsp = [BASE_TIJUCAL] + resultados
    rota_ordenada = resolver_tsp_nn(lista_para_tsp)
    
    # Adiciona retorno à base no final
    rota_ordenada.append(BASE_TIJUCAL.copy())
    rota_ordenada[-1]['nome'] += " (Retorno)"

    # 5. Gerar Mapa
    print("🗺️ Gerando mapa...")
    mapa = folium.Map(location=[BASE_TIJUCAL['lat'], BASE_TIJUCAL['lon']], zoom_start=12)
    
    # Linhas da rota
    pontos_linha = [[p['lat'], p['lon']] for p in rota_ordenada]
    folium.PolyLine(pontos_linha, color="blue", weight=2.5, opacity=0.8).add_to(mapa)
    
    for i, ponto in enumerate(rota_ordenada):
        # Define cor do pino
        fonte = ponto.get('fonte', 'Base')
        if fonte == "JSON (Oficial)": cor = "green"
        elif "Base" in fonte: cor = "black"
        else: cor = "red" # Geopy ou CEP (Dados externos/lentos)
        
        popup_text = f"<b>{i}. {ponto['nome']}</b><br>Fonte: {fonte}"
        
        folium.Marker(
            [ponto['lat'], ponto['lon']],
            popup=popup_text,
            icon=folium.Icon(color=cor, icon="info-sign")
        ).add_to(mapa)

    mapa.save("mapa_rota_otimizada.html")
    print("🏁 Concluído! Abra o arquivo 'mapa_rota_otimizada.html'.")

if __name__ == "__main__":
    processar()
