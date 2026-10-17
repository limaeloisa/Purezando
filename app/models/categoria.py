from app import db


class Categoria(db.Model):
    __tablename__ = "categoria"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=False)

    perguntas = db.relationship("Pergunta", back_populates="categoria")