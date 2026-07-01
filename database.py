# ============================================================================
# SANHUB UNIFIED — Gerenciador de Banco de Dados SQLite
# ============================================================================
import sqlite3
import os
from datetime import date, datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sanhub.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Melhor concorrência para acesso simultâneo
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Inicializa todas as tabelas do banco de dados (idempotente)."""
    with get_conn() as conn:
        conn.executescript("""
            -- Tabela de Ordens de Serviço
            CREATE TABLE IF NOT EXISTS orders (
                os_number           TEXT PRIMARY KEY,
                solicitation_date   TEXT,
                neighborhood        TEXT,
                address             TEXT,
                service_description TEXT,
                limit_date          TEXT,
                status              TEXT DEFAULT 'Pendente',
                category            TEXT DEFAULT 'Indefinido',
                team_id             INTEGER,
                execution_order     INTEGER,
                import_date         TEXT,
                execution_date      TEXT,
                scheduled_date      TEXT,
                is_postergada       INTEGER DEFAULT 0,
                postergo_reason     TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL
            );

            -- Tabela de Equipes
            CREATE TABLE IF NOT EXISTS teams (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT UNIQUE NOT NULL,
                type    TEXT NOT NULL CHECK(type IN ('Calçada', 'Asfalto')),
                task_type TEXT NOT NULL DEFAULT 'Execução' CHECK(task_type IN ('Prévia', 'Execução'))
            );

            -- Cache de Geocodificação (bairros já localizados)
            CREATE TABLE IF NOT EXISTS cache_addresses (
                address TEXT PRIMARY KEY,
                lat     REAL NOT NULL,
                lon     REAL NOT NULL,
                source  TEXT,
                cached_at TEXT
            );

            -- Configurações globais da aplicação
            CREATE TABLE IF NOT EXISTS settings (
                key     TEXT PRIMARY KEY,
                value   TEXT NOT NULL
            );

            -- Insere configurações padrão se não existirem
            INSERT OR IGNORE INTO settings VALUES ('cidade', 'Cuiabá');
            INSERT OR IGNORE INTO settings VALUES ('estado', 'MT');
            INSERT OR IGNORE INTO settings VALUES ('base_lat', '-15.635673');
            INSERT OR IGNORE INTO settings VALUES ('base_lon', '-56.023234');
            INSERT OR IGNORE INTO settings VALUES ('center_lat', '-15.5989');
            INSERT OR IGNORE INTO settings VALUES ('center_lon', '-56.0949');
        """)
        
        # Migration para scheduled_date
        try:
            conn.execute("ALTER TABLE orders ADD COLUMN scheduled_date TEXT;")
        except sqlite3.OperationalError:
            pass

        # Adicionar as colunas de postergo nas bases existentes
        try:
            conn.execute("ALTER TABLE orders ADD COLUMN is_postergada INTEGER DEFAULT 0;")
            conn.execute("ALTER TABLE orders ADD COLUMN postergo_reason TEXT;")
        except sqlite3.OperationalError:
            pass
        
        try:
            conn.execute("ALTER TABLE teams ADD COLUMN task_type TEXT NOT NULL DEFAULT 'Execução' CHECK(task_type IN ('Prévia', 'Execução'));")
        except sqlite3.OperationalError:
            pass
        
        # Migration para address
        try:
            conn.execute("ALTER TABLE orders ADD COLUMN address TEXT;")
        except sqlite3.OperationalError:
            pass

        # Migration para force_task_type (override manual de Prévia/Execução)
        try:
            conn.execute("ALTER TABLE orders ADD COLUMN force_task_type TEXT;")
        except sqlite3.OperationalError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))


# ─────────────────────────────────────────────────────────────────────────────
# ORDENS DE SERVIÇO
# ─────────────────────────────────────────────────────────────────────────────

def upsert_orders(orders: list[dict]) -> dict:
    """
    Insere ou ignora OSs. Retorna contagem de novas inserções.
    NÃO sobrescreve dados existentes (equipe, status, etc.).
    """
    new_count = 0
    with get_conn() as conn:
        for o in orders:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO orders
                    (os_number, solicitation_date, neighborhood, address,
                     service_description, limit_date, status,
                     category, import_date, is_postergada, postergo_reason)
                VALUES (?, ?, ?, ?, ?, ?, 'Pendente', ?, ?, ?, ?)
            """, (
                o["os_number"],
                o.get("solicitation_date", ""),
                o.get("neighborhood", ""),
                o.get("address", ""),
                o.get("service_description", ""),
                o.get("limit_date", ""),
                o.get("category", "Indefinido"),
                date.today().isoformat(),
                1 if o.get("is_postergada") else 0,
                o.get("postergo_reason", "")
            ))
            if cursor.rowcount > 0:
                new_count += 1
            else:
                # Update postergo info and address for existing orders
                if "is_postergada" in o:
                    conn.execute("""
                        UPDATE orders 
                        SET is_postergada = ?, postergo_reason = ?, address = COALESCE(?, address)
                        WHERE os_number = ? AND status = 'Pendente'
                    """, (
                        1 if o.get("is_postergada") else 0,
                        o.get("postergo_reason", ""),
                        o.get("address", ""),
                        o["os_number"]
                    ))
                else:
                    conn.execute("""
                        UPDATE orders 
                        SET address = COALESCE(?, address)
                        WHERE os_number = ? AND status = 'Pendente'
                    """, (
                        o.get("address", ""),
                        o["os_number"]
                    ))
    return {"inserted": new_count}


