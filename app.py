from flask import Flask, render_template, request, redirect, session, jsonify, send_from_directory
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import pandas as pd
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'chave_secreta_do_sistema'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
GRAFICOS_FOLDER = os.path.join(BASE_DIR, 'static', 'graficos')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def criar_pastas():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(GRAFICOS_FOLDER, exist_ok=True)


def conectar_banco():
    return sqlite3.connect(os.path.join(BASE_DIR, 'database.db'))


def data_hora_brasil():
    return (datetime.utcnow() - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')


def salvar_arquivo(arquivo):
    if not arquivo or arquivo.filename == '':
        return ''

    nome_seguro = secure_filename(arquivo.filename)
    nome_final = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{nome_seguro}"

    caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], nome_final)
    arquivo.save(caminho_arquivo)

    return nome_final


def criar_banco():
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            prioridade TEXT NOT NULL,
            status TEXT NOT NULL,
            data_abertura DATETIME,
            usuario_id INTEGER,
            imagem TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)

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


def gerar_grafico_prioridade():
    conn = conectar_banco()

    df = pd.read_sql_query("""
        SELECT prioridade
        FROM chamados
    """, conn)

    conn.close()

    caminho_grafico = os.path.join(GRAFICOS_FOLDER, 'prioridade.png')

    plt.figure(figsize=(6, 4))

    if len(df) > 0:
        df['prioridade'].value_counts().plot(kind='bar')
        plt.title('Chamados por Prioridade')
        plt.xlabel('Prioridade')
        plt.ylabel('Quantidade')
    else:
        plt.text(
            0.5,
            0.5,
            'Nenhum chamado cadastrado',
            horizontalalignment='center',
            verticalalignment='center'
        )
        plt.axis('off')

    plt.tight_layout()
    plt.savefig(caminho_grafico)
    plt.close()


@app.route('/')
def home():
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_usuarios = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM chamados")
    total_chamados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM chamados WHERE status = 'ABERTO'")
    chamados_abertos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM chamados WHERE status = 'CONCLUIDO'")
    chamados_concluidos = cursor.fetchone()[0]

    conn.close()

    gerar_grafico_prioridade()

    return render_template(
        'dashboard.html',
        nome=session['usuario_nome'],
        total_usuarios=total_usuarios,
        total_chamados=total_chamados,
        chamados_abertos=chamados_abertos,
        chamados_concluidos=chamados_concluidos
    )


@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')


@app.route('/salvar_usuario', methods=['POST'])
def salvar_usuario():
    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']

    conn = conectar_banco()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO usuarios
            (nome, email, senha, perfil)
            VALUES (?, ?, ?, ?)
        """, (nome, email, senha, 'USUARIO'))

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        return 'Este e-mail já está cadastrado.'

    conn.close()

    return redirect('/login')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/autenticar', methods=['POST'])
def autenticar():
    email = request.form['email']
    senha = request.form['senha']

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, email, perfil
        FROM usuarios
        WHERE email = ? AND senha = ?
    """, (email, senha))

    usuario = cursor.fetchone()
    conn.close()

    if usuario:
        session['usuario_id'] = usuario[0]
        session['usuario_nome'] = usuario[1]
        session['usuario_email'] = usuario[2]
        session['usuario_perfil'] = usuario[3]
        return redirect('/')

    return 'Email ou senha inválidos.'


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/novo-chamado')
def novo_chamado():
    if 'usuario_id' not in session:
        return redirect('/login')

    return render_template('novo_chamado.html')


@app.route('/salvar_chamado', methods=['POST'])
def salvar_chamado():
    if 'usuario_id' not in session:
        return redirect('/login')

    titulo = request.form['titulo']
    descricao = request.form['descricao']
    prioridade = request.form['prioridade']
    usuario_id = session['usuario_id']

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chamados
        (
            titulo,
            descricao,
            prioridade,
            status,
            data_abertura,
            usuario_id,
            imagem
        )
        VALUES
        (?, ?, ?, ?, ?, ?, ?)
    """, (
        titulo,
        descricao,
        prioridade,
        'ABERTO',
        data_hora_brasil(),
        usuario_id,
        ''
    ))

    chamado_id = cursor.lastrowid

    arquivos = request.files.getlist('anexos')

    total_anexos = 0

    for arquivo in arquivos:
        nome_arquivo = salvar_arquivo(arquivo)

        if nome_arquivo:
            total_anexos += 1

            cursor.execute("""
                INSERT INTO anexos
                (chamado_id, comentario_id, nome_arquivo, data_anexo)
                VALUES (?, ?, ?, ?)
            """, (
                chamado_id,
                None,
                nome_arquivo,
                data_hora_brasil()
            ))

    cursor.execute("""
        INSERT INTO timeline
        (chamado_id, usuario_id, acao, data_acao)
        VALUES (?, ?, ?, ?)
    """, (
        chamado_id,
        usuario_id,
        'Chamado criado',
        data_hora_brasil()
    ))

    if total_anexos > 0:
        cursor.execute("""
            INSERT INTO timeline
            (chamado_id, usuario_id, acao, data_acao)
            VALUES (?, ?, ?, ?)
        """, (
            chamado_id,
            usuario_id,
            f'{total_anexos} anexo(s) adicionado(s) ao chamado',
            data_hora_brasil()
        ))

    conn.commit()
    conn.close()

    gerar_grafico_prioridade()

    return redirect('/')


@app.route('/chamados')
def listar_chamados():
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            titulo,
            descricao,
            prioridade,
            status,
            strftime('%d/%m/%Y %H:%M:%S', data_abertura) AS data_abertura,
            usuario_id,
            imagem
        FROM chamados
        ORDER BY id DESC
    """)

    chamados = cursor.fetchall()
    conn.close()

    return render_template(
        'chamados.html',
        chamados=chamados
    )


