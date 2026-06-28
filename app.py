from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'chave_secreta_do_sistema'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
def home():
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
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

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO usuarios
        (nome, email, senha, perfil)
        VALUES (?, ?, ?, ?)
    """, (nome, email, senha, 'USUARIO'))

    conn.commit()
    conn.close()

    return redirect('/login')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/autenticar', methods=['POST'])
def autenticar():
    email = request.form['email']
    senha = request.form['senha']

    conn = sqlite3.connect('database.db')
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
    else:
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

    imagem = request.files.get('imagem')
    nome_imagem = ''

    if imagem and imagem.filename != '':
        nome_imagem = imagem.filename

        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        caminho_imagem = os.path.join(
            app.config['UPLOAD_FOLDER'],
            nome_imagem
        )

        imagem.save(caminho_imagem)

    conn = sqlite3.connect('database.db')
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
        (?, ?, ?, ?, datetime('now'), ?, ?)
    """, (
        titulo,
        descricao,
        prioridade,
        'ABERTO',
        usuario_id,
        nome_imagem
    ))

    conn.commit()
    conn.close()

    return redirect('/')


@app.route('/chamados')
def listar_chamados():
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM chamados
        ORDER BY id DESC
    """)

    chamados = cursor.fetchall()
    conn.close()

    return render_template(
        'chamados.html',
        chamados=chamados
    )


@app.route('/status/<int:id>/<status>')
def atualizar_status(id, status):
    if 'usuario_id' not in session:
        return redirect('/login')

    status = status.replace('_', ' ')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE chamados
        SET status = ?
        WHERE id = ?
    """, (status, id))

    conn.commit()
    conn.close()

    return redirect('/chamados')

@app.route('/api/chamados')
def api_chamados():

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            titulo,
            prioridade,
            status,
            data_abertura
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

if __name__ == '__main__':
    app.run(debug=True)