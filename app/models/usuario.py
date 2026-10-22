
from app import db


class Usuario(db.Model):
    __tablename__ = "usuario"

    id = db.Column(
        "id_usuario",
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    nome = db.Column(
        db.String(100),
        nullable=False
    )

    nome_usuario = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    senha = db.Column(
        db.String(255),
        nullable=False
    )

    tipo_usuario = db.Column(
        db.String(20),
        nullable=False,
        default="jogador"
    )

    data_cadastro = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.now()
    )