@app.route('/chamado/<int:id>')
def detalhe_chamado(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            titulo,
            descricao,
            prioridade,
            status,
            strftime('%d/%m/%Y %H:%M:%S', data_abertura) AS data_abertura,
            usuario_id,
            imagem
        FROM chamados
        WHERE id = ?
    """, (id,))

    chamado = cursor.fetchone()

    if chamado is None:
        conn.close()
        return redirect('/chamados')

    cursor.execute("""
        SELECT
            comentarios.id,
            comentarios.comentario,
            strftime('%d/%m/%Y %H:%M:%S', comentarios.data_comentario) AS data_comentario,
            usuarios.nome
        FROM comentarios
        INNER JOIN usuarios
            ON comentarios.usuario_id = usuarios.id
        WHERE comentarios.chamado_id = ?
        ORDER BY comentarios.id ASC
    """, (id,))

    comentarios = cursor.fetchall()

    cursor.execute("""
        SELECT
            timeline.id,
            timeline.acao,
            strftime('%d/%m/%Y %H:%M:%S', timeline.data_acao) AS data_acao,
            usuarios.nome
        FROM timeline
        LEFT JOIN usuarios
            ON timeline.usuario_id = usuarios.id
        WHERE timeline.chamado_id = ?
        ORDER BY timeline.id ASC
    """, (id,))

    timeline = cursor.fetchall()

    cursor.execute("""
        SELECT
            id,
            nome_arquivo,
            strftime('%d/%m/%Y %H:%M:%S', data_anexo) AS data_anexo,
            comentario_id
        FROM anexos
        WHERE chamado_id = ?
        ORDER BY id ASC
    """, (id,))

    anexos = cursor.fetchall()

    conn.close()

    anexos_chamado = []
    anexos_por_comentario = {}

    for anexo in anexos:
        comentario_id = anexo[3]

        if comentario_id is None:
            anexos_chamado.append(anexo)
        else:
            if comentario_id not in anexos_por_comentario:
                anexos_por_comentario[comentario_id] = []

            anexos_por_comentario[comentario_id].append(anexo)

    return render_template(
        'detalhe_chamado.html',
        chamado=chamado,
        comentarios=comentarios,
        timeline=timeline,
        anexos_chamado=anexos_chamado,
        anexos_por_comentario=anexos_por_comentario
    )


@app.route('/comentar/<int:chamado_id>', methods=['POST'])
def comentar_chamado(chamado_id):
    if 'usuario_id' not in session:
        return redirect('/login')

    comentario = request.form['comentario']

    arquivos = request.files.getlist('anexos')

    if comentario.strip() == '' and all(arquivo.filename == '' for arquivo in arquivos):
        return redirect(f'/chamado/{chamado_id}')

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO comentarios
        (chamado_id, usuario_id, comentario, data_comentario)
        VALUES (?, ?, ?, ?)
    """, (
        chamado_id,
        session['usuario_id'],
        comentario,
        data_hora_brasil()
    ))

    comentario_id = cursor.lastrowid

    total_anexos = 0

    for arquivo in arquivos:
        nome_arquivo = salvar_arquivo(arquivo)

        if nome_arquivo:
            total_anexos += 1

            cursor.execute("""
                INSERT INTO anexos
                (chamado_id, comentario_id, nome_arquivo, data_anexo)
                VALUES (?, ?, ?, ?)
            """, (
                chamado_id,
                comentario_id,
                nome_arquivo,
                data_hora_brasil()
            ))

    cursor.execute("""
        INSERT INTO timeline
        (chamado_id, usuario_id, acao, data_acao)
        VALUES (?, ?, ?, ?)
    """, (
        chamado_id,
        session['usuario_id'],
        'Novo comentário adicionado',
        data_hora_brasil()
    ))

    if total_anexos > 0:
        cursor.execute("""
            INSERT INTO timeline
            (chamado_id, usuario_id, acao, data_acao)
            VALUES (?, ?, ?, ?)
        """, (
            chamado_id,
            session['usuario_id'],
            f'{total_anexos} anexo(s) adicionado(s) ao comentário',
            data_hora_brasil()
        ))

    conn.commit()
    conn.close()

    return redirect(f'/chamado/{chamado_id}')


@app.route('/status/<int:id>/<status>')
def atualizar_status(id, status):
    if 'usuario_id' not in session:
        return redirect('/login')

    status = status.replace('_', ' ')

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE chamados
        SET status = ?
        WHERE id = ?
    """, (status, id))

    cursor.execute("""
        INSERT INTO timeline
        (chamado_id, usuario_id, acao, data_acao)
        VALUES (?, ?, ?, ?)
    """, (
        id,
        session['usuario_id'],
        f'Status alterado para {status}',
        data_hora_brasil()
    ))

    conn.commit()
    conn.close()

    gerar_grafico_prioridade()

    return redirect('/chamados')


@app.route('/uploads/<filename>')
def ver_upload(filename):
    if 'usuario_id' not in session:
        return redirect('/login')

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename
    )


@app.route('/api/chamados')
def api_chamados():
    conn = conectar_banco()
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            titulo,
            prioridade,
            status,
            strftime('%d/%m/%Y %H:%M:%S', data_abertura) AS data_abertura
        FROM chamados
    """)

    chamados = cursor.fetchall()
    conn.close()

    resultado = []

    for chamado in chamados:
        resultado.append({
            "id": chamado["id"],
            "titulo": chamado["titulo"],
            "prioridade": chamado["prioridade"],
            "status": chamado["status"],
            "data_abertura": chamado["data_abertura"]
        })

    return jsonify(resultado)


criar_pastas()
criar_banco()
gerar_grafico_prioridade()


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)