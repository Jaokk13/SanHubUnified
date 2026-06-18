import json
import os
import unicodedata
import requests

# --- CONFIGURAÇÕES ---
# Define o diretório base como o local onde o script está salvo
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Arquivos
DB_FILE = os.path.join(SCRIPT_DIR, "banco_bairros_oficial.json")

def atualizar_banco():
    print("🔄 Iniciando atualização da base de bairros...")

    # 1. Carregar Banco Existente (Modo Append/Merge)
    db_data = {}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            print(f"📂 Banco atual carregado: {len(db_data)} registros encontrados.")
        except Exception as e:
            print(f"⚠️ Erro ao ler banco existente (o arquivo pode estar corrompido): {e}")
            print("   -> Criando um novo banco do zero.")
    else:
        print("⚠️ Arquivo 'banco_bairros_oficial.json' não existe. Criando um novo.")

    count_novos = 0
    count_atualizados = 0

    # 2. Buscar Bairros Automaticamente do OpenStreetMap (OSM)
    print("🌍 Consultando OpenStreetMap (Overpass API) para buscar bairros de Cuiabá...")
    try:
        # Query para buscar nós, caminhos e relações marcados como bairro/subúrbio em Cuiabá
        overpass_url = "http://overpass-api.de/api/interpreter"
        query = """
        [out:json][timeout:25];
        area["name"="Cuiabá"]->.searchArea;
        (
          node["place"~"suburb|neighbourhood"](area.searchArea);
          way["place"~"suburb|neighbourhood"](area.searchArea);
          relation["place"~"suburb|neighbourhood"](area.searchArea);
        );
        out center;
        """
        response = requests.get(overpass_url, params={'data': query})
        
        if response.status_code == 200:
            data = response.json()
            elementos = data.get('elements', [])
            print(f"   -> Encontrados {len(elementos)} locais no OSM.")
            
            for el in elementos:
                nome = el.get('tags', {}).get('name')
                if not nome: continue
                
                lat, lon = None, None
                if el['type'] == 'node':
                    lat, lon = el['lat'], el['lon']
                elif 'center' in el:
                    lat, lon = el['center']['lat'], el['center']['lon']
                
                if lat and lon:
                    chave = nome.upper().strip()
                    # Regra de segurança: Se já existe (manual ou anterior), NÃO sobrescreve
                    if chave in db_data: continue
                    
                    db_data[chave] = {
                        "lat": lat, 
                        "lon": lon, 
                        "tipo": "importado_osm"
                    }
                    count_novos += 1
        else:
            print(f"   -> Erro na API OSM: Código {response.status_code}")
            
    except Exception as e:
        print(f"   -> Erro de conexão com OSM: {e}")

    # 4. Salvar Banco Atualizado
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(db_data, f, ensure_ascii=False, indent=4)
        
        print("-" * 40)
        print(f"✅ ATUALIZAÇÃO CONCLUÍDA!")
        print(f"   - Novos bairros adicionados: {count_novos}")
        print(f"   - TOTAL DE REGISTROS NO BANCO: {len(db_data)}")
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ Erro crítico ao salvar o arquivo JSON: {e}")

if __name__ == "__main__":
    atualizar_banco()
