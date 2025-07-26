# app.py
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

# --- Configuração da Aplicação ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-segura-e-dificil-de-adivinhar'
app.config['DATABASE'] = os.path.join(app.instance_path, 'curso.db')
app.config['UPLOAD_FOLDER_MATERIALES'] = os.path.join('uploads', 'materiales')
app.config['UPLOAD_FOLDER_ENTREGAS'] = os.path.join('uploads', 'entregas')

# Garante que as pastas de upload existam
os.makedirs(app.config['UPLOAD_FOLDER_MATERIALES'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_ENTREGAS'], exist_ok=True)

# --- Conexão com o Banco de Dados ---
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Decoradores de Autenticação e Autorização ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Por favor, inicie sesión para acceder a esta página.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('user_rol') != role:
                flash("No tiene permiso para acceder a esta página.", "danger")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Rotas Principais ---
@app.route('/')
def index():
    if 'user_id' in session:
        if session['user_rol'] == 'profesor':
            return redirect(url_for('dashboard_profesor'))
        else:
            return redirect(url_for('dashboard_estudiante'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['user_nombre'] = user['nombre']
            session['user_rol'] = user['rol']
            
            if user['rol'] == 'profesor':
                return redirect(url_for('dashboard_profesor'))
            else:
                return redirect(url_for('dashboard_estudiante'))
        else:
            flash("Email o contraseña incorrectos.", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Ha cerrado sesión exitosamente.", "success")
    return redirect(url_for('login'))

# --- Rotas do Professor ---
@app.route('/dashboard_profesor')
@login_required
@role_required('profesor')
def dashboard_profesor():
    db = get_db()
    anuncios = db.execute('SELECT * FROM anuncios ORDER BY fecha_creacion DESC').fetchall()
    materiales = db.execute('SELECT * FROM materiales ORDER BY id DESC').fetchall()
    return render_template('dashboard_profesor.html', anuncios=anuncios, materiales=materiales)

@app.route('/publicar_anuncio', methods=['POST'])
@login_required
@role_required('profesor')
def publicar_anuncio():
    titulo = request.form['titulo']
    contenido = request.form['contenido']
    db = get_db()
    db.execute('INSERT INTO anuncios (titulo, contenido) VALUES (?, ?)', (titulo, contenido))
    db.commit()
    flash("Anuncio publicado con éxito.", "success")
    return redirect(url_for('dashboard_profesor'))

@app.route('/subir_material', methods=['POST'])
@login_required
@role_required('profesor')
def subir_material():
    titulo = request.form['titulo']
    descripcion = request.form['descripcion']
    file = request.files['archivo']

    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER_MATERIALES'], filename)
        file.save(filepath)

        db = get_db()
        db.execute('INSERT INTO materiales (titulo, descripcion, nombre_archivo, ruta_archivo) VALUES (?, ?, ?, ?)',
                   (titulo, descripcion, filename, filepath))
        db.commit()
        flash("Material subido con éxito.", "success")
    else:
        flash("Debe seleccionar un archivo.", "warning")

    return redirect(url_for('dashboard_profesor'))

@app.route('/ver_entregas_profesor')
@login_required
@role_required('profesor')
def ver_entregas_profesor():
    db = get_db()
    entregas = db.execute('''
        SELECT e.titulo_entrega, e.nombre_archivo, e.fecha_entrega, u.nombre as nombre_estudiante
        FROM entregas e
        JOIN usuarios u ON e.id_estudiante = u.id
        ORDER BY e.fecha_entrega DESC
    ''').fetchall()
    return render_template('ver_entregas_profesor.html', entregas=entregas)


# --- Rotas do Estudante ---
@app.route('/dashboard_estudiante')
@login_required
@role_required('estudiante')
def dashboard_estudiante():
    db = get_db()
    anuncios = db.execute('SELECT * FROM anuncios ORDER BY fecha_creacion DESC').fetchall()
    materiales = db.execute('SELECT * FROM materiales ORDER BY id DESC').fetchall()
    entregas = db.execute('SELECT * FROM entregas WHERE id_estudiante = ? ORDER BY fecha_entrega DESC', 
                          (session['user_id'],)).fetchall()
    return render_template('dashboard_estudiante.html', anuncios=anuncios, materiales=materiales, entregas=entregas)

@app.route('/subir_entrega', methods=['POST'])
@login_required
@role_required('estudiante')
def subir_entrega():
    titulo = request.form['titulo']
    file = request.files['archivo']
    id_estudiante = session['user_id']

    if file and file.filename != '':
        filename = secure_filename(file.filename)
        # Adicionar id do estudante ao nome do arquivo para evitar conflitos
        unique_filename = f"{id_estudiante}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER_ENTREGAS'], unique_filename)
        file.save(filepath)

        db = get_db()
        db.execute('INSERT INTO entregas (id_estudiante, titulo_entrega, nombre_archivo, ruta_archivo) VALUES (?, ?, ?, ?)',
                   (id_estudiante, titulo, filename, filepath))
        db.commit()
        flash("Trabajo práctico enviado con éxito.", "success")
    else:
        flash("Debe seleccionar un archivo para enviar.", "warning")
        
    return redirect(url_for('dashboard_estudiante'))

# --- Rota para Download de Arquivos ---
@app.route('/download/<path:folder>/<path:filename>')
@login_required
def download_file(folder, filename):
    if folder not in ['materiales', 'entregas']:
        flash("Carpeta no válida.", "danger")
        return redirect(url_for('index'))

    # Segurança: Apenas professores podem baixar entregas
    if folder == 'entregas' and session['user_rol'] != 'profesor':
         # Permite que o próprio aluno baixe seu trabalho
        db = get_db()
        entrega = db.execute('SELECT * FROM entregas WHERE nombre_archivo = ? AND id_estudiante = ?', 
                             (filename.split('_', 1)[1], session['user_id'])).fetchone()
        if not entrega:
            flash("No tiene permiso para descargar este archivo.", "danger")
            return redirect(url_for('dashboard_estudiante'))

    directory = os.path.join(os.getcwd(), 'uploads', folder)
    return send_from_directory(directory=directory, path=filename, as_attachment=True)

# --- Execução da Aplicação ---
if __name__ == '__main__':
    app.run(debug=True) # debug=True apenas para desenvolvimento local