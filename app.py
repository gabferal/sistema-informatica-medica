# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

# --- Configuração da Aplicação ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-segura-e-dificil-de-adivinhar'
app.config['UPLOAD_FOLDER_MATERIALES'] = os.path.join('uploads', 'materiales')
app.config['UPLOAD_FOLDER_ENTREGAS'] = os.path.join('uploads', 'entregas')

# Garante que as pastas de upload existam
os.makedirs(app.config['UPLOAD_FOLDER_MATERIALES'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_ENTREGAS'], exist_ok=True)

# --- Configuração do Banco de Dados (PostgreSQL + Fallback para SQLite) ---
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    # Se não estiver no Railway (ou outra plataforma com DATABASE_URL), usa um SQLite local.
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    DATABASE_URL = f'sqlite:///{os.path.join(instance_path, "curso.db")}'

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Modelos de Dados (Tabelas como Classes Python) ---
class Usuarios(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # 'estudiante' ou 'profesor'

class Anuncios(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime(timezone=True), server_default=func.now())

class Materiales(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    nombre_archivo = db.Column(db.String(200), nullable=False)
    ruta_archivo = db.Column(db.String(300), nullable=False)

class Entregas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_estudiante = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    titulo_entrega = db.Column(db.String(200), nullable=False)
    nombre_archivo = db.Column(db.String(200), nullable=False)
    ruta_archivo = db.Column(db.String(300), nullable=False)
    fecha_entrega = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    estudiante = db.relationship('Usuarios', backref=db.backref('entregas', lazy=True))

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
        
        user = Usuarios.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session['user_id'] = user.id
            session['user_nombre'] = user.nombre
            session['user_rol'] = user.rol
            
            if user.rol == 'profesor':
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
    anuncios = Anuncios.query.order_by(Anuncios.fecha_creacion.desc()).all()
    materiales = Materiales.query.order_by(Materiales.id.desc()).all()
    return render_template('dashboard_profesor.html', anuncios=anuncios, materiales=materiales)

@app.route('/publicar_anuncio', methods=['POST'])
@login_required
@role_required('profesor')
def publicar_anuncio():
    titulo = request.form['titulo']
    contenido = request.form['contenido']
    
    nuevo_anuncio = Anuncios(titulo=titulo, contenido=contenido)
    db.session.add(nuevo_anuncio)
    db.session.commit()
    
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

        nuevo_material = Materiales(titulo=titulo, descripcion=descripcion, nombre_archivo=filename, ruta_archivo=filepath)
        db.session.add(nuevo_material)
        db.session.commit()
        
        flash("Material subido con éxito.", "success")
    else:
        flash("Debe seleccionar un archivo.", "warning")

    return redirect(url_for('dashboard_profesor'))

@app.route('/ver_entregas_profesor')
@login_required
@role_required('profesor')
def ver_entregas_profesor():
    entregas = Entregas.query.order_by(Entregas.fecha_entrega.desc()).all()
    return render_template('ver_entregas_profesor.html', entregas=entregas)


# --- Rotas do Estudante ---
@app.route('/dashboard_estudiante')
@login_required
@role_required('estudiante')
def dashboard_estudiante():
    anuncios = Anuncios.query.order_by(Anuncios.fecha_creacion.desc()).all()
    materiales = Materiales.query.order_by(Materiales.id.desc()).all()
    entregas = Entregas.query.filter_by(id_estudiante=session['user_id']).order_by(Entregas.fecha_entrega.desc()).all()
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
        unique_filename = f"{id_estudiante}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER_ENTREGAS'], unique_filename)
        file.save(filepath)

        nueva_entrega = Entregas(id_estudiante=id_estudiante, titulo_entrega=titulo, nombre_archivo=filename, ruta_archivo=filepath)
        db.session.add(nueva_entrega)
        db.session.commit()
        
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

    # Segurança: Apenas professores podem baixar entregas de alunos.
    # Alunos só podem baixar materiais.
    if folder == 'entregas' and session['user_rol'] != 'profesor':
        flash("No tiene permiso para descargar este archivo.", "danger")
        return redirect(url_for('dashboard_estudiante'))
        
    directory = os.path.join(os.getcwd(), 'uploads', folder)
    
    # Nome do arquivo no disco para entregas é prefixado com id do aluno.
    if folder == 'entregas':
        # Esta parte pode ser melhorada para buscar o id do aluno do DB,
        # mas por enquanto vamos assumir que o nome do arquivo já vem completo.
        # Ex: na chamada do template, o nome já é construído.
        path_to_file = filename
    else:
        path_to_file = filename

    return send_from_directory(directory=directory, path=path_to_file, as_attachment=True)

# --- Bloco de Execução ---
if __name__ == '__main__':
    with app.app_context():
        # db.create_all() não deve ser usado em produção com Gunicorn
        # Este bloco é principalmente para desenvolvimento local com `flask run`
        db.create_all() 
    app.run(debug=True)