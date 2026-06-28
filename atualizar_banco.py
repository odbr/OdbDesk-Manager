import sqlite3

conn = sqlite3.connect('database.db')

cursor = conn.cursor()

try:
    cursor.execute("""
        ALTER TABLE chamados
        ADD COLUMN imagem TEXT
    """)

    print("Campo imagem criado!")

except:
    print("Campo já existe!")

conn.commit()
conn.close()