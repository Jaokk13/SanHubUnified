# ============================================================================
# SANHUB UNIFIED — Motor de Geocodificação e Roteirização
# ============================================================================
# Adaptado e consolidado a partir do Roteirizador/Localizador.py
# ============================================================================

import math
import time
import re
import unicodedata
import difflib
import json
import os
import requests

from geopy.geocoders import Nominatim, ArcGIS
from geopy.extra.rate_limiter import RateLimiter

import database as db

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

# Banco local de bairros
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DB_FILE = os.path.join(SCRIPT_DIR, "banco_bairros_compartilhar.json")


def get_app_config() -> dict:
    return {
        "cidade":     db.get_setting("cidade", "Cuiabá"),
        "estado":     db.get_setting("estado", "MT"),
        "base_lat":   float(db.get_setting("base_lat", "-15.635673")),
        "base_lon":   float(db.get_setting("base_lon", "-56.023234")),
        "center_lat": float(db.get_setting("center_lat", "-15.5989")),
        "center_lon": float(db.get_setting("center_lon", "-56.0949")),
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────────────────────────────────────

def remover_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_endereco(texto: str) -> str:
    texto = texto.replace(".", " ")
    abreviacoes = {
        "adm": "Administrativo", "res": "Residencial", "jd": "Jardim",
        "jdm": "Jardim", "pq": "Parque", "vl": "Vila", "av": "Avenida",
        "dr": "Doutor", "sta": "Santa", "sto": "Santo", "prof": "Professor"
    }
    palavras = texto.split()
    return " ".join(abreviacoes.get(p.lower(), p) for p in palavras)


def calcular_distancia(coord1: tuple, coord2: tuple) -> float:
    """Fórmula de Haversine — retorna distância em km."""
    R = 6371
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def validar_coordenadas(lat: float, lon: float, config: dict) -> bool:
    if lat is None or lon is None:
        return False
    # Validação por raio (máx 100 km do centro)
    dist = calcular_distancia(
        (lat, lon), (config["center_lat"], config["center_lon"])
    )
    return dist <= 100


# ─────────────────────────────────────────────────────────────────────────────
# CARREGAMENTO DO BANCO LOCAL JSON (herdado do Roteirizador)
# ─────────────────────────────────────────────────────────────────────────────

_local_db_cache: dict | None = None


def _load_local_db() -> dict:
    global _local_db_cache
    if _local_db_cache is not None:
        return _local_db_cache

    data = {}
    if os.path.exists(LOCAL_DB_FILE):
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for k, v in raw.items():
                data[k] = v
                data[remover_acentos(k).lower()] = v
        except Exception:
            pass
    _local_db_cache = data
    return data


# ─────────────────────────────────────────────────────────────────────────────
# GEOCODIFICAÇÃO (com fallback múltiplo e cache SQLite)
# ─────────────────────────────────────────────────────────────────────────────

def geocodificar(bairro: str, config: dict | None = None, log_fn=None) -> dict | None:
    """
    Tenta geocodificar um bairro/endereço usando fallback múltiplo:
    1. Cache SQLite
    2. Banco JSON local
    3. Nominatim (OSM)
    4. ArcGIS
    5. BrasilAPI (CEP)

    Retorna {'lat': float, 'lon': float, 'source': str} ou None.
    """
    if config is None:
        config = get_app_config()

    def _log(msg: str):
        if log_fn:
            log_fn(msg)

    bairro_clean = normalizar_endereco(bairro.strip())
    cidade = config["cidade"]
    estado = config["estado"]

    # Variações de nome para busca
    variacoes = [bairro_clean]
    bairro_raw = " ".join(bairro.replace(".", " ").split())
    if bairro_raw.lower() != bairro_clean.lower():
        variacoes.append(bairro_raw)
    for prefixo in ["jardim ", "residencial ", "parque ", "vila ", "setor ", "loteamento "]:
        if bairro_clean.lower().startswith(prefixo):
            variacoes.append(bairro_clean[len(prefixo):].strip())

    # ── TENTATIVA 0: Coordenadas diretas ──
    if "," in bairro:
        try:
            parts = bairro.split(",")
            if len(parts) == 2:
                c_lat, c_lon = float(parts[0].strip()), float(parts[1].strip())
                if validar_coordenadas(c_lat, c_lon, config):
                    return {"lat": c_lat, "lon": c_lon, "source": "coordenadas"}
        except ValueError:
            pass

    # ── TENTATIVA 1: Cache SQLite ──
    cached = db.get_cached_address(bairro_clean)
    if cached and validar_coordenadas(cached["lat"], cached["lon"], config):
        _log(f"[Cache] {bairro}")
        return cached

    # ── TENTATIVA 2: Banco JSON local ──
    local_db = _load_local_db()
    for nome_busca in variacoes:
        chave_norm = remover_acentos(nome_busca).lower()
        cand = local_db.get(bairro) or local_db.get(nome_busca) or local_db.get(chave_norm)
        if cand:
            lat, lon = cand.get("lat"), cand.get("lon")
            if validar_coordenadas(lat, lon, config):
                _log(f"[JSON Local] {nome_busca}")
                db.save_cached_address(bairro_clean, lat, lon, "json")
                return {"lat": lat, "lon": lon, "source": "json"}

        # Busca fuzzy no banco local
        chaves = list(local_db.keys())
        matches = difflib.get_close_matches(chave_norm, chaves, n=1, cutoff=0.92)
        if matches:
            cand = local_db[matches[0]]
            lat, lon = cand.get("lat"), cand.get("lon")
            if validar_coordenadas(lat, lon, config):
                _log(f"[JSON Fuzzy] {nome_busca} → {matches[0]}")
                db.save_cached_address(bairro_clean, lat, lon, "json_fuzzy")
                return {"lat": lat, "lon": lon, "source": "json_fuzzy"}

    # ── TENTATIVA 3: ArcGIS ──
    try:
        arcgis = ArcGIS()
        for nome_busca in variacoes:
            loc = arcgis.geocode(f"{nome_busca}, {cidade}, {estado}", timeout=5)
            if loc and validar_coordenadas(loc.latitude, loc.longitude, config):
                addr_norm = remover_acentos((loc.address or "").lower())
                
                # Rejeita resultados muito genéricos (ex: só o nome da cidade)
                cidade_norm = remover_acentos(cidade.lower())
                if len(addr_norm) <= len(cidade_norm) + 20 and cidade_norm in addr_norm:
                    # Muito genérico, tenta a próxima variação
                    continue
                
                busca_parts = [
                    p for p in remover_acentos(nome_busca.lower()).split()
                    if len(p) > 2 and p not in ["bairro", "jardim", "residencial", "parque", "vila", "setor"]
                ]
                if not busca_parts or any(p in addr_norm for p in busca_parts):
                    _log(f"[ArcGIS] {nome_busca}")
                    db.save_cached_address(bairro_clean, loc.latitude, loc.longitude, "arcgis")
                    return {"lat": loc.latitude, "lon": loc.longitude, "source": "arcgis"}
    except Exception:
        pass

    # ── TENTATIVA 4: BrasilAPI (CEP) ──
    cep_match = re.search(r"\b\d{5}-?\d{3}\b", bairro)
    if cep_match:
        cep = cep_match.group().replace("-", "")
        try:
            resp = requests.get(f"https://brasilapi.com.br/api/cep/v2/{cep}", timeout=5)
            if resp.status_code == 200:
                data_api = resp.json()
                if data_api.get("city", "").lower() == cidade.lower():
                    coords = data_api.get("location", {}).get("coordinates", {})
                    lat = float(coords.get("latitude", 0))
                    lon = float(coords.get("longitude", 0))
                    if lat and lon and validar_coordenadas(lat, lon, config):
                        _log(f"[BrasilAPI CEP] {cep}")
                        db.save_cached_address(bairro_clean, lat, lon, "brasilapi")
                        return {"lat": lat, "lon": lon, "source": "brasilapi"}
        except Exception:
            pass

    # ── TENTATIVA 5: Nominatim (OSM) ──
    try:
        geolocator = Nominatim(user_agent="sanhub_unified_v1")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        for nome_busca in variacoes:
            q = {"neighborhood": nome_busca, "city": cidade, "state": estado}
            loc = geocode(q)
            if loc and validar_coordenadas(loc.latitude, loc.longitude, config):
                _log(f"[Nominatim] {nome_busca}")
                db.save_cached_address(bairro_clean, loc.latitude, loc.longitude, "nominatim")
                return {"lat": loc.latitude, "lon": loc.longitude, "source": "nominatim"}
    except Exception:
        pass

    _log(f"[FALHA] Não encontrado: {bairro}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# ALGORITMOS DE ROTEAMENTO (TSP Nearest Neighbor + 2-Opt)
# ─────────────────────────────────────────────────────────────────────────────

def _distancia_rota(rota: list[dict]) -> float:
    d = sum(
        calcular_distancia((rota[i]["lat"], rota[i]["lon"]), (rota[i + 1]["lat"], rota[i + 1]["lon"]))
        for i in range(len(rota) - 1)
    )
    if rota:
        d += calcular_distancia((rota[-1]["lat"], rota[-1]["lon"]), (rota[0]["lat"], rota[0]["lon"]))
    return d


def nearest_neighbor(pontos: list[dict]) -> list[dict]:
    if not pontos:
        return []
    rota = [pontos[0]]
    visitados = {0}
    atual = 0
    while len(rota) < len(pontos):
        melhor_dist, proximo = float("inf"), -1
        for i, p in enumerate(pontos):
            if i not in visitados:
                d = calcular_distancia(
                    (pontos[atual]["lat"], pontos[atual]["lon"]),
                    (p["lat"], p["lon"]),
                )
                if d < melhor_dist:
                    melhor_dist, proximo = d, i
        if proximo != -1:
            visitados.add(proximo)
            rota.append(pontos[proximo])
            atual = proximo
    return rota


def two_opt(rota: list[dict]) -> list[dict]:
    melhor = rota[:]
    melhor_dist = _distancia_rota(melhor)
    melhorou = True
    while melhorou:
        melhorou = False
        for i in range(1, len(melhor) - 1):
            for j in range(i + 1, len(melhor)):
                nova = melhor[:]
                nova[i : j + 1] = reversed(nova[i : j + 1])
                nova_dist = _distancia_rota(nova)
                if nova_dist < melhor_dist:
                    melhor, melhor_dist, melhorou = nova, nova_dist, True
    return melhor


def otimizar_rota(pontos: list[dict]) -> list[dict]:
    """Aplica Nearest Neighbor seguido de 2-Opt."""
    if len(pontos) <= 2:
        return pontos
    return two_opt(nearest_neighbor(pontos))


# ─────────────────────────────────────────────────────────────────────────────
# ROTEIRIZAÇÃO DE EQUIPES
# ─────────────────────────────────────────────────────────────────────────────

def roteirizar_equipe(orders: list[dict], log_fn=None) -> dict:
    """
    Recebe uma lista de dicts de OS (com campo 'neighborhood'),
    geocodifica cada bairro e retorna a rota otimizada com distâncias.
    
    Retorna:
    {
        "route": [{"os_number", "neighborhood", "lat", "lon", "order", "distance_km", "source"}],
        "not_found": [str],
        "total_km": float,
        "maps_link": str
    }
    """
    config = get_app_config()

    base = {
        "os_numbers": ["BASE"],
        "neighborhood": f"{config['cidade']} - Base",
        "lat": config["base_lat"],
        "lon": config["base_lon"],
        "source": "config",
    }

    pontos = [base]
    not_found = []

    # Agrupar OSs por bairro
    bairros_unicos = {}
    for o in orders:
        bairro = o.get("neighborhood", "")
        if not bairro:
            not_found.append(o.get("os_number", "?"))
            continue
            
        bairro_key = bairro.upper().strip()
        if bairro_key not in bairros_unicos:
            bairros_unicos[bairro_key] = {
                "neighborhood": bairro,
                "os_numbers": [o["os_number"]],
            }
        else:
            bairros_unicos[bairro_key]["os_numbers"].append(o["os_number"])

    # Geocodificar apenas bairros únicos
    for b_key, b_data in bairros_unicos.items():
        coords = geocodificar(b_data["neighborhood"], config, log_fn)
        if coords:
            pontos.append({
                "os_numbers": b_data["os_numbers"],
                "neighborhood": b_data["neighborhood"],
                "lat": coords["lat"],
                "lon": coords["lon"],
                "source": coords["source"],
            })
        else:
            not_found.extend(b_data["os_numbers"])

    if len(pontos) < 2:
        return {"route": [], "not_found": not_found, "total_km": 0, "maps_link": ""}

    # Otimiza mantendo a base no início
    base_ponto = pontos[0]
    demais = pontos[1:]
    rota_otimizada = [base_ponto] + otimizar_rota(demais)

    # Adiciona retorno à base
    retorno = base_ponto.copy()
    retorno["neighborhood"] = f"{retorno['neighborhood']} (Retorno)"
    rota_otimizada.append(retorno)

    # Calcula distâncias acumuladas
    total_km = 0.0
    resultado = []
    for i, p in enumerate(rota_otimizada):
        dist = 0.0
        if i > 0:
            prev = rota_otimizada[i - 1]
            dist = calcular_distancia((prev["lat"], prev["lon"]), (p["lat"], p["lon"]))
            total_km += dist
        resultado.append({**p, "order": i, "distance_km": round(dist, 2)})

    # Link Google Maps
    coords_str = "/".join(f"{p['lat']},{p['lon']}" for p in rota_otimizada)
    maps_link = f"https://www.google.com/maps/dir/{coords_str}"

    return {
        "route": resultado,
        "not_found": not_found,
        "total_km": round(total_km, 2),
        "maps_link": maps_link,
    }


def montar_rota_salva(orders: list[dict]) -> dict:
    """
    Monta a visualização da rota para equipes que já têm `execution_order` salvo no banco.
    Não usa o caixeiro-viajante, apenas respeita a ordem do banco.
    """
    config = get_app_config()

    base = {
        "os_numbers": ["BASE"],
        "neighborhood": f"{config['cidade']} - Base",
        "lat": config["base_lat"],
        "lon": config["base_lon"],
        "source": "config",
    }

    pontos_bairro = []
    not_found = []
    
    # Agrupar bairros na ordem em que aparecem (preservando o execution_order)
    bairro_atual = None
    for o in orders:
        if o.get("execution_order") is None:
            continue
            
        bairro = o.get("neighborhood", "")
        if not bairro:
            not_found.append(o.get("os_number", "?"))
            continue
            
        if bairro != bairro_atual:
            bairro_atual = bairro
            pontos_bairro.append({
                "neighborhood": bairro,
                "os_numbers": [o["os_number"]]
            })
        else:
            pontos_bairro[-1]["os_numbers"].append(o["os_number"])
            
    pontos = [base]
    for b_data in pontos_bairro:
        coords = geocodificar(b_data["neighborhood"], config)
        if coords:
            pontos.append({
                "os_numbers": b_data["os_numbers"],
                "neighborhood": b_data["neighborhood"],
                "lat": coords["lat"],
                "lon": coords["lon"],
                "source": coords["source"],
            })
        else:
            not_found.extend(b_data["os_numbers"])
            
    pontos.append(base) # Volta para a base
    
    total_km = 0.0
    resultado = []
    for i, p in enumerate(pontos):
        dist = 0.0
        if i > 0:
            prev = pontos[i - 1]
            dist = calcular_distancia((prev["lat"], prev["lon"]), (p["lat"], p["lon"]))
            total_km += dist
        resultado.append({**p, "order": i, "distance_km": round(dist, 2)})

    coords_str = "/".join(f"{p['lat']},{p['lon']}" for p in pontos)
    maps_link = f"https://www.google.com/maps/dir/{coords_str}"

    return {
        "route": resultado,
        "not_found": not_found,
        "total_km": round(total_km, 2),
        "maps_link": maps_link,
    }

def dividir_em_equipes_sweep(orders: list[dict], num_equipes: int) -> dict:
    """
    Usa o Algoritmo Sweep (Varredura Angular) para dividir as OSs 
    em um número de equipes com base em suas localizações geocodificadas.
    Retorna { "equipe_index": [lista de os_number] }
    """
    config = get_app_config()
    center_lat = config["center_lat"]
    center_lon = config["center_lon"]
    
    if num_equipes <= 0 or not orders:
        return {}

    # 1. Geocodificar todas as OSs válidas
    pontos_geocodificados = []
    for o in orders:
        bairro = o.get("neighborhood", "")
        if not bairro:
            continue
        coords = geocodificar(bairro, config)
        if coords:
            # Calcular o ângulo usando math.atan2 (do centro)
            angulo = math.atan2(coords["lon"] - center_lon, coords["lat"] - center_lat)
            pontos_geocodificados.append({
                "os_number": o["os_number"],
                "lat": coords["lat"],
                "lon": coords["lon"],
                "angulo": angulo
            })

    # 2. Ordenar por ângulo (Sweep)
    pontos_geocodificados.sort(key=lambda x: x["angulo"])

    # 3. Dividir as fatias igualmente entre as equipes
    total = len(pontos_geocodificados)
    tamanho_base = total // num_equipes
    sobra = total % num_equipes

    resultado = {}
    idx_atual = 0

    for j in range(num_equipes):
        qtd = tamanho_base + (1 if j < sobra else 0)
        membros = pontos_geocodificados[idx_atual : idx_atual + qtd]
        idx_atual += qtd
        
        resultado[j] = [m["os_number"] for m in membros]

    return resultado
