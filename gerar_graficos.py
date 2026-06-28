import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

conn = sqlite3.connect('database.db')

df = pd.read_sql_query("""
SELECT prioridade
FROM chamados
""", conn)

conn.close()

if len(df) > 0:

    grafico = df['prioridade'].value_counts()

    plt.figure(figsize=(6,4))
    grafico.plot(kind='bar')

    plt.title('Chamados por Prioridade')
    plt.xlabel('Prioridade')
    plt.ylabel('Quantidade')

    plt.tight_layout()

    plt.savefig('static/graficos/prioridade.png')

    print("Gráfico criado!")
else:
    print("Não existem chamados cadastrados.")