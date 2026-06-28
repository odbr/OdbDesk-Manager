import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS comentarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chamado_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    comentario TEXT NOT NULL,
    data_comentario DATETIME,
    FOREIGN KEY(chamado_id) REFERENCES chamados(id),
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chamado_id INTEGER NOT NULL,
    usuario_id INTEGER,
    acao TEXT NOT NULL,
    data_acao DATETIME,
    FOREIGN KEY(chamado_id) REFERENCES chamados(id),
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)
""")

conn.commit()
conn.close()

print("Tabelas de comentários e timeline criadas com sucesso!")