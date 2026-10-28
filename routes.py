from datetime import timedelta, timezone
from functools import wraps

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from werkzeug.security import check_password_hash, generate_password_hash

from app import app, db
from app.models.categoria import Categoria
from app.models.pergunta import Pergunta
from app.models.resultado_quiz import ResultadoQuiz
from app.models.usuario import Usuario

DIFICULDADES_QUIZ = [
    ("muito_facil", "Muito fácil", 100),
    ("facil", "Fácil", 200),
    ("media", "Média", 300),
    ("dificil", "Difícil", 400),
    ("muito_dificil", "Muito difícil", 500),
    ("desafio", "Desafio", 600),
    ("especial", "Especial", 700),
    ("avancado", "Avançado", 800),
    ("especialista", "Especialista", 900),
    ("mestre", "Mestre", 1000),
    ("lendario", "Lendário", 1100),
    ("supremo", "Supremo", 1200)
]
DIFICULDADE_PONTOS = {
    chave: pontos
    for chave, _, pontos in DIFICULDADES_QUIZ
}
FUSO_HORARIO_BRASILIA = timezone(timedelta(hours=-3))


def formatar_data_historico(data):
    if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)
    return data.astimezone(FUSO_HORARIO_BRASILIA).strftime("%d/%m/%Y %H:%M")


def perfil_requerido(perfil):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("usuario_id"):
                destino = "admin_login" if perfil == "admin" else "login"
                return redirect(url_for(destino, next=request.path))

            try:
                usuario_atual = db.session.get(Usuario, session["usuario_id"])
            except SQLAlchemyError:
                app.logger.exception("Erro ao validar sessão do usuário")
                abort(503)

            if usuario_atual is None:
                session.clear()
                return redirect(url_for("login"))

            perfil_atual = usuario_atual.tipo_usuario.lower()
            session["tipo_usuario"] = perfil_atual
            session["nome_usuario"] = usuario_atual.nome_usuario
            if perfil_atual != perfil:
                destino = "admin" if perfil_atual == "admin" else "categorias"
                return redirect(url_for(destino))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def autenticar(perfil):
    erro = None
    if request.method == "POST":
        nome_usuario = request.form.get("nome_usuario", "").strip()
        senha = request.form.get("senha", "")

        try:
            usuario = Usuario.query.filter_by(nome_usuario=nome_usuario).first()
        except SQLAlchemyError:
            app.logger.exception("Erro ao consultar usuário no banco")
            usuario = None
            erro = "Não foi possível acessar o banco de dados."

        if erro is None:
            tipo_usuario = (
                (usuario.tipo_usuario or "").strip().lower()
                if usuario else ""
            )
            senha_valida = False
            if usuario is not None and usuario.senha:
                try:
                    senha_valida = check_password_hash(usuario.senha, senha)
                except (TypeError, ValueError):
                    app.logger.warning(
                        "Hash de senha inválido durante autenticação (%s)",
                        perfil
                    )

            if (
                usuario is None
                or not senha_valida
                or tipo_usuario != perfil
            ):
                app.logger.warning(
                    "Autenticacao %s rejeitada: usuario_encontrado=%s, "
                    "tipo_usuario=%s, senha_valida=%s",
                    perfil,
                    usuario is not None,
                    tipo_usuario or "(vazio)",
                    senha_valida
                )

            if not usuario or not senha_valida:
                erro = "Usuário ou senha inválidos."
            elif tipo_usuario != perfil:
                erro = "Esta conta não tem acesso a esta área."
            else:
                session.clear()
                session["usuario_id"] = usuario.id
                session["nome_usuario"] = usuario.nome_usuario
                session["tipo_usuario"] = tipo_usuario

                proxima_pagina = request.form.get("next", "")
                if proxima_pagina.startswith("/") and not proxima_pagina.startswith("//"):
                    return redirect(proxima_pagina)
                destino = "admin" if tipo_usuario == "admin" else "categorias"
                return redirect(url_for(destino))

    return render_template(
        "public/login.html",
        admin_mode=perfil == "admin",
        erro=erro,
        next=request.args.get("next", "")
    )


