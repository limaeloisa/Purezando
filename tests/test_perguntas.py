import os
import unittest

os.environ["DB_DRIVER"] = "sqlite"
os.environ["DB_PATH"] = ":memory:"

from app import app, db
from app.models.categoria import Categoria
from app.models.pergunta import Pergunta
from app.models.resultado_quiz import ResultadoQuiz
from app.models.usuario import Usuario
from app.routes import ler_pergunta_form, pergunta_duplicada


class PerguntaTests(unittest.TestCase):
    def setUp(self):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app_context = app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

        self.categoria = Categoria(nome="História", descricao="História local")
        self.outra_categoria = Categoria(nome="Cultura", descricao="Cultura local")
        db.session.add_all([self.categoria, self.outra_categoria])
        db.session.flush()
        self.pergunta = Pergunta(
            enunciado="Qual é a capital?",
            categoria_id=self.categoria.id,
            opcao_a="A",
            opcao_b="B",
            opcao_c="C",
            opcao_d="D",
            resposta_correta="A"
        )
        db.session.add(self.pergunta)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.app_context.pop()

    def test_detects_duplicate_question_in_same_category(self):
        self.assertTrue(pergunta_duplicada(
            "  QUAL   É A CAPITAL? ",
            self.categoria.id
        ))

    def test_allows_same_question_in_another_category(self):
        self.assertFalse(pergunta_duplicada(
            self.pergunta.enunciado,
            self.outra_categoria.id
        ))

    def test_ignores_current_question_when_editing(self):
        self.assertFalse(pergunta_duplicada(
            self.pergunta.enunciado,
            self.categoria.id,
            pergunta_id_excluida=self.pergunta.id
        ))

    def test_form_rejects_duplicate_in_selected_category(self):
        dados = {
            "enunciado": self.pergunta.enunciado,
            "categoria_id": str(self.categoria.id),
            "opcao_a": "A",
            "opcao_b": "B",
            "opcao_c": "C",
            "opcao_d": "D",
            "resposta_correta": "A",
            "dificuldade": "muito_facil"
        }
        with app.test_request_context("/admin/perguntas", method="POST", data=dados):
            with self.assertRaisesRegex(ValueError, "Já existe uma pergunta"):
                ler_pergunta_form()

    def test_admin_lists_questions_under_their_category(self):
        outra_pergunta = Pergunta(
            enunciado="Quando é a festa?",
            categoria_id=self.outra_categoria.id,
            opcao_a="A",
            opcao_b="B",
            opcao_c="C",
            opcao_d="D",
            resposta_correta="A"
        )
        admin = Usuario(
            nome="Admin",
            nome_usuario="admin-teste",
            senha="hash",
            tipo_usuario="admin"
        )
        db.session.add_all([outra_pergunta, admin])
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sessao:
            sessao["usuario_id"] = admin.id
        response = client.get("/admin")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Testar quiz", html)
        perguntas_html = html.split(
            '<section class="admin-section" id="perguntas"',
            1
        )[1]
        cultura = perguntas_html.index(
            f'id="perguntas-categoria-{self.outra_categoria.id}"'
        )
        pergunta_cultura = perguntas_html.index(outra_pergunta.enunciado)
        historia = perguntas_html.index(
            f'id="perguntas-categoria-{self.categoria.id}"'
        )
        pergunta_historia = perguntas_html.index(self.pergunta.enunciado)
        self.assertLess(cultura, pergunta_cultura)
        self.assertLess(pergunta_cultura, historia)
        self.assertLess(historia, pergunta_historia)

    def test_admin_can_test_quiz_without_saving_result(self):
        admin = Usuario(
            nome="Admin",
            nome_usuario="admin-teste",
            senha="hash",
            tipo_usuario="admin"
        )
        db.session.add(admin)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sessao:
            sessao["usuario_id"] = admin.id

        categorias_response = client.get("/categorias")
        self.assertEqual(categorias_response.status_code, 200)
        self.assertIn(b"Testar quiz", categorias_response.data)

        quiz_response = client.post("/quiz", data={
            "categoria": str(self.categoria.id),
            "resposta_0": "0"
        })
        self.assertEqual(quiz_response.status_code, 302)
        self.assertEqual(quiz_response.headers["Location"], "/resultado")

        resultado_response = client.get("/resultado")
        self.assertEqual(resultado_response.status_code, 200)
        self.assertIn(b"Modo de teste", resultado_response.data)
        self.assertEqual(db.session.query(ResultadoQuiz).count(), 0)

    def test_player_quiz_still_saves_result(self):
        jogador = Usuario(
            nome="Jogador",
            nome_usuario="jogador-teste",
            senha="hash",
            tipo_usuario="jogador"
        )
        db.session.add(jogador)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sessao:
            sessao["usuario_id"] = jogador.id

        response = client.post("/quiz", data={
            "categoria": str(self.categoria.id),
            "resposta_0": "0"
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/ranking?categoria="))
        self.assertEqual(db.session.query(ResultadoQuiz).count(), 1)


if __name__ == "__main__":
    unittest.main()
