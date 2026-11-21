import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DB_PATH = Path("plano_acao.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Cria as tabelas relacionais e popula exemplos iniciais se o banco estiver vazio."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS reunioes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                notas_originais TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reuniao_id INTEGER NOT NULL,
                descricao TEXT NOT NULL,
                responsavel TEXT NOT NULL,
                prazo TEXT NOT NULL,
                prioridade TEXT NOT NULL DEFAULT 'Média',
                status TEXT NOT NULL DEFAULT 'Pendente',
                FOREIGN KEY (reuniao_id) REFERENCES reunioes(id) ON DELETE CASCADE
            );
            """
        )

        total = conn.execute("SELECT COUNT(*) FROM tarefas;").fetchone()[0]
        if total == 0:
            cursor = conn.execute(
                "INSERT INTO reunioes (titulo, notas_originais) VALUES (?, ?);",
                (
                    "Alinhamento Sprint — Plataforma Conversacional",
                    "Mariana vai revisar os fluxos do chatbot de cobrança até sexta. "
                    "Lucas precisa otimizar a query SQL do relatório de retenção até quarta (alta prioridade). "
                    "Rafael ficou de configurar o webhook da API REST em homologação até amanhã.",
                ),
            )
            reuniao_id = cursor.lastrowid
            tarefas_iniciais = [
                (reuniao_id, "Configurar webhook da API REST em homologação", "Rafael", "Amanhã", "Alta", "Em Andamento"),
                (reuniao_id, "Otimizar query SQL do relatório de retenção", "Lucas", "Quarta-feira", "Alta", "Pendente"),
                (reuniao_id, "Revisar fluxos do chatbot de cobrança", "Mariana", "Sexta-feira", "Média", "Concluída"),
            ]
            conn.executemany(
                """
                INSERT INTO tarefas (reuniao_id, descricao, responsavel, prazo, prioridade, status)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                tarefas_iniciais,
            )


def salvar_reuniao_e_tarefas(titulo: str, notas: str, tarefas: List[Dict]) -> int:
    """Insere a reunião e todas as tarefas extraídas dentro de uma única transação SQL."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO reunioes (titulo, notas_originais) VALUES (?, ?);",
            (titulo.strip(), notas.strip()),
        )
        reuniao_id = cursor.lastrowid

        registros = [
            (
                reuniao_id,
                t.get("descricao", "Tarefa sem descrição"),
                t.get("responsavel", "Não definido"),
                t.get("prazo", "A definir"),
                t.get("prioridade", "Média"),
                "Pendente",
            )
            for t in tarefas
        ]
        conn.executemany(
            """
            INSERT INTO tarefas (reuniao_id, descricao, responsavel, prazo, prioridade, status)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            registros,
        )
        return reuniao_id


def listar_tarefas(
    responsavel: Optional[str] = None, status: Optional[str] = None
) -> Tuple[List[Dict], str]:
    """Consulta tarefas com JOIN na tabela de reuniões e retorna também a query SQL executada."""
    query = """
    SELECT
        t.id,
        r.titulo AS reuniao,
        t.descricao,
        t.responsavel,
        t.prazo,
        t.prioridade,
        t.status
    FROM tarefas t
    INNER JOIN reunioes r ON r.id = t.reuniao_id
    WHERE 1=1
    """
    params = []

    if responsavel and responsavel != "Todos":
        query += " AND t.responsavel = ?"
        params.append(responsavel)

    if status and status != "Todos":
        query += " AND t.status = ?"
        params.append(status)

    query += " ORDER BY t.id DESC;"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows], query.strip()


def listar_responsaveis() -> List[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT responsavel FROM tarefas ORDER BY responsavel ASC;"
        ).fetchall()
        return [row["responsavel"] for row in rows]


def obter_metricas() -> Dict[str, int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS total FROM tarefas GROUP BY status;"
        ).fetchall()
        contagem = {row["status"]: row["total"] for row in rows}
        return {
            "total": sum(contagem.values()),
            "Pendente": contagem.get("Pendente", 0),
            "Em Andamento": contagem.get("Em Andamento", 0),
            "Concluída": contagem.get("Concluída", 0),
        }


def atualizar_status_tarefa(tarefa_id: int, novo_status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE tarefas SET status = ? WHERE id = ?;",
            (novo_status, tarefa_id),
        )


def excluir_tarefa(tarefa_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM tarefas WHERE id = ?;", (tarefa_id,))
