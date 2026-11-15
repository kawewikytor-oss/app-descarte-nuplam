import psycopg2
import psycopg2.extras
import pandas as pd
import streamlit as st

def get_connection():
    url = st.secrets["DB_URL"]
    return psycopg2.connect(url)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Tabela Coletas
    c.execute('''
        CREATE TABLE IF NOT EXISTS coletas (
            id SERIAL PRIMARY KEY,
            data_coleta TEXT,
            nome_medicamento TEXT,
            forma_farmaceutica TEXT,
            validade TEXT,
            situacao_validade TEXT
        )
    ''')
    # Tabela Classificacoes
    c.execute('''
        CREATE TABLE IF NOT EXISTS classificacoes (
            nome_medicamento TEXT PRIMARY KEY,
            classe_atc TEXT,
            mecanismo_acao TEXT,
            classe_estrutural TEXT,
            mecanismo_antiresistencia TEXT
        )
    ''')
    # Tabela Formas Farmaceuticas
    c.execute('''
        CREATE TABLE IF NOT EXISTS formas (
            nome_forma TEXT PRIMARY KEY,
            estado_fisico TEXT
        )
    ''')
    # Tabela Pesagens
    c.execute('''
        CREATE TABLE IF NOT EXISTS pesagens (
            mes_ano TEXT PRIMARY KEY,
            peso_liquidos REAL,
            peso_solidos REAL
        )
    ''')

    # Inserir formas iniciais se vazio
    c.execute("SELECT COUNT(*) FROM formas")
    if c.fetchone()[0] == 0:
        formas_iniciais = [
            ("Comprimido", "Sólido"),
            ("Cápsula", "Sólido"),
            ("Suspensão oral", "Líquido"),
            ("Solução", "Líquido"),
            ("Pomada", "Semissólido"),
            ("Pó para suspensão", "Sólido")
        ]
        c.executemany("INSERT INTO formas (nome_forma, estado_fisico) VALUES (%s, %s)", formas_iniciais)

    conn.commit()
    conn.close()

def get_all_nomes():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT nome_medicamento FROM coletas ORDER BY nome_medicamento")
    nomes = [row[0] for row in c.fetchall()]
    conn.close()
    return nomes

def get_all_formas():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT nome_forma FROM formas ORDER BY nome_forma")
    formas = [row[0] for row in c.fetchall()]
    conn.close()
    return formas

def add_forma(nome, estado):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO formas (nome_forma, estado_fisico) VALUES (%s, %s) ON CONFLICT DO NOTHING", (nome, estado))
    conn.commit()
    conn.close()

def insert_coleta(data_coleta, nome, forma, validade, situacao):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO coletas (data_coleta, nome_medicamento, forma_farmaceutica, validade, situacao_validade)
        VALUES (%s, %s, %s, %s, %s)
    ''', (data_coleta.strftime("%Y-%m-%d"), nome, forma, validade, situacao))
    conn.commit()
    conn.close()

def get_classificacoes():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM classificacoes")
    rows = c.fetchall()
    conn.close()
    return {row[0]: {"atc": row[1], "mec_acao": row[2], "classe_est": row[3], "mec_antires": row[4]} for row in rows}

def upsert_classificacao(nome, atc, mec_acao, classe_est, mec_antires):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO classificacoes (nome_medicamento, classe_atc, mecanismo_acao, classe_estrutural, mecanismo_antiresistencia)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (nome_medicamento) DO UPDATE SET
            classe_atc=EXCLUDED.classe_atc,
            mecanismo_acao=EXCLUDED.mecanismo_acao,
            classe_estrutural=EXCLUDED.classe_estrutural,
            mecanismo_antiresistencia=EXCLUDED.mecanismo_antiresistencia
    ''', (nome, atc, mec_acao, classe_est, mec_antires))
    conn.commit()
    conn.close()

def get_pesagens():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM pesagens")
    rows = c.fetchall()
    conn.close()
    return {row[0]: {"liquidos": row[1], "solidos": row[2]} for row in rows}

def upsert_pesagem(mes_ano, liquidos, solidos):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO pesagens (mes_ano, peso_liquidos, peso_solidos)
        VALUES (%s, %s, %s)
        ON CONFLICT (mes_ano) DO UPDATE SET
            peso_liquidos=EXCLUDED.peso_liquidos,
            peso_solidos=EXCLUDED.peso_solidos
    ''', (mes_ano, liquidos, solidos))
    conn.commit()
    conn.close()

def get_df_exportacao():
    conn = get_connection()
    query = '''
        SELECT
            c.id as "ID",
            COALESCE(cl.classe_atc, '') as "Classe ATC",
            c.data_coleta as "Data da Coleta",
            c.nome_medicamento as "Nome do Medicamento",
            c.validade as "Ano Validade",
            c.situacao_validade as "Situação Validade",
            c.forma_farmaceutica as "Forma Farmacêutica",
            COALESCE(cl.mecanismo_acao, '') as "Mecanismo de Ação",
            COALESCE(cl.classe_estrutural, '') as "Classe Estrutural",
            COALESCE(cl.mecanismo_antiresistencia, '-') as "Mecanismo Antiresistência"
        FROM coletas c
        LEFT JOIN classificacoes cl ON c.nome_medicamento = cl.nome_medicamento
        ORDER BY c.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_df_completo():
    conn = get_connection()
    query = '''
        SELECT
            c.*,
            COALESCE(cl.classe_atc, '') as classe_atc,
            COALESCE(cl.mecanismo_acao, '') as mecanismo_acao,
            COALESCE(cl.classe_estrutural, '') as classe_estrutural,
            f.estado_fisico
        FROM coletas c
        LEFT JOIN classificacoes cl ON c.nome_medicamento = cl.nome_medicamento
        LEFT JOIN formas f ON c.forma_farmaceutica = f.nome_forma
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def clear_all_coletas():
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM coletas")
    conn.commit()
    conn.close()
