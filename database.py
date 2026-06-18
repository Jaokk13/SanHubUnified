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
                service_description TEXT,
                limit_date          TEXT,
                status              TEXT DEFAULT 'Pendente',
                category            TEXT DEFAULT 'Indefinido',
                team_id             INTEGER,
                execution_order     INTEGER,
                import_date         TEXT,
                execution_date      TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL
            );

            -- Tabela de Equipes
            CREATE TABLE IF NOT EXISTS teams (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT UNIQUE NOT NULL,
                type    TEXT NOT NULL CHECK(type IN ('Calçada', 'Asfalto'))
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
                    (os_number, solicitation_date, neighborhood,
                     service_description, limit_date, status,
                     category, import_date)
                VALUES (?, ?, ?, ?, ?, 'Pendente', ?, ?)
            """, (
                o["os_number"],
                o.get("solicitation_date", ""),
                o.get("neighborhood", ""),
                o.get("service_description", ""),
                o.get("limit_date", ""),
                o.get("category", "Indefinido"),
                date.today().isoformat(),
            ))
            if cursor.rowcount > 0:
                new_count += 1
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
) -> list[dict]:
    """Retorna lista de OSs filtradas."""
    sql = """
        SELECT o.*, t.name as team_name, t.type as team_type
        FROM orders o
        LEFT JOIN teams t ON o.team_id = t.id
        WHERE 1=1
    """
    params = []
    if status:
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

    sql += " ORDER BY o.team_id, o.execution_order, o.os_number"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def assign_order_to_team(os_number: str, team_id: Optional[int]):
    """Atribui (ou desatribui) uma OS a uma equipe."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE orders SET team_id=?, execution_order=NULL WHERE os_number=?",
            (team_id, os_number),
        )


def set_execution_orders(team_id: int, os_list: list[str]):
    """Define a ordem de execução de OSs de uma equipe (lista ordenada de os_number)."""
    with get_conn() as conn:
        for idx, os_number in enumerate(os_list, start=1):
            conn.execute(
                "UPDATE orders SET execution_order=? WHERE os_number=? AND team_id=?",
                (idx, os_number, team_id),
            )


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        pendente = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Pendente'").fetchone()[0]
        executado = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Executado'").fetchone()[0]
        calcada = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Pendente' AND category='Calçada'").fetchone()[0]
        asfalto = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Pendente' AND category='Asfalto'").fetchone()[0]
        sem_equipe = conn.execute("SELECT COUNT(*) FROM orders WHERE status='Pendente' AND team_id IS NULL").fetchone()[0]
        return {
            "total": total,
            "pendente": pendente,
            "executado": executado,
            "calcada_pendente": calcada,
            "asfalto_pendente": asfalto,
            "sem_equipe": sem_equipe,
        }


# ─────────────────────────────────────────────────────────────────────────────
# EQUIPES
# ─────────────────────────────────────────────────────────────────────────────

def get_teams() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT t.*, COUNT(o.os_number) as os_count
            FROM teams t
            LEFT JOIN orders o ON t.id = o.team_id AND o.status='Pendente'
            GROUP BY t.id
            ORDER BY t.type, t.name
        """).fetchall()
        return [dict(r) for r in rows]


def create_team(name: str, type_: str) -> dict:
    with get_conn() as conn:
        cursor = conn.execute("INSERT INTO teams(name, type) VALUES(?, ?)", (name, type_))
        return {"id": cursor.lastrowid, "name": name, "type": type_}


def update_team(team_id: int, name: str, type_: str):
    with get_conn() as conn:
        conn.execute("UPDATE teams SET name=?, type=? WHERE id=?", (name, type_, team_id))


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