def reconcile_executed(current_os_numbers: set[str]) -> int:
    """
    Marca como 'Executado' todas as OS que estavam Pendentes
    mas NÃO aparecem mais na importação atual.
    Retorna a quantidade de OSs marcadas como executadas.
    """
    today = date.today().isoformat()
    with get_conn() as conn:
        # Busca todos os números pendentes no banco
        rows = conn.execute(
            "SELECT os_number FROM orders WHERE status='Pendente'"
        ).fetchall()
        pending_in_db = {r["os_number"] for r in rows}

        # Diferença: estavam pendentes e não constam na importação → executados
        to_mark = pending_in_db - current_os_numbers
        if to_mark:
            placeholders = ",".join("?" * len(to_mark))
            conn.execute(
                f"""UPDATE orders
                    SET status='Executado', execution_date=?
                    WHERE os_number IN ({placeholders})""",
                [today, *to_mark],
            )
        return len(to_mark)


def get_orders(
    status: Optional[str] = None,
    category: Optional[str] = None,
    team_id: Optional[int] = None,
    search: Optional[str] = None,
    scheduled_date: Optional[str] = None,
) -> list[dict]:
    sql = """
        SELECT o.*, t.name as team_name, t.type as team_type, t.task_type as team_task_type
        FROM orders o
        LEFT JOIN teams t ON o.team_id = t.id
        WHERE 1=1
    """
    params = []
    
    if status == "pendentes":
        sql += " AND o.status='Pendente' AND o.is_postergada=0"
    elif status == "executadas":
        sql += " AND o.status='Executado'"
    elif status == "postergadas":
        sql += " AND o.status='Pendente' AND o.is_postergada=1"
    elif status and status != "todas":
        # Fallback para consultas antigas, caso hajam
        sql += " AND o.status=?"
        params.append(status)
    if category and category != "Todos":
        sql += " AND o.category=?"
        params.append(category)
    if team_id is not None:
        sql += " AND o.team_id=?"
        params.append(team_id)
    if search:
        sql += " AND (o.os_number LIKE ? OR o.neighborhood LIKE ? OR o.service_description LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    if scheduled_date is not None:
        if team_id is not None:
            # Filtra pela data apenas se houver uma equipe, 
            # as OSs não atribuídas (Sem Equipe) a gente lista todas
            sql += " AND o.scheduled_date=?"
            params.append(scheduled_date)
            
    sql += " ORDER BY o.team_id, o.execution_order, o.os_number"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def assign_order_to_team(os_number: str, team_id: Optional[int], scheduled_date: Optional[str] = None):
    """Atribui (ou desatribui) uma OS a uma equipe."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE orders SET team_id=?, scheduled_date=?, execution_order=NULL WHERE os_number=?",
            (team_id, scheduled_date, os_number),
        )

def reset_past_routes(date_str: str) -> int:
    """Remove a atribuição de equipes para OSs pendentes agendadas ANTES da data informada."""
    with get_conn() as conn:
        cursor = conn.execute(
            "UPDATE orders SET team_id=NULL, scheduled_date=NULL, execution_order=NULL WHERE scheduled_date<? AND status='Pendente'",
            (date_str,)
        )
        return cursor.rowcount


def set_execution_orders(team_id: int, os_list: list[str]):
    """Define a ordem de execução de OSs de uma equipe (lista ordenada de os_number)."""
    with get_conn() as conn:
        for idx, os_number in enumerate(os_list, start=1):
            conn.execute(
                "UPDATE orders SET execution_order=? WHERE os_number=? AND team_id=?",
                (idx, os_number, team_id),
            )


def get_stats() -> dict:
    today = date.today().isoformat()
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM orders WHERE is_postergada=0").fetchone()[0]
        pendente = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Pendente' AND is_postergada=0").fetchone()[0]
        executado = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Executado'").fetchone()[0]
        executado_hoje = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Executado' AND execution_date=?", (today,)).fetchone()[0]
        postergada = conn.execute("SELECT COUNT(*) FROM orders WHERE is_postergada=1").fetchone()[0]
        calcada = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Pendente' AND category='Calçada' AND is_postergada=0").fetchone()[0]
        asfalto = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Pendente' AND category='Asfalto' AND is_postergada=0").fetchone()[0]
        sem_equipe = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Pendente' AND team_id IS NULL AND is_postergada=0").fetchone()[0]
        return {
            "total": total,
            "pendente": pendente,
            "executado": executado,
            "executado_hoje": executado_hoje,
            "postergadas": postergada,
            "calcada_pendente": calcada,
            "asfalto_pendente": asfalto,
            "sem_equipe": sem_equipe,
        }

def get_team_execution_stats() -> list[dict]:
    """Retorna a quantidade de OS executadas (Geral e Hoje) por equipe."""
    today = date.today().isoformat()
    sql = """
        SELECT 
            t.name as team_name,
            COUNT(o.os_number) as total_executadas,
            SUM(CASE WHEN o.execution_date = ? THEN 1 ELSE 0 END) as executadas_hoje
        FROM teams t
        LEFT JOIN orders o ON t.id = o.team_id AND o.status = 'Executado'
        GROUP BY t.id
        HAVING total_executadas > 0 OR executadas_hoje > 0
        ORDER BY executadas_hoje DESC, total_executadas DESC
    """
    with get_conn() as conn:
        rows = conn.execute(sql, (today,)).fetchall()
        return [dict(r) for r in rows]

def get_chart_stats() -> list[dict]:
    """Retorna dados agregados por data de importação para o gráfico (ignora postergadas)."""
    sql = """
        SELECT 
            import_date as date,
            COUNT(os_number) as total,
            SUM(CASE WHEN category = 'Calçada' THEN 1 ELSE 0 END) as calcada,
            SUM(CASE WHEN category = 'Asfalto' THEN 1 ELSE 0 END) as asfalto
        FROM orders
        WHERE is_postergada=0
        GROUP BY import_date
        ORDER BY import_date ASC
        LIMIT 30
    """
    with get_conn() as conn:
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# EQUIPES
# ─────────────────────────────────────────────────────────────────────────────

def get_teams() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT t.*, 
                   COUNT(o.os_number) as os_count,
                   SUM(CASE WHEN o.execution_order IS NOT NULL THEN 1 ELSE 0 END) as routed_count
            FROM teams t
            LEFT JOIN orders o ON t.id = o.team_id AND o.status='Pendente'
            GROUP BY t.id
            ORDER BY t.type, t.name
        """).fetchall()
        return [dict(r) for r in rows]


