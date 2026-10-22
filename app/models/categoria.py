from app import db


class Categoria(db.Model):
    __tablename__ = "categoria"

    id = db.Column("idcategoria", db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(90), nullable=False)
    descricao = db.Column(db.String(255), nullable=False)

    perguntas = db.relationship("Pergunta", back_populates="categoria")