@app.route("/")
def inicio():
    return render_template("public/index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    return autenticar("jogador")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    return autenticar("admin")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("inicio"))


@app.route("/sobre")
def sobre():
    return render_template("public/sobre.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        nome_usuario = request.form.get("nome_usuario", "").strip()
        senha = request.form.get("senha", "")

        if not nome or not nome_usuario or len(senha) < 8:
            return render_template(
                "public/cadastro.html",
                erro="Preencha todos os campos. A senha deve ter pelo menos 8 caracteres."
            )

        try:
            usuario_existente = Usuario.query.filter_by(
                nome_usuario=nome_usuario
            ).first()
            if usuario_existente:
                return render_template(
                    "public/cadastro.html",
                    erro="Esse nome de usuário já está em uso."
                )

            novo_usuario = Usuario(
                nome=nome,
                nome_usuario=nome_usuario,
                senha=generate_password_hash(senha),
                tipo_usuario="jogador"
            )
            db.session.add(novo_usuario)
            db.session.commit()
            return redirect(url_for("login"))
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Erro ao cadastrar usuário")
            return render_template(
                "public/cadastro.html",
                erro="Não foi possível salvar o cadastro. Verifique a conexão com o banco."
            )

    return render_template("public/cadastro.html")


@app.route("/categorias")
@perfil_requerido("jogador")
def categorias():
    try:
        categorias_disponiveis = (
            Categoria.query
            .options(selectinload(Categoria.perguntas))
            .order_by(Categoria.nome.asc())
            .all()
        )
    except SQLAlchemyError:
        app.logger.exception("Erro ao carregar categorias")
        flash(
            "Não foi possível conectar ao banco ou ele precisa de atualização. "
            "Verifique DB_HOST/DB_PORT no config.env e rode "
            "`python -m flask --app app init-db`.",
            "error"
        )
        return render_template(
            "public/categorias.html",
            categorias=[]
        ), 503
    return render_template("public/categorias.html", categorias=categorias_disponiveis)


@app.route("/quiz", methods=["GET", "POST"])
@perfil_requerido("jogador")
def quiz():
    categoria_id = request.values.get("categoria", "")
    try:
        if categoria_id.isdigit():
            categoria = db.session.get(Categoria, int(categoria_id))
        else:
            nomes_legados = {
                "historia": "História",
                "cultura": "Cultura",
                "geografia": "Geografia"
            }
            categoria_nome = nomes_legados.get(categoria_id.lower(), "Geografia")
            categoria = Categoria.query.filter_by(nome=categoria_nome).first()
            if categoria is None:
                categoria = Categoria.query.order_by(Categoria.nome.asc()).first()
        if categoria is None:
            flash("Cadastre uma categoria antes de iniciar o quiz.", "error")
            return redirect(url_for("categorias"))

        perguntas_db = (
            Pergunta.query
            .filter_by(categoria_id=categoria.id)
            .order_by(Pergunta.id.asc())
            .all()
        )
    except SQLAlchemyError:
        app.logger.exception("Erro ao carregar perguntas")
        flash("Não foi possível carregar as perguntas.", "error")
        return redirect(url_for("categorias"))

    if not perguntas_db:
        flash("Esta categoria ainda não possui perguntas.", "error")
        return redirect(url_for("categorias"))

    perguntas = [
        {
            "texto": pergunta.enunciado,
            "opcoes": pergunta.opcoes,
            "correta": "ABCD".index(pergunta.resposta_correta),
            "resposta_correta": pergunta.opcoes[
                "ABCD".index(pergunta.resposta_correta)
            ],
            "pontos": pergunta.pontos
        }
        for pergunta in perguntas_db
    ]

    if request.method == "POST":
        respostas = [
            request.form.get(f"resposta_{indice}")
            for indice in range(len(perguntas))
        ]
        if any(resposta is None for resposta in respostas):
            erro = "Responda todas as perguntas antes de finalizar."
            return render_template(
                "public/quiz.html",
                categoria=categoria.id,
                nome_categoria=categoria.nome,
                perguntas=perguntas,
                erro=erro
            )

        acertos = sum(
            resposta.isdigit() and int(resposta) == pergunta["correta"]
            for resposta, pergunta in zip(respostas, perguntas)
        )
        pontuacao = sum(
            pergunta["pontos"]
            for resposta, pergunta in zip(respostas, perguntas)
            if resposta.isdigit() and int(resposta) == pergunta["correta"]
        )
        pontuacao_maxima = sum(pergunta["pontos"] for pergunta in perguntas)
        persistido = True
        try:
            resultado = ResultadoQuiz(
                usuario_id=session["usuario_id"],
                categoria=categoria.nome,
                pontuacao=pontuacao,
                pontuacao_maxima=pontuacao_maxima,
                acertos=acertos,
                total_perguntas=len(perguntas)
            )
            db.session.add(resultado)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Erro ao salvar resultado do quiz")
            persistido = False

        session["resultado_quiz"] = {
            "categoria": categoria.nome,
            "categoria_id": categoria.id,
            "pontuacao": pontuacao,
            "pontuacao_maxima": pontuacao_maxima,
            "acertos": acertos,
            "total": len(perguntas),
            "persistido": persistido
        }
        return redirect(url_for("ranking", categoria=categoria.id))

    return render_template(
        "public/quiz.html",
        categoria=categoria.id,
        nome_categoria=categoria.nome,
        perguntas=perguntas,
        erro=None
    )


@app.route("/resultado")
@perfil_requerido("jogador")
def resultado():
    resultado_atual = session.get("resultado_quiz")
    if not resultado_atual:
        return redirect(url_for("categorias"))
    return render_template("public/resultado.html", resultado=resultado_atual)


@app.route("/admin")
@perfil_requerido("admin")
def admin():
    try:
        usuarios = Usuario.query.order_by(Usuario.nome_usuario.asc()).all()
        categorias_disponiveis = Categoria.query.order_by(Categoria.nome.asc()).all()
        perguntas_disponiveis = Pergunta.query.order_by(Pergunta.id.desc()).all()
        total_partidas = ResultadoQuiz.query.count()
        dialeto_banco = db.engine.dialect.name
        nome_banco = db.engine.url.database
        tipo_banco = {
            "mysql": "MySQL",
            "sqlite": "SQLite"
        }.get(dialeto_banco, dialeto_banco.upper())
        banco_ativo = f"{tipo_banco} · {nome_banco if dialeto_banco == 'mysql' else 'local'}"
        erro = None
    except SQLAlchemyError:
        app.logger.exception("Erro ao carregar usuários para o painel admin")
        usuarios = []
        categorias_disponiveis = []
        perguntas_disponiveis = []
        total_partidas = 0
        banco_ativo = None
        erro = (
            "Não foi possível conectar ao banco ou ele precisa de atualização. "
            "Verifique DB_HOST/DB_PORT no config.env e rode "
            "`python -m flask --app app init-db`."
        )
        status_code = 503
    else:
        status_code = 200
    return render_template(
        "private/admin.html",
        usuarios=usuarios,
        categorias=categorias_disponiveis,
        perguntas=perguntas_disponiveis,
        niveis_dificuldade=DIFICULDADES_QUIZ,
        total_partidas=total_partidas,
        banco_ativo=banco_ativo,
        erro=erro
    ), status_code


@app.post("/admin/usuarios/<int:usuario_id>/perfil")
@perfil_requerido("admin")
def alterar_perfil_usuario(usuario_id):
    if usuario_id == session.get("usuario_id"):
        abort(400)

    perfil = request.form.get("tipo_usuario")
    if perfil not in {"admin", "jogador"}:
        abort(400)

    try:
        usuario = db.session.get(Usuario, usuario_id)
        if usuario is None:
            abort(404)
        if (
            usuario.tipo_usuario == "admin"
            and perfil == "jogador"
            and Usuario.query.filter_by(tipo_usuario="admin").count() <= 1
        ):
            flash("O sistema precisa manter pelo menos um administrador.", "error")
            return redirect(url_for("admin"))
        usuario.tipo_usuario = perfil
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro ao alterar perfil do usuário")
        abort(503)

    return redirect(url_for("admin"))


@app.post("/admin/usuarios")
@perfil_requerido("admin")
def criar_usuario_admin():
    nome = request.form.get("nome", "").strip()
    nome_usuario = request.form.get("nome_usuario", "").strip()
    senha = request.form.get("senha", "")
    tipo_usuario = request.form.get("tipo_usuario", "jogador")

    if not nome or not nome_usuario or len(senha) < 8:
        flash("Preencha nome, usuário e senha com pelo menos 8 caracteres.", "error")
        return redirect(url_for("admin"))
    if tipo_usuario not in {"admin", "jogador"}:
        abort(400)

    try:
        if Usuario.query.filter_by(nome_usuario=nome_usuario).first():
            flash("Esse nome de usuário já está em uso.", "error")
            return redirect(url_for("admin"))
        db.session.add(Usuario(
            nome=nome,
            nome_usuario=nome_usuario,
            senha=generate_password_hash(senha),
            tipo_usuario=tipo_usuario
        ))
        db.session.commit()
        flash("Usuário criado.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro ao criar usuário pelo painel")
        flash("Não foi possível criar o usuário.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/usuarios/<int:usuario_id>/editar")
@perfil_requerido("admin")
def editar_usuario_admin(usuario_id):
    try:
        usuario = db.session.get(Usuario, usuario_id)
        if usuario is None:
            abort(404)

        nome = request.form.get("nome", "").strip()
        nome_usuario = request.form.get("nome_usuario", "").strip()
        senha = request.form.get("senha", "")
        tipo_usuario = request.form.get("tipo_usuario", usuario.tipo_usuario)

        if not nome or not nome_usuario:
            flash("Nome e nome de usuário são obrigatórios.", "error")
            return redirect(url_for("admin"))
        if senha and len(senha) < 8:
            flash("A nova senha deve ter pelo menos 8 caracteres.", "error")
            return redirect(url_for("admin"))
        if usuario.id == session.get("usuario_id"):
            tipo_usuario = "admin"
        if tipo_usuario not in {"admin", "jogador"}:
            abort(400)
        duplicado = Usuario.query.filter(
            Usuario.nome_usuario == nome_usuario,
            Usuario.id != usuario.id
        ).first()
        if duplicado:
            flash("Esse nome de usuário já está em uso.", "error")
            return redirect(url_for("admin"))
        if (
            usuario.tipo_usuario == "admin"
            and tipo_usuario == "jogador"
            and Usuario.query.filter_by(tipo_usuario="admin").count() <= 1
        ):
            flash("O sistema precisa manter pelo menos um administrador.", "error")
            return redirect(url_for("admin"))

        usuario.nome = nome
        usuario.nome_usuario = nome_usuario
        usuario.tipo_usuario = tipo_usuario
        if senha:
            usuario.senha = generate_password_hash(senha)
        if usuario.id == session.get("usuario_id"):
            session["nome_usuario"] = nome_usuario
        db.session.commit()
        flash("Usuário atualizado.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro ao atualizar usuário pelo painel")
        flash("Não foi possível atualizar o usuário.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/usuarios/<int:usuario_id>/excluir")
@perfil_requerido("admin")
def excluir_usuario_admin(usuario_id):
    try:
        usuario = db.session.get(Usuario, usuario_id)
        if usuario is None:
            abort(404)
        if usuario.id == session.get("usuario_id"):
            flash("Não é possível excluir a própria conta ativa.", "error")
            return redirect(url_for("admin"))
        if (
            usuario.tipo_usuario == "admin"
            and Usuario.query.filter_by(tipo_usuario="admin").count() <= 1
        ):
            flash("O sistema precisa manter pelo menos um administrador.", "error")
            return redirect(url_for("admin"))
        ResultadoQuiz.query.filter_by(usuario_id=usuario.id).delete(
            synchronize_session=False
        )
        db.session.delete(usuario)
        db.session.commit()
        flash("Usuário excluído.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro ao excluir usuário pelo painel")
        flash("Não foi possível excluir o usuário.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/categorias")
@perfil_requerido("admin")
def criar_categoria():
    nome = request.form.get("nome", "").strip()
    descricao = request.form.get("descricao", "").strip()
    if not nome or not descricao:
        flash("Nome e descrição da categoria são obrigatórios.", "error")
        return redirect(url_for("admin"))

    try:
        if Categoria.query.filter_by(nome=nome).first():
            flash("Já existe uma categoria com esse nome.", "error")
            return redirect(url_for("admin"))
        db.session.add(Categoria(nome=nome, descricao=descricao))
        db.session.commit()
        flash("Categoria criada.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro ao criar categoria")
        flash("Não foi possível criar a categoria.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/categorias/<int:categoria_id>/editar")
@perfil_requerido("admin")
def editar_categoria(categoria_id):
    try:
        categoria = db.session.get(Categoria, categoria_id)
        if categoria is None:
            abort(404)
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        if not nome or not descricao:
            flash("Nome e descrição da categoria são obrigatórios.", "error")
            return redirect(url_for("admin"))
        duplicada = Categoria.query.filter(
            Categoria.nome == nome,
            Categoria.id != categoria.id
        ).first()
        if duplicada:
            flash("Já existe uma categoria com esse nome.", "error")
            return redirect(url_for("admin"))
        categoria.nome = nome
        categoria.descricao = descricao
        db.session.commit()
        flash("Categoria atualizada.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro ao atualizar categoria")
        flash("Não foi possível atualizar a categoria.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/categorias/<int:categoria_id>/excluir")
@perfil_requerido("admin")
def excluir_categoria(categoria_id):
    try:
        categoria = db.session.get(Categoria, categoria_id)
        if categoria is None:
            abort(404)
        if categoria.perguntas:
            flash("Exclua ou mova as perguntas antes de remover a categoria.", "error")
            return redirect(url_for("admin"))
        db.session.delete(categoria)
        db.session.commit()
        flash("Categoria excluída.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro ao excluir categoria")
        flash("Não foi possível excluir a categoria.", "error")
    return redirect(url_for("admin"))


def ler_pergunta_form():
    enunciado = request.form.get("enunciado", "").strip()
    categoria_id = request.form.get("categoria_id", "")
    opcoes = [
        request.form.get("opcao_a", "").strip(),
        request.form.get("opcao_b", "").strip(),
        request.form.get("opcao_c", "").strip(),
        request.form.get("opcao_d", "").strip()
    ]
    correta = request.form.get("resposta_correta", "").upper()
    dificuldade = request.form.get("dificuldade", "")
    if not enunciado or not all(opcoes):
        raise ValueError("Preencha o enunciado e as quatro alternativas.")
    if not categoria_id.isdigit() or correta not in {"A", "B", "C", "D"}:
        raise ValueError("Selecione uma categoria e a alternativa correta.")
    if dificuldade not in DIFICULDADE_PONTOS:
        raise ValueError("Selecione uma dificuldade válida.")
    categoria = db.session.get(Categoria, int(categoria_id))
    if categoria is None:
        raise ValueError("A categoria selecionada não existe.")
    return (
        enunciado,
        categoria,
        opcoes,
        correta,
        dificuldade,
        DIFICULDADE_PONTOS[dificuldade]
    )


@app.post("/admin/perguntas")
@perfil_requerido("admin")
def criar_pergunta():
    try:
        enunciado, categoria, opcoes, correta, dificuldade, pontos = ler_pergunta_form()
        db.session.add(Pergunta(
            enunciado=enunciado,
            categoria_id=categoria.id,
            opcao_a=opcoes[0],
            opcao_b=opcoes[1],
            opcao_c=opcoes[2],
            opcao_d=opcoes[3],
            resposta_correta=correta,
            pontos=pontos,
            dificuldade=dificuldade
        ))
        db.session.commit()
        flash("Pergunta criada.", "success")
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "error")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro ao criar pergunta")
        flash("Não foi possível criar a pergunta.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/perguntas/<int:pergunta_id>/editar")
@perfil_requerido("admin")
def editar_pergunta(pergunta_id):
    try:
        pergunta = db.session.get(Pergunta, pergunta_id)
        if pergunta is None:
            abort(404)
        enunciado, categoria, opcoes, correta, dificuldade, pontos = ler_pergunta_form()
        pergunta.enunciado = enunciado
        pergunta.categoria_id = categoria.id
        pergunta.opcao_a = opcoes[0]
        pergunta.opcao_b = opcoes[1]
        pergunta.opcao_c = opcoes[2]
        pergunta.opcao_d = opcoes[3]
        pergunta.resposta_correta = correta
        pergunta.pontos = pontos
        pergunta.dificuldade = dificuldade
        db.session.commit()
        flash("Pergunta atualizada.", "success")
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "error")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro ao atualizar pergunta")
        flash("Não foi possível atualizar a pergunta.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/perguntas/<int:pergunta_id>/excluir")
