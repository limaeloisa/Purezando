from app import db


class ResultadoQuiz(db.Model):
    __tablename__ = "resultado_quiz"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False
    )
    categoria = db.Column(db.String(40), nullable=False)
    pontuacao = db.Column(db.Integer, nullable=False)
    pontuacao_maxima = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    acertos = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    total_perguntas = db.Column(db.Integer, nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=db.func.now())

    usuario = db.relationship("Usuario", backref="resultados_quiz")