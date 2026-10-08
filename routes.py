from app import app
from flask import render_template, request, redirect, url_for


@app.route("/")
def inicio():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        return redirect(url_for('categorias'))

    return render_template('cadastro.html')

@app.route("/categorias")
def categorias():
    return render_template("categorias.html")

@app.route("/ranking")
def ranking():
    return render_template("ranking.html")