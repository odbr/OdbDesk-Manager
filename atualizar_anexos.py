import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS anexos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chamado_id INTEGER NOT NULL,
    comentario_id INTEGER,
    nome_arquivo TEXT NOT NULL,
    data_anexo DATETIME,
    FOREIGN KEY(chamado_id) REFERENCES chamados(id),
    FOREIGN KEY(comentario_id) REFERENCES comentarios(id)
)
""")

conn.commit()
conn.close()

print("Tabela anexos criada com sucesso!")