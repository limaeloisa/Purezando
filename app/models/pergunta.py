from app import db


class Pergunta(db.Model):
    __tablename__ = "perguntas"

    id = db.Column("idperguntas", db.Integer, primary_key=True, autoincrement=True)
    enunciado = db.Column(db.Text, nullable=False)
    categoria_id = db.Column(
        db.Integer,
        db.ForeignKey("categoria.idcategoria"),
        nullable=False
    )
    opcao_a = db.Column("alternativa_A", db.String(255), nullable=False)
    opcao_b = db.Column("alternativa_B", db.String(255), nullable=False)
    opcao_c = db.Column("alternativa_C", db.String(255), nullable=False)
    opcao_d = db.Column("alternativa_D", db.String(255), nullable=False)
    resposta_correta = db.Column(db.String(1), nullable=False)

    categoria = db.relationship("Categoria", back_populates="perguntas")

    @property
    def opcoes(self):
        return [self.opcao_a, self.opcao_b, self.opcao_c, self.opcao_d]