# PUREZANDO

Quiz educativo sobre Pureza/RN, com áreas de jogador e administrador.

## Organização

```text
app/
	forms/                 formulários compartilhados
	models/                modelos SQLAlchemy compartilhados
	templates/
		public/              telas de jogador e páginas públicas
		private/             dashboard e telas administrativas
	static/
		public/              CSS, JS e imagens públicas
		private/             CSS e JS do dashboard
routes.py                rotas públicas e administrativas
```

A pasta `private` organiza os arquivos administrativos; a proteção efetiva é feita
pelos controles de perfil nas rotas Flask. Não coloque senhas ou outros segredos em
arquivos estáticos.

## Executar localmente

1. Instale as dependências: `pip install -r requirements.txt`.
2. Para usar SQLite local, adicione ao `config.env`:

	```env
	DB_DRIVER=sqlite
	DB_PATH=instance/purezando.sqlite3
	SECRET_KEY=gere-uma-chave-segura
	```

3. Crie as tabelas: `python -m flask --app app init-db`.
4. Inicie o servidor: `python app.py` e abra `http://127.0.0.1:5000`.

O comando `init-db` cria as tabelas e inclui três categorias com perguntas de
exemplo na primeira inicialização. No painel `/admin`, é possível criar, editar
e excluir usuários, categorias e perguntas. A senha é armazenada com hash.

Cada pergunta tem enunciado, categoria, quatro alternativas e a alternativa
correta, necessários para o quiz calcular e salvar a pontuação.

Para MySQL, configure `DB_DRIVER=mysql` e as variáveis `DB_USER`, `DB_PASSWORD`,
`DB_HOST`, `DB_PORT` e `DB_NAME` no `config.env`. O banco indicado por `DB_NAME`
precisa existir antes de executar `init-db`; o comando cria as tabelas da aplicação.
Se o servidor exigir um certificado CA, informe seu caminho em `DB_SSL_CA`.

## Primeiro administrador

O cadastro público sempre cria uma conta de jogador. Para promover uma conta
existente usando o ORM SQLAlchemy:

```powershell
python -m flask --app app promover-admin seu_usuario
```

Entre em `/admin/login`. A partir do painel, administradores podem alterar o perfil
das outras contas, editar nomes de usuário e redefinir senhas. Jogadores e
administradores têm rotas e navegação separadas.

## Usuários de teste

- Administrador: usuário `admin`, provisionado no banco Aiven. A senha inicial é
	temporária e deve ser compartilhada fora do repositório; altere-a após o primeiro
	login em `/admin/login`.
- Jogador: cadastre uma conta de teste em `/cadastro` e use a senha escolhida no
	formulário para validar login, quiz, resultado e histórico.
- Para testar localmente sem afetar o Aiven, configure SQLite conforme a seção de
	execução e crie os usuários de teste pelo próprio cadastro.

Não versione `config.env`, senhas ou hashes. O arquivo está coberto pelo `.gitignore`.