@perfil_requerido("admin")
def excluir_pergunta(pergunta_id):
    try:
        pergunta = db.session.get(Pergunta, pergunta_id)
        if pergunta is None:
            abort(404)
        db.session.delete(pergunta)
        db.session.commit()
        flash("Pergunta excluída.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro ao excluir pergunta")
        flash("Não foi possível excluir a pergunta.", "error")
    return redirect(url_for("admin"))


@app.route("/ranking")
@perfil_requerido("jogador")
def ranking():
    categoria_id = request.args.get("categoria", type=int)
    categorias = []
    categoria_selecionada = None
    resultado_recente = session.get("resultado_quiz")
    if (
        not resultado_recente
        or categoria_id is None
        or resultado_recente.get("categoria_id") != categoria_id
    ):
        resultado_recente = None

    try:
        categorias = Categoria.query.order_by(Categoria.nome.asc()).all()
        consulta = (
            ResultadoQuiz.query
            .join(Usuario)
            .filter(ResultadoQuiz.total_perguntas > 0)
        )
        if categoria_id is not None:
            categoria_selecionada = db.session.get(Categoria, categoria_id)
            if categoria_selecionada is None:
                abort(404)
            consulta = consulta.filter(
                ResultadoQuiz.categoria == categoria_selecionada.nome
            )
        aproveitamento = (
            ResultadoQuiz.pontuacao * 1.0 / ResultadoQuiz.pontuacao_maxima
        )
        resultados = (
            consulta
            .filter(ResultadoQuiz.pontuacao_maxima > 0)
            .order_by(
                aproveitamento.desc(),
                ResultadoQuiz.pontuacao.desc(),
                ResultadoQuiz.criado_em.asc()
            )
            .limit(10)
            .all()
        )
        erro = None
    except SQLAlchemyError:
        app.logger.exception("Erro ao carregar ranking")
        resultados = []
        erro = "O ranking estará disponível quando o banco estiver conectado."
    return render_template(
        "public/ranking.html",
        resultados=resultados,
        categorias=categorias,
        categoria_selecionada=categoria_selecionada,
        resultado_recente=resultado_recente,
        erro=erro
    )


@app.route("/historico")
@perfil_requerido("jogador")
def historico():
    try:
        partidas = (
            ResultadoQuiz.query
            .filter_by(usuario_id=session["usuario_id"])
            .order_by(ResultadoQuiz.criado_em.desc())
            .limit(50)
            .all()
        )
        erro = None
    except SQLAlchemyError:
        app.logger.exception("Erro ao carregar histórico de partidas")
        partidas = []
        erro = "Não foi possível carregar seu histórico."
    return render_template(
        "public/historico.html",
        partidas=partidas,
        erro=erro,
        formatar_data=formatar_data_historico
    )