def create_team(name: str, type_: str, task_type: str = 'Execução') -> dict:
    with get_conn() as conn:
        cursor = conn.execute("INSERT INTO teams(name, type, task_type) VALUES(?, ?, ?)", (name, type_, task_type))
        return {"id": cursor.lastrowid, "name": name, "type": type_, "task_type": task_type}


def update_team(team_id: int, name: str, type_: str, task_type: str = 'Execução'):
    with get_conn() as conn:
        conn.execute("UPDATE teams SET name=?, type=?, task_type=? WHERE id=?", (name, type_, task_type, team_id))


def delete_team(team_id: int):
    with get_conn() as conn:
        # Desatribui OS antes de remover a equipe
        conn.execute("UPDATE orders SET team_id=NULL, execution_order=NULL WHERE team_id=?", (team_id,))
        conn.execute("DELETE FROM teams WHERE id=?", (team_id,))


# ─────────────────────────────────────────────────────────────────────────────
# CACHE DE GEOCODIFICAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def get_cached_address(address: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT lat, lon, source FROM cache_addresses WHERE address=?", (address,)
        ).fetchone()
        return dict(row) if row else None


def save_cached_address(address: str, lat: float, lon: float, source: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO cache_addresses(address, lat, lon, source, cached_at)
               VALUES(?, ?, ?, ?, ?)""",
            (address, lat, lon, source, datetime.now().isoformat()),
        )

def clear_cache():
    with get_conn() as conn:
        conn.execute("DELETE FROM cache_addresses")

def get_settings() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}

def get_setting(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        if row:
            return row["value"]
        return default

def save_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

def update_os_state(os_number: str, state: str):
    """Atualiza o estado virtual da OS."""
    with get_conn() as conn:
        today = date.today().isoformat()
        if state == 'pendentes':
            conn.execute("UPDATE orders SET status='Pendente', is_postergada=0 WHERE os_number=?", (os_number,))
        elif state == 'executadas':
            conn.execute("UPDATE orders SET status='Executado', is_postergada=0, execution_date=? WHERE os_number=?", (today, os_number))
        elif state == 'postergadas':
            conn.execute("UPDATE orders SET status='Pendente', is_postergada=1 WHERE os_number=?", (os_number,))


def set_force_task_type(os_number: str, task_type: str | None):
    """Define manualmente a função (Prévia/Execução) de uma OS, ou None para auto-detectar."""
    with get_conn() as conn:
        conn.execute("UPDATE orders SET force_task_type=? WHERE os_number=?", (task_type, os_number))


def set_os_category(os_number: str, category: str):
    """Altera a categoria (Calçada/Asfalto) de uma OS."""
    with get_conn() as conn:
        conn.execute("UPDATE orders SET category=? WHERE os_number=?", (category, os_number))


def lookup_os_numbers(os_numbers: list[str]) -> dict:
    """
    Busca informações detalhadas de uma lista de números de OS.
    Retorna um dicionário onde a chave é o os_number e o valor é um dict
    com status, team_name, scheduled_date, is_postergada, postergo_reason.
    Se a OS não existir no banco, ela não aparece no dicionário.
    """
    if not os_numbers:
        return {}

    with get_conn() as conn:
        placeholders = ",".join("?" * len(os_numbers))
        rows = conn.execute(f"""
            SELECT o.os_number, o.status, o.is_postergada, o.postergo_reason,
                   o.team_id, o.scheduled_date,
                   t.name as team_name
            FROM orders o
            LEFT JOIN teams t ON o.team_id = t.id
            WHERE o.os_number IN ({placeholders})
        """, list(os_numbers)).fetchall()

        return {r["os_number"]: dict(r) for r in rows}
