import os
from app import app
from flask import render_template, request, redirect, url_for
from dotenv import load_dotenv
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv("config.env")

conexao = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)
cursor = conexao.cursor()
print("Conectado com sucesso ao banco da Aiven!")


@app.route("/")
def inicio():
    return render_template("index.html")

print("Conectado com sucesso ao banco da Aiven!")
@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

from datetime import datetime 

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        try:
            local_cursor = conexao.cursor()

            # 1. Gambiarra necessária para contornar a falta do AUTO_INCREMENT no ID
            local_cursor.execute("SELECT COALESCE(MAX(id_usuario), 0) + 1 FROM usuario")
            proximo_id = local_cursor.fetchone()[0]

            # 2. Pega a data e hora exata do momento atual para o cadastro
            data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

            # 3. Mapeia todas as colunas obrigatórias exigidas pelo seu script SQL
            sql = """
                INSERT INTO usuario (id_usuario, nome, email, senha_hash, tipo, data_cadastro) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            valores = (proximo_id, nome, email, generate_password_hash(senha), 'comum', data_atual)
            
            # 4. Executa e grava as alterações na Aiven
            local_cursor.execute(sql, valores)
            conexao.commit()
            local_cursor.close()
            
            print(f"Usuário {nome} cadastrado com sucesso com o ID {proximo_id}!")
            return redirect(url_for('login'))
            
        except mysql.connector.Error as erro:
            print(f"Erro ao salvar no banco: {erro}")

    return render_template('cadastro.html')



@app.route("/categorias")
def categorias():
    return render_template("categorias.html")

@app.route("/ranking")
def ranking():
    return render_template("ranking.html")