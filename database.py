# database.py
# Este script é para popular o banco de dados com dados iniciais.
# Rode apenas uma vez ou quando quiser resetar o banco de dados.

from app import app, db, Usuarios # Importa o app, o db e o modelo
from werkzeug.security import generate_password_hash
import os

def create_database():
    # Apaga o arquivo de banco de dados SQLite se ele existir
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    db_file = os.path.join(instance_path, 'curso.db')
    if os.path.exists(db_file):
        os.remove(db_file)
        print("Banco de datos SQLite anterior eliminado.")

    # O 'with app.app_context()' garante que a aplicação Flask entenda o contexto
    with app.app_context():
        print("Creando todas las tablas...")
        db.create_all() # Cria as tabelas com base nos modelos

        # --- Inserir usuários de exemplo ---
        print("Insertando usuarios de ejemplo...")

        # Verifica se os usuários já existem para não dar erro
        if not Usuarios.query.filter_by(email='profesor@email.com').first():
            profesor = Usuarios(
                nombre='Profesor Admin',
                email='profesor@email.com',
                password_hash=generate_password_hash('admin123', method='pbkdf2:sha256'),
                rol='profesor'
            )
            db.session.add(profesor)
            print("Usuario 'profesor' creado.")

        if not Usuarios.query.filter_by(email='alumno@email.com').first():
            alumno = Usuarios(
                nombre='Alumno Ejemplo',
                email='alumno@email.com',
                password_hash=generate_password_hash('alumno123', method='pbkdf2:sha256'),
                rol='estudiante'
            )
            db.session.add(alumno)
            print("Usuario 'alumno' creado.")

        db.session.commit() # Salva todas as inserções no banco

        print("\n¡Configuración del banco de datos completada!")

if __name__ == '__main__':
    create_database()