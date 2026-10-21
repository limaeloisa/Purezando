import os
from pathlib import Path

import click
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / "config.env")

app = Flask(
	__name__,
	template_folder="templates",
	static_folder="static"
)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or os.urandom(32)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

mysql_settings = ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME")
default_database_driver = (
	"mysql" if any(os.getenv(setting) for setting in mysql_settings) else "sqlite"
)
database_driver = (os.getenv("DB_DRIVER") or default_database_driver).lower()
if database_driver == "sqlite":
	database_path = os.getenv(
		"DB_PATH",
		str(PROJECT_ROOT / "instance" / "purezando.sqlite3")
	)
	if database_path != ":memory:":
		database_file = Path(database_path)
		if not database_file.is_absolute():
			database_file = PROJECT_ROOT / database_file
		database_file = database_file.resolve()
		database_file.parent.mkdir(parents=True, exist_ok=True)
		database_path = str(database_file)
	url_banco = URL.create("sqlite", database=database_path)
	app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
		"connect_args": {"check_same_thread": False}
	}
elif database_driver == "mysql":
	url_banco = URL.create(
		drivername="mysql+pymysql",
		username=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
		host=os.getenv("DB_HOST"),
		port=int(os.getenv("DB_PORT", "3306")),
		database=os.getenv("DB_NAME")
	)

	ssl_options = {"check_hostname": True}
	ssl_ca = os.getenv("DB_SSL_CA")
	if ssl_ca:
		ssl_options["ca"] = ssl_ca

	app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
		"connect_args": {"ssl": ssl_options}
	}
else:
	raise ValueError("DB_DRIVER deve ser 'mysql' ou 'sqlite'.")

app.config["SQLALCHEMY_DATABASE_URI"] = url_banco

db = SQLAlchemy(app)

import routes


@app.cli.command("init-db")
def initialize_database():
	from app.models.categoria import Categoria
	from app.models.pergunta import Pergunta

	db.create_all()
	conteudo_inicial = [
		(
			"História",
			"Memórias, origens e acontecimentos de Pureza/RN.",
			[
				("O que uma fonte histórica pode revelar?", ["A previsão do tempo de amanhã", "Como as pessoas viviam em outra época", "A velocidade da internet", "A distância até a Lua"], "B"),
				("Qual destes itens pode ser uma fonte histórica?", ["Uma senha de Wi-Fi", "Um documento antigo", "Um sinal de trânsito novo", "Uma previsão do tempo"], "B"),
				("Como a memória de uma comunidade pode ser preservada?", ["Somente mapas de outros países", "Apenas notícias sobre esportes", "Relatos de moradores e registros locais", "Somente fotografias sem contexto"], "C")
			]
		),
		(
			"Cultura",
			"Tradições, costumes e expressões culturais locais.",
			[
				("Qual opção representa uma expressão cultural?", ["A senha de uma conta", "A velocidade de um automóvel", "Festas, músicas e tradições", "A previsão de chuva"], "C"),
				("A cultura de uma comunidade é formada por...", ["Somente prédios novos", "Costumes, saberes e modos de vida", "Apenas regras de trânsito", "Somente produtos importados"], "B"),
				("Uma tradição pode ser transmitida...", ["Somente por máquinas", "Apenas por placas de trânsito", "Sem participação das pessoas", "Entre diferentes gerações"], "D")
			]
		),
		(
			"Geografia",
			"Localização, território e características de Pureza/RN.",
			[
				("Pureza fica em qual estado brasileiro?", ["Paraíba", "Ceará", "Rio Grande do Norte", "Pernambuco"], "C"),
				("Em qual região do Brasil está o Rio Grande do Norte?", ["Norte", "Nordeste", "Centro-Oeste", "Sul"], "B"),
				("Qual é a capital do Rio Grande do Norte?", ["Mossoró", "Parnamirim", "Caicó", "Natal"], "D")
			]
		)
	]
	for nome, descricao, questoes in conteudo_inicial:
		categoria = Categoria.query.filter_by(nome=nome).first()
		if categoria is None:
			categoria = Categoria(nome=nome, descricao=descricao)
			db.session.add(categoria)
			db.session.flush()
		if not categoria.perguntas:
			for enunciado, opcoes, correta in questoes:
				db.session.add(Pergunta(
					enunciado=enunciado,
					categoria_id=categoria.id,
					opcao_a=opcoes[0],
					opcao_b=opcoes[1],
					opcao_c=opcoes[2],
					opcao_d=opcoes[3],
					resposta_correta=correta
				))
	db.session.commit()
	print("Tabelas criadas ou atualizadas.")


@app.cli.command("promover-admin")
@click.argument("nome_usuario")
def promover_admin(nome_usuario):
	from app.models.usuario import Usuario

	usuario = Usuario.query.filter_by(nome_usuario=nome_usuario).first()
	if usuario is None:
		raise click.ClickException("Usuário não encontrado.")

	usuario.tipo_usuario = "admin"
	db.session.commit()
	print(f"{nome_usuario} agora tem perfil de administrador.")
