# database.py
import sqlite3
from werkzeug.security import generate_password_hash
import os

# Garante que o diretório 'instance' exista
if not os.path.exists('instance'):
    os.makedirs('instance')

# Conecta ao banco de dados (será criado em 'instance/curso.db')
connection = sqlite3.connect('instance/curso.db')
cursor = connection.cursor()

print("Configurando el banco de datos...")

# --- Criar tabelas ---

# Tabela de Usuários (com roles: 'estudiante' ou 'profesor')
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK(rol IN ('estudiante', 'profesor'))
)
''')

# Tabela de Anúncios
cursor.execute('''
CREATE TABLE IF NOT EXISTS anuncios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    contenido TEXT NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Tabela de Materiais de Aula
cursor.execute('''
CREATE TABLE IF NOT EXISTS materiales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    nombre_archivo TEXT NOT NULL,
    ruta_archivo TEXT NOT NULL
)
''')

# Tabela de Entregas (trabalhos dos alunos)
cursor.execute('''
CREATE TABLE IF NOT EXISTS entregas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_estudiante INTEGER NOT NULL,
    id_material INTEGER, -- Opcional, se a entrega for para um material específico
    titulo_entrega TEXT NOT NULL,
    nombre_archivo TEXT NOT NULL,
    ruta_archivo TEXT NOT NULL,
    fecha_entrega TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_estudiante) REFERENCES usuarios(id)
)
''')

print("Tablas creadas con éxito.")

# --- Inserir usuários de exemplo ---

try:
    # Professor
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (?, ?, ?, ?)",
        ('Profesor Admin', 'profesor@email.com', generate_password_hash('admin123'), 'profesor')
    )
    print("Usuario 'profesor' creado.")

    # Aluno
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (?, ?, ?, ?)",
        ('Alumno Ejemplo', 'alumno@email.com', generate_password_hash('alumno123'), 'estudiante')
    )
    print("Usuario 'alumno' creado.")

except sqlite3.IntegrityError:
    print("Los usuarios de ejemplo ya existen en el banco de datos.")


# Salvar alterações e fechar conexão
connection.commit()
connection.close()

print("¡Configuración del banco de datos completada!")