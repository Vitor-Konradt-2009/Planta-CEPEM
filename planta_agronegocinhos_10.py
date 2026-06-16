from flask import Flask, request, redirect, url_for, session, flash, render_template_string
from functools import wraps
import os
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")

TOPO_IMAGEM_URL = os.getenv(
    "TOPO_IMAGEM_URL",
    "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?q=80&w=1600&auto=format&fit=crop"
)
LOGO_FILENAME = "planta_logo.jpeg"
EDITAL_FILENAME = "edital_inscricao_planta.pdf"

ADMIN_SEEDS = {
    "nelise.ruscheinsky@escola.pr.gov.br": {"nome": "Nelise Ruscheinsky", "senha": "agrocepem"},
    "alexandra.martinez@escola.pr.gov.br": {"nome": "Alexandra da Silva Martinez", "senha": "agrocepem"},
    "victor.luiz.marchi@escola.pr.gov.br": {"nome": "Victor Luiz Marchi", "senha": "agrocepem"},
    "s.claudinei@escola.pr.gov.br": {"nome": "Claudinei Ferreira da Silva", "senha": "agrocepem"},
}

TURMAS_VALIDAS = ["1° Agronegócio", "2° Agronegócio", "3° Agronegócio"]

MISSAO = (
    "Desenvolver líderes capacitados, éticos e inovadores no setor do agronegócio, "
    "promovendo conhecimento técnico, responsabilidade socioambiental e habilidades "
    "de gestão para contribuir com o crescimento sustentável do campo e da sociedade."
)
VISAO = (
    "Ser um programa de referência na formação de lideranças do agronegócio, "
    "reconhecido por preparar profissionais comprometidos com a excelência, "
    "a inovação e o desenvolvimento sustentável do setor."
)
VALORES = [
    "🌱 Sustentabilidade – Produzir com responsabilidade, preservando os recursos naturais para as futuras gerações.",
    "🤝 Ética – Agir com honestidade, transparência e respeito em todas as decisões e relações.",
    "🚜 Comprometimento – Demonstrar dedicação, responsabilidade e disciplina na busca por resultados.",
    "💡 Inovação – Incentivar novas ideias, tecnologias e soluções para os desafios do agronegócio.",
    "📚 Aprendizado Contínuo – Buscar constantemente conhecimento e aperfeiçoamento profissional.",
    "👥 Trabalho em Equipe – Valorizar a colaboração, o respeito e a união para alcançar objetivos comuns.",
    "🏆 Excelência – Buscar alta qualidade em todas as atividades e processos desenvolvidos.",
    "🌎 Responsabilidade Social – Contribuir para o desenvolvimento das comunidades e para o fortalecimento do agronegócio de forma justa e inclusiva.",
]


def normalize_database_url(url: str) -> str:
    if not url:
        return ""
    p = urlparse(url.strip())
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q["sslmode"] = "require"
    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), p.fragment))


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL", ""))


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não configurada.")
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10
    )


def now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


LAYOUT_INICIO = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{ titulo }}</title>
  <style>
    * { box-sizing: border-box; font-family: Arial, sans-serif; }
    body { margin: 0; background: #f5f7f5; color: #1f2937; padding-top: 78px; }
    .bg-logo{
      position: fixed; inset: 0; z-index: 0; pointer-events: none;
      background: url('{{ url_for("static", filename=logo_filename) }}') no-repeat center center;
      background-size: min(70vw, 720px); opacity: .08;
    }

    .topbar {
      position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
      background: rgba(17, 24, 39, 0.95); backdrop-filter: blur(6px);
      border-bottom: 1px solid rgba(255,255,255,0.12); padding: 10px 14px;
    }
    .topbar-inner {
      max-width: 1180px; margin: 0 auto; display: flex; align-items: center;
      justify-content: space-between; gap: 10px; flex-wrap: wrap;
    }
    .brand { color: #fff; font-weight: 700; font-size: 15px; white-space: nowrap; }
    .left-nav, .right-info { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }

    .topo, .container { position: relative; z-index: 1; }
    .topo { height: 230px; overflow: hidden; position: relative; }
    .topo img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .overlay{
      position:absolute; inset:0; background: rgba(0,0,0,.35); color:#fff;
      display:flex; flex-direction:column; justify-content:center; padding-left:32px;
    }

    .container { max-width: 1100px; margin: 24px auto; padding: 0 16px; }
    .logo-wrap { text-align:center; margin-bottom: 16px; }
    .logo-wrap img {
      max-height: 200px; width:auto; background:#fff; border-radius:10px;
      padding: 8px; box-shadow: 0 2px 12px rgba(0,0,0,.1);
    }

    .chip {
      background:#e5e7eb; border-radius:999px; padding:6px 12px;
      font-size:12px; color:#111827; font-weight:600;
    }

    .card {
      background: rgba(255,255,255,.96); border-radius: 12px; padding: 20px;
      box-shadow: 0 2px 12px rgba(0,0,0,.08); margin-bottom: 16px;
    }

    h2, h3, h4 { margin-top: 0; }
    label { display:block; margin-top:12px; margin-bottom:6px; font-weight:bold; }
    input, select, textarea, button {
      width:100%; padding:10px; border:1px solid #d1d5db; border-radius:8px;
    }
    textarea { min-height: 120px; resize: vertical; }

    .checkbox-linha{
      display:flex; gap:10px; align-items:flex-start; margin-top:16px; padding:12px;
      border:1px solid #d1d5db; border-radius:8px; background:#f9fafb;
    }
    .checkbox-linha input[type="checkbox"]{ width:auto; margin-top:4px; }

    .btn, button{
      margin-top:12px; display:inline-block; width:auto; text-decoration:none; cursor:pointer;
      background:#166534; color:#fff; border:none; padding:10px 16px; border-radius:8px; font-size:14px;
    }
    .btn.secundario { background:#374151; }
    .btn.warning { background:#92400e; }
    .btn.danger { background:#b91c1c; }

    .alert { padding:12px; border-radius:8px; margin-bottom:14px; }
    .alert.erro { background:#fee2e2; color:#991b1b; }
    .alert.ok { background:#dcfce7; color:#166534; }

    .politica h4, .mvv h4 { margin: 14px 0 6px; color:#14532d; }
    .politica ul, .mvv ul { margin: 0 0 8px 18px; padding:0; }

    .citacao{
      margin-top:10px; padding:10px 12px; border-left:4px solid #166534;
      background:#f0fdf4; font-style:italic;
    }

    .table-wrap { overflow-x:auto; }
    table { width:100%; border-collapse: collapse; font-size:14px; }
    th, td { border-bottom:1px solid #e5e7eb; text-align:left; padding:10px 8px; vertical-align:top; }
    th { background:#f3f4f6; }

    .badge { display:inline-block; font-size:12px; font-weight:bold; border-radius:999px; padding:4px 8px; }
    .badge.pendente { background:#fef3c7; color:#92400e; }
    .badge.aceita { background:#dcfce7; color:#166534; }
    .badge.negada { background:#fee2e2; color:#991b1b; }
    .badge.espera { background:#dbeafe; color:#1e3a8a; }

    .post { border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; background: #fff; margin-bottom: 10px; }
    .post small { color: #6b7280; }
    .post p { margin: 8px 0 0; white-space: pre-wrap; }
  </style>
</head>
<body>
  <div class="bg-logo" aria-hidden="true"></div>

  <div class="topbar">
    <div class="topbar-inner">
      <div class="brand">PLANTA • Programa de Liderança</div>
      <div class="left-nav">
        {% for item in nav_items %}
          <a class="btn {{ item.cls }}" href="{{ item.href }}">{{ item.label }}</a>
        {% endfor %}
      </div>
      <div class="right-info">
        {% if session.get('admin_autenticado') %}
          <span class="chip">Admin: {{ session.get('admin_nome') }}</span>
        {% endif %}
        {% if session.get('aluno_autenticado') %}
          <span class="chip">Aluno: {{ session.get('aluno_nome') }}</span>
        {% endif %}
      </div>
    </div>
  </div>

  <header class="topo">
    <img src="{{ topo_url }}" alt="Topo PLANTA">
    <div class="overlay">
      <h1>PLANTA</h1>
      <p>Programa Liderança de Alto Nível do Técnico em Agronegócio</p>
    </div>
  </header>

  <main class="container">
    <div class="logo-wrap">
      <img src="{{ url_for('static', filename=logo_filename) }}" alt="Logo PLANTA">
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for categoria, mensagem in messages %}
          <div class="alert {{ categoria }}">{{ mensagem }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
"""

LAYOUT_FIM = """
  </main>
</body>
</html>
"""

BLOCO_MVV = """
<section class="card mvv">
  <h3>Missão, Visão e Valores</h3>
  <h4>Missão</h4><p>{{ missao }}</p>
  <h4>Visão</h4><p>{{ visao }}</p>
  <h4>Valores</h4>
  <ul>{% for v in valores %}<li>{{ v }}</li>{% endfor %}</ul>
</section>
"""


def render_pagina(conteudo_html: str, titulo: str, page: str, **ctx):
    return render_template_string(
        LAYOUT_INICIO + conteudo_html + LAYOUT_FIM,
        titulo=titulo,
        topo_url=TOPO_IMAGEM_URL,
        logo_filename=LOGO_FILENAME,
        edital_filename=EDITAL_FILENAME,
        missao=MISSAO,
        visao=VISAO,
        valores=VALORES,
        nav_items=build_nav_items(page),
        **ctx
    )


def build_nav_items(page: str):
    if session.get("admin_autenticado"):
        return [
            {"label": "Informações", "href": url_for("admin_info"), "cls": "secundario"},
            {"label": "Configurações", "href": url_for("admin_config"), "cls": "secundario"},
            {"label": "Inscritos", "href": url_for("admin_inscritos"), "cls": "warning"},
            {"label": "Postagens", "href": url_for("admin_postagens"), "cls": ""},
            {"label": "Logout", "href": url_for("admin_logout"), "cls": "danger"},
        ]
    if session.get("aluno_autenticado"):
        return [
            {"label": "Informações", "href": url_for("aluno_info"), "cls": "secundario"},
            {"label": "Configurações", "href": url_for("aluno_config"), "cls": "secundario"},
            {"label": "Mural", "href": url_for("aluno_dashboard"), "cls": ""},
            {"label": "Logout", "href": url_for("aluno_logout"), "cls": "danger"},
        ]

    items = []
    if page != "home":
        items.append({"label": "Início", "href": url_for("index"), "cls": ""})
    if page != "inscricao":
        items.append({"label": "Inscrição", "href": url_for("inscricao"), "cls": ""})
    if page != "consulta":
        items.append({"label": "Consultar inscrição", "href": url_for("consulta"), "cls": "secundario"})
    if page != "aluno_primeiro_acesso":
        items.append({"label": "Primeiro acesso", "href": url_for("aluno_primeiro_acesso"), "cls": "secundario"})
    if page != "aluno_login":
        items.append({"label": "Login Aluno", "href": url_for("aluno_login"), "cls": ""})
    if page != "admin_login":
        items.append({"label": "Login Admin", "href": url_for("admin_login"), "cls": "warning"})
    return items


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("admin_autenticado"):
            flash("Faça login como administrador.", "erro")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapped


def aluno_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("aluno_autenticado"):
            flash("Faça login como aluno.", "erro")
            return redirect(url_for("aluno_login"))
        return f(*args, **kwargs)
    return wrapped


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS inscricoes (
                    id BIGSERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    data_nascimento TEXT NOT NULL,
                    cpf TEXT NOT NULL,
                    email TEXT NOT NULL,
                    telefone TEXT NOT NULL,
                    turma TEXT NOT NULL,
                    compromisso_lider BOOLEAN NOT NULL DEFAULT FALSE,
                    status TEXT NOT NULL DEFAULT 'Pendente',
                    decidido_por TEXT,
                    data_decisao TEXT,
                    motivo_negacao TEXT,
                    posicao_espera INTEGER,
                    acesso_aluno_ativo BOOLEAN NOT NULL DEFAULT FALSE,
                    criado_em TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id BIGSERIAL PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    nome TEXT NOT NULL,
                    senha_hash TEXT NOT NULL,
                    ativo BOOLEAN NOT NULL DEFAULT TRUE,
                    criado_em TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS alunos_users (
                    id BIGSERIAL PRIMARY KEY,
                    inscricao_id BIGINT NOT NULL UNIQUE REFERENCES inscricoes(id) ON DELETE CASCADE,
                    email TEXT NOT NULL UNIQUE,
                    cpf TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    senha_hash TEXT NOT NULL,
                    ativo BOOLEAN NOT NULL DEFAULT TRUE,
                    criado_em TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS postagens (
                    id BIGSERIAL PRIMARY KEY,
                    conteudo TEXT NOT NULL,
                    autor_email TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    ativo BOOLEAN NOT NULL DEFAULT TRUE
                )
            """)

            # Migrações leves
            cur.execute("ALTER TABLE inscricoes ADD COLUMN IF NOT EXISTS posicao_espera INTEGER")
            cur.execute("ALTER TABLE inscricoes ADD COLUMN IF NOT EXISTS compromisso_lider BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("ALTER TABLE inscricoes ADD COLUMN IF NOT EXISTS acesso_aluno_ativo BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("ALTER TABLE inscricoes ADD COLUMN IF NOT EXISTS motivo_negacao TEXT")
            cur.execute("ALTER TABLE inscricoes ADD COLUMN IF NOT EXISTS decidido_por TEXT")
            cur.execute("ALTER TABLE inscricoes ADD COLUMN IF NOT EXISTS data_decisao TEXT")
            cur.execute("ALTER TABLE inscricoes ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'Pendente'")

            cur.execute("ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE")
            cur.execute("ALTER TABLE alunos_users ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE")
            cur.execute("ALTER TABLE postagens ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE")

            # Seeds admin
            for email, dados in ADMIN_SEEDS.items():
                cur.execute("""
                    INSERT INTO admin_users (email, nome, senha_hash, ativo, criado_em)
                    VALUES (%s, %s, %s, TRUE, %s)
                    ON CONFLICT (email) DO NOTHING
                """, (email.lower(), dados["nome"], generate_password_hash(dados["senha"]), now_str()))


# ========================== PÚBLICO ==========================

@app.route("/")
def index():
    conteudo = """
    <section class="card">
      <h2>Bem-vindo ao PLANTA</h2>
      <p>Inscrição de alunos sem senha. Área admin protegida por login.</p>
      <a class="btn" href="{{ url_for('inscricao') }}">Fazer inscrição</a>
      <a class="btn secundario" href="{{ url_for('consulta') }}">Consultar inscrição</a>
      <a class="btn warning" href="{{ url_for('static', filename=edital_filename) }}" target="_blank" rel="noopener">
        Abrir Edital (PDF)
      </a>
    </section>
    """ + BLOCO_MVV
    return render_pagina(conteudo, "Início - PLANTA", page="home")


@app.route("/inscricao", methods=["GET", "POST"])
def inscricao():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        data_nascimento = request.form.get("data_nascimento", "").strip()
        cpf = request.form.get("cpf", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        turma = request.form.get("turma", "").strip()
        compromisso_lider = request.form.get("compromisso_lider")

        if not all([nome, data_nascimento, cpf, email, telefone, turma]):
            flash("Preencha todos os campos.", "erro")
            return redirect(url_for("inscricao"))

        cpf_num = re.sub(r"\D", "", cpf)
        if len(cpf_num) != 11:
            flash("CPF inválido. Use 11 dígitos.", "erro")
            return redirect(url_for("inscricao"))

        if turma not in TURMAS_VALIDAS:
            flash("Turma inválida.", "erro")
            return redirect(url_for("inscricao"))

        if compromisso_lider != "on":
            flash("É obrigatório aceitar o Compromisso do Líder.", "erro")
            return redirect(url_for("inscricao"))

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO inscricoes (
                        nome, data_nascimento, cpf, email, telefone, turma, compromisso_lider,
                        status, posicao_espera, acesso_aluno_ativo, criado_em
                    ) VALUES (%s, %s, %s, %s, %s, %s, TRUE, 'Pendente', NULL, FALSE, %s)
                """, (nome, data_nascimento, cpf_num, email, telefone, turma, now_str()))

        conteudo = """
        <section class="card">
          <h2>Inscrição concluída</h2>
          <p>Obrigado, <strong>{{ nome }}</strong>. Sua inscrição foi enviada com status <span class="badge pendente">Pendente</span>.</p>
          <a class="btn" href="{{ url_for('consulta') }}">Consultar inscrição</a>
          <a class="btn secundario" href="{{ url_for('aluno_primeiro_acesso') }}">Primeiro acesso</a>
        </section>
        """ + BLOCO_MVV
        return render_pagina(conteudo, "Inscrição Enviada", page="inscricao", nome=nome)

    conteudo = """
    <section class="card">
      <h2>Formulário de Inscrição</h2>
      <form method="POST">
        <label>Nome</label>
        <input type="text" name="nome" required>

        <label>Data de nascimento</label>
        <input type="date" name="data_nascimento" required>

        <label>CPF</label>
        <input type="text" name="cpf" required>

        <label>E-mail</label>
        <input type="email" name="email" required>

        <label>Número de telefone</label>
        <input type="tel" name="telefone" required>

        <label>Turma</label>
        <select name="turma" required>
          <option value="">Selecione...</option>
          {% for t in turmas %}
            <option value="{{ t }}">{{ t }}</option>
          {% endfor %}
        </select>

        <div class="checkbox-linha">
          <input type="checkbox" id="compromisso_lider" name="compromisso_lider" required>
          <label for="compromisso_lider">
            Li e aceito o <strong>Compromisso do Líder</strong>. Esta aceitação é obrigatória para concluir a inscrição.
          </label>
        </div>

        <button type="submit">Enviar inscrição</button>
      </form>
    </section>

    <section class="card politica">
      <h3>Código de Ética e Conduta</h3>
      <p><strong>Programa de Liderança de Alto Nível – Técnico em Agronegócio</strong></p>

      <h4>1. Respeito e Profissionalismo</h4>
      <ul>
        <li>Tratar todos os participantes, professores, colaboradores e parceiros com respeito e educação.</li>
        <li>Valorizar a diversidade de opiniões, culturas e experiências.</li>
        <li>Evitar qualquer forma de discriminação, assédio ou comportamento ofensivo.</li>
      </ul>

      <h4>2. Integridade e Honestidade</h4>
      <ul>
        <li>Agir com transparência em todas as atividades e decisões.</li>
        <li>Não praticar plágio, fraude ou qualquer forma de desonestidade acadêmica e profissional.</li>
        <li>Assumir a responsabilidade pelos próprios atos e resultados.</li>
      </ul>

      <h4>3. Compromisso com a Sustentabilidade</h4>
      <ul>
        <li>Incentivar práticas agrícolas responsáveis e sustentáveis.</li>
        <li>Respeitar o meio ambiente e promover o uso consciente dos recursos naturais.</li>
        <li>Buscar soluções que conciliem produtividade, preservação ambiental e bem-estar social.</li>
      </ul>

      <h4>4. Liderança Exemplar</h4>
      <ul>
        <li>Servir de exemplo por meio de atitudes positivas e éticas.</li>
        <li>Demonstrar iniciativa, responsabilidade e espírito de equipe.</li>
        <li>Incentivar a cooperação e o desenvolvimento dos demais participantes.</li>
      </ul>

      <h4>5. Responsabilidade e Comprometimento</h4>
      <ul>
        <li>Cumprir horários, prazos e compromissos assumidos.</li>
        <li>Participar ativamente das atividades do programa.</li>
        <li>Zelar pelos materiais, equipamentos e espaços utilizados.</li>
      </ul>

      <h4>6. Comunicação e Trabalho em Equipe</h4>
      <ul>
        <li>Manter uma comunicação clara, respeitosa e construtiva.</li>
        <li>Ouvir opiniões diferentes e resolver conflitos de forma pacífica.</li>
        <li>Compartilhar conhecimentos para fortalecer o aprendizado coletivo.</li>
      </ul>

      <h4>7. Inovação e Desenvolvimento Contínuo</h4>
      <ul>
        <li>Buscar constantemente novos conhecimentos e tecnologias para o agronegócio.</li>
        <li>Estimular a criatividade e a melhoria dos processos produtivos.</li>
        <li>Estar aberto ao aprendizado e ao aperfeiçoamento profissional.</li>
      </ul>

      <h4>8. Confidencialidade e Segurança</h4>
      <ul>
        <li>Respeitar informações confidenciais compartilhadas durante o programa.</li>
        <li>Utilizar dados e informações de forma ética e responsável.</li>
        <li>Seguir as normas de segurança em atividades práticas e visitas técnicas.</li>
      </ul>

      <h4>Compromisso do Líder</h4>
      <div class="citacao">
        “Comprometo-me a agir com ética, responsabilidade, respeito e profissionalismo, contribuindo para o desenvolvimento sustentável do agronegócio e servindo como exemplo de liderança positiva para minha equipe e comunidade.”
      </div>
    </section>
    """
    return render_pagina(conteudo, "Inscrição - PLANTA", page="inscricao", turmas=TURMAS_VALIDAS)


@app.route("/consulta", methods=["GET", "POST"])
def consulta():
    resultado = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        cpf = re.sub(r"\D", "", request.form.get("cpf", "").strip())

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM inscricoes
                    WHERE email = %s AND cpf = %s
                    ORDER BY id DESC
                    LIMIT 1
                """, (email, cpf))
                resultado = cur.fetchone()

        if not resultado:
            flash("Inscrição não encontrada para este e-mail/CPF.", "erro")

    conteudo = """
    <section class="card">
      <h2>Consultar inscrição</h2>
      <form method="POST">
        <label>E-mail</label>
        <input type="email" name="email" required>
        <label>CPF</label>
        <input type="text" name="cpf" required>
        <button type="submit">Consultar</button>
      </form>
    </section>

    {% if resultado %}
    <section class="card">
      <h3>Resultado</h3>
      <p><strong>Nome:</strong> {{ resultado['nome'] }}</p>
      <p><strong>Turma:</strong> {{ resultado['turma'] }}</p>
      <p>
        <strong>Status:</strong>
        {% if resultado['status'] == 'Aceita' %}
          <span class="badge aceita">Aceita</span>
          {% if resultado['acesso_aluno_ativo'] %}
            <small> | acesso ativo</small>
          {% else %}
            <small> | acesso removido</small>
          {% endif %}
        {% elif resultado['status'] == 'Lista de Espera' %}
          <span class="badge espera">Lista de Espera</span>
          {% if resultado['posicao_espera'] %}
            <small> | posição {{ resultado['posicao_espera'] }}</small>
          {% endif %}
        {% elif resultado['status'] == 'Negada' %}
          <span class="badge negada">Negada</span>
        {% else %}
          <span class="badge pendente">Pendente</span>
        {% endif %}
      </p>
      {% if resultado['status'] == 'Negada' and resultado['motivo_negacao'] %}
        <p><strong>Motivo:</strong> {{ resultado['motivo_negacao'] }}</p>
      {% endif %}
    </section>
    {% endif %}
    """
    return render_pagina(conteudo, "Consultar inscrição", page="consulta", resultado=resultado)


# ========================== ADMIN ==========================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "").strip()

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM admin_users WHERE email = %s AND ativo = TRUE", (email,))
                admin = cur.fetchone()

        if not admin:
            flash("Administrador não encontrado.", "erro")
            return redirect(url_for("admin_login"))

        if not check_password_hash(admin["senha_hash"], senha):
            flash("Senha incorreta.", "erro")
            return redirect(url_for("admin_login"))

        session["admin_autenticado"] = True
        session["admin_email"] = admin["email"]
        session["admin_nome"] = admin["nome"]
        flash("Login admin realizado com sucesso.", "ok")
        return redirect(url_for("admin_inscritos"))

    conteudo = """
    <section class="card">
      <h2>Login do Administrador</h2>
      <form method="POST">
        <label>E-mail</label>
        <input type="email" name="email" required>
        <label>Senha</label>
        <input type="password" name="senha" required>
        <button type="submit">Entrar</button>
      </form>
    </section>
    """
    return render_pagina(conteudo, "Login Admin", page="admin_login")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_autenticado", None)
    session.pop("admin_email", None)
    session.pop("admin_nome", None)
    flash("Logout admin realizado.", "ok")
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_root():
    return redirect(url_for("admin_inscritos"))


@app.route("/admin/info")
@admin_required
def admin_info():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nome, email, criado_em FROM admin_users WHERE email = %s", (session.get("admin_email"),))
            admin = cur.fetchone()

    conteudo = """
    <section class="card">
      <h2>Informações da Conta (Admin)</h2>
      <p><strong>Nome:</strong> {{ admin['nome'] }}</p>
      <p><strong>E-mail:</strong> {{ admin['email'] }}</p>
      <p><strong>Criado em:</strong> {{ admin['criado_em'] or '-' }}</p>
    </section>
    """
    return render_pagina(conteudo, "Informações Admin", page="admin_info", admin=admin)


@app.route("/admin/config", methods=["GET", "POST"])
@admin_required
def admin_config():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM admin_users WHERE email = %s", (session.get("admin_email"),))
            admin = cur.fetchone()

            if request.method == "POST":
                nome = request.form.get("nome", "").strip()
                senha_atual = request.form.get("senha_atual", "").strip()
                nova_senha = request.form.get("nova_senha", "").strip()
                confirmar_senha = request.form.get("confirmar_senha", "").strip()

                if not nome:
                    flash("Nome é obrigatório.", "erro")
                    return redirect(url_for("admin_config"))

                if senha_atual or nova_senha or confirmar_senha:
                    if not check_password_hash(admin["senha_hash"], senha_atual):
                        flash("Senha atual incorreta.", "erro")
                        return redirect(url_for("admin_config"))
                    if len(nova_senha) < 6:
                        flash("Nova senha deve ter pelo menos 6 caracteres.", "erro")
                        return redirect(url_for("admin_config"))
                    if nova_senha != confirmar_senha:
                        flash("Confirmação da nova senha não confere.", "erro")
                        return redirect(url_for("admin_config"))

                    cur.execute("""
                        UPDATE admin_users
                        SET nome = %s, senha_hash = %s
                        WHERE email = %s
                    """, (nome, generate_password_hash(nova_senha), admin["email"]))
                else:
                    cur.execute("UPDATE admin_users SET nome = %s WHERE email = %s", (nome, admin["email"]))

                session["admin_nome"] = nome
                flash("Configurações de admin atualizadas.", "ok")
                return redirect(url_for("admin_config"))

    conteudo = """
    <section class="card">
      <h2>Configurações da Conta (Admin)</h2>
      <form method="POST">
        <label>Nome</label>
        <input type="text" name="nome" value="{{ admin['nome'] }}" required>

        <h4 style="margin-top:18px;">Alterar senha (opcional)</h4>
        <label>Senha atual</label>
        <input type="password" name="senha_atual">

        <label>Nova senha</label>
        <input type="password" name="nova_senha">

        <label>Confirmar nova senha</label>
        <input type="password" name="confirmar_senha">

        <button type="submit">Salvar configurações</button>
      </form>
    </section>
    """
    return render_pagina(conteudo, "Configurações Admin", page="admin_config", admin=admin)


@app.route("/admin/inscritos")
@admin_required
def admin_inscritos():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM inscricoes
                WHERE status = 'Pendente'
                   OR status = 'Lista de Espera'
                   OR (status = 'Aceita' AND acesso_aluno_ativo = TRUE)
                ORDER BY id DESC
            """)
            rows = cur.fetchall()

    grupos = {t: [] for t in TURMAS_VALIDAS}
    for r in rows:
        if r["turma"] in grupos:
            grupos[r["turma"]].append(r)

    conteudo = """
    <section class="card">
      <h2>Inscritos por Turma</h2>
      <p>Separado por 1°, 2° e 3° Agronegócio.</p>
    </section>

    {% for turma in turmas %}
    <section class="card">
      <h3>{{ turma }}</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th><th>Nome</th><th>E-mail</th><th>Status</th><th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {% for i in grupos[turma] %}
              <tr>
                <td>{{ i['id'] }}</td>
                <td>
                  <strong>{{ i['nome'] }}</strong><br>
                  <small>CPF: {{ i['cpf'] }} | Tel: {{ i['telefone'] }}</small>
                </td>
                <td>{{ i['email'] }}</td>
                <td>
                  {% if i['status'] == 'Aceita' %}
                    <span class="badge aceita">Aceita</span>
                  {% elif i['status'] == 'Lista de Espera' %}
                    <span class="badge espera">Lista de Espera</span>
                    {% if i['posicao_espera'] %}
                      <br><small>Posição: {{ i['posicao_espera'] }}</small>
                    {% endif %}
                  {% elif i['status'] == 'Negada' %}
                    <span class="badge negada">Negada</span>
                  {% else %}
                    <span class="badge pendente">Pendente</span>
                  {% endif %}
                </td>
                <td>
                  {% if i['status'] == 'Pendente' or i['status'] == 'Lista de Espera' %}
                    <form method="POST" action="{{ url_for('aceitar_inscricao', inscricao_id=i['id']) }}" style="margin-bottom:8px;">
                      <button type="submit">Aceitar</button>
                    </form>

                    <form method="POST" action="{{ url_for('lista_espera_inscricao', inscricao_id=i['id']) }}" style="margin-bottom:8px;">
                      <input type="number" min="1" name="posicao_espera" placeholder="Posição na fila" required>
                      <button type="submit" class="btn warning">Lista de espera</button>
                    </form>

                    <form method="POST" action="{{ url_for('negar_inscricao', inscricao_id=i['id']) }}">
                      <input type="text" name="motivo" placeholder="Motivo (opcional)">
                      <button type="submit" class="btn danger">Negar</button>
                    </form>
                  {% elif i['status'] == 'Aceita' %}
                    <form method="POST" action="{{ url_for('remover_acesso_aluno', inscricao_id=i['id']) }}">
                      <button type="submit" class="btn danger">Remover acesso</button>
                    </form>
                  {% endif %}
                </td>
              </tr>
            {% else %}
              <tr><td colspan="5">Nenhum inscrito exibível nesta turma.</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </section>
    {% endfor %}
    """
    return render_pagina(
        conteudo,
        "Inscritos - Admin",
        page="admin_inscritos",
        grupos=grupos,
        turmas=TURMAS_VALIDAS
    )


@app.route("/admin/lista-espera/<int:inscricao_id>", methods=["POST"])
@admin_required
def lista_espera_inscricao(inscricao_id):
    pos = request.form.get("posicao_espera", "").strip()
    if not pos.isdigit() or int(pos) < 1:
        flash("Informe uma posição válida (1 ou maior).", "erro")
        return redirect(url_for("admin_inscritos"))

    posicao = int(pos)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM inscricoes WHERE id = %s", (inscricao_id,))
            insc = cur.fetchone()

            if not insc:
                flash("Inscrição não encontrada.", "erro")
                return redirect(url_for("admin_inscritos"))

            cur.execute("""
                UPDATE inscricoes
                SET status = 'Lista de Espera',
                    posicao_espera = %s,
                    decidido_por = %s,
                    data_decisao = %s,
                    acesso_aluno_ativo = FALSE
                WHERE id = %s
            """, (posicao, session.get("admin_email"), now_str(), inscricao_id))

            cur.execute("""
                UPDATE alunos_users
                SET ativo = FALSE, senha_hash = %s
                WHERE inscricao_id = %s
            """, (generate_password_hash(os.urandom(16).hex()), inscricao_id))

    flash(f"Inscrição #{inscricao_id} enviada para lista de espera (posição {posicao}).", "ok")
    return redirect(url_for("admin_inscritos"))


@app.route("/admin/postagens", methods=["GET", "POST"])
@admin_required
def admin_postagens():
    if request.method == "POST":
        conteudo_post = request.form.get("conteudo", "").strip()
        if not conteudo_post:
            flash("Digite algo antes de publicar.", "erro")
            return redirect(url_for("admin_postagens"))

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO postagens (conteudo, autor_email, criado_em, ativo)
                    VALUES (%s, %s, %s, TRUE)
                """, (conteudo_post, session.get("admin_email"), now_str()))
        flash("Postagem publicada com sucesso.", "ok")
        return redirect(url_for("admin_postagens"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.id,
                       p.conteudo,
                       COALESCE(a.nome, p.autor_email) AS autor_nome,
                       p.criado_em
                FROM postagens p
                LEFT JOIN admin_users a ON a.email = p.autor_email
                WHERE p.ativo = TRUE
                ORDER BY p.id DESC
            """)
            postagens = cur.fetchall()

    conteudo = """
    <section class="card">
      <h2>Postagens</h2>
      <form method="POST">
        <label>Mensagem para os alunos</label>
        <textarea name="conteudo" required placeholder="Escreva aqui..."></textarea>
        <button type="submit">Publicar</button>
      </form>
    </section>

    <section class="card">
      <h3>Publicadas</h3>
      {% for p in postagens %}
        <div class="post">
          <small><strong>{{ p['autor_nome'] }}</strong> • {{ p['criado_em'] }}</small>
          <p>{{ p['conteudo'] }}</p>

          <form method="POST" action="{{ url_for('admin_remover_postagem', post_id=p['id']) }}">
            <button type="submit" class="btn danger">Remover postagem</button>
          </form>
        </div>
      {% else %}
        <p>Nenhuma postagem ainda.</p>
      {% endfor %}
    </section>
    """
    return render_pagina(conteudo, "Postagens - Admin", page="admin_postagens", postagens=postagens)


@app.route("/admin/postagens/remover/<int:post_id>", methods=["POST"])
@admin_required
def admin_remover_postagem(post_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE postagens SET ativo = FALSE WHERE id = %s", (post_id,))

    flash("Postagem removida com sucesso.", "ok")
    return redirect(url_for("admin_postagens"))


@app.route("/admin/aceitar/<int:inscricao_id>", methods=["POST"])
@admin_required
def aceitar_inscricao(inscricao_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM inscricoes WHERE id = %s", (inscricao_id,))
            row = cur.fetchone()

            if not row:
                flash("Inscrição não encontrada.", "erro")
                return redirect(url_for("admin_inscritos"))

            if row["status"] not in ("Pendente", "Lista de Espera"):
                flash("Somente pendentes/lista de espera podem ser aceitas.", "erro")
                return redirect(url_for("admin_inscritos"))

            cur.execute("""
                UPDATE inscricoes
                SET status = 'Aceita',
                    posicao_espera = NULL,
                    motivo_negacao = NULL,
                    decidido_por = %s,
                    data_decisao = %s,
                    acesso_aluno_ativo = TRUE
                WHERE id = %s
            """, (session.get("admin_email"), now_str(), inscricao_id))

    flash(f"Inscrição #{inscricao_id} aceita.", "ok")
    return redirect(url_for("admin_inscritos"))


@app.route("/admin/negar/<int:inscricao_id>", methods=["POST"])
@admin_required
def negar_inscricao(inscricao_id):
    motivo = request.form.get("motivo", "").strip()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM inscricoes WHERE id = %s", (inscricao_id,))
            insc = cur.fetchone()

            if not insc:
                flash("Inscrição não encontrada.", "erro")
                return redirect(url_for("admin_inscritos"))

            if insc["status"] not in ("Pendente", "Lista de Espera"):
                flash("Somente pendentes/lista de espera podem ser negadas.", "erro")
                return redirect(url_for("admin_inscritos"))

            cur.execute("""
                UPDATE inscricoes
                SET status = 'Negada',
                    decidido_por = %s,
                    data_decisao = %s,
                    motivo_negacao = %s,
                    posicao_espera = NULL,
                    acesso_aluno_ativo = FALSE
                WHERE id = %s
            """, (session.get("admin_email"), now_str(), motivo, inscricao_id))

            cur.execute("""
                UPDATE alunos_users
                SET ativo = FALSE, senha_hash = %s
                WHERE inscricao_id = %s
            """, (generate_password_hash(os.urandom(16).hex()), inscricao_id))

    flash(f"Inscrição #{inscricao_id} negada.", "ok")
    return redirect(url_for("admin_inscritos"))


@app.route("/admin/remover-acesso/<int:inscricao_id>", methods=["POST"])
@admin_required
def remover_acesso_aluno(inscricao_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM inscricoes WHERE id = %s", (inscricao_id,))
            insc = cur.fetchone()

            if not insc:
                flash("Inscrição não encontrada.", "erro")
                return redirect(url_for("admin_inscritos"))

            if insc["status"] != "Aceita":
                flash("Só é possível remover acesso de inscrição aceita.", "erro")
                return redirect(url_for("admin_inscritos"))

            cur.execute("""
                UPDATE alunos_users
                SET ativo = FALSE, senha_hash = %s
                WHERE inscricao_id = %s
            """, (generate_password_hash(os.urandom(16).hex()), inscricao_id))

            cur.execute("""
                UPDATE inscricoes
                SET acesso_aluno_ativo = FALSE
                WHERE id = %s
            """, (inscricao_id,))

    flash(f"Acesso do aluno da inscrição #{inscricao_id} removido.", "ok")
    return redirect(url_for("admin_inscritos"))


# ========================== ALUNO ==========================

@app.route("/aluno/primeiro-acesso", methods=["GET", "POST"])
def aluno_primeiro_acesso():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        cpf = re.sub(r"\D", "", request.form.get("cpf", "").strip())
        senha = request.form.get("senha", "").strip()
        confirmar = request.form.get("confirmar_senha", "").strip()

        if len(senha) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "erro")
            return redirect(url_for("aluno_primeiro_acesso"))
        if senha != confirmar:
            flash("Confirmação de senha não confere.", "erro")
            return redirect(url_for("aluno_primeiro_acesso"))

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM inscricoes
                    WHERE email = %s AND cpf = %s
                    ORDER BY id DESC
                    LIMIT 1
                """, (email, cpf))
                insc = cur.fetchone()

                if not insc:
                    flash("Inscrição não encontrada.", "erro")
                    return redirect(url_for("aluno_primeiro_acesso"))

                if insc["status"] != "Aceita" or not insc["acesso_aluno_ativo"]:
                    flash("Acesso indisponível. Verifique o status da inscrição.", "erro")
                    return redirect(url_for("consulta"))

                cur.execute("SELECT * FROM alunos_users WHERE inscricao_id = %s", (insc["id"],))
                ja = cur.fetchone()
                if ja:
                    if ja["ativo"]:
                        flash("Conta já criada. Faça login de aluno.", "ok")
                        return redirect(url_for("aluno_login"))
                    flash("Seu acesso foi removido pela administração.", "erro")
                    return redirect(url_for("consulta"))

                cur.execute("""
                    INSERT INTO alunos_users (inscricao_id, email, cpf, nome, senha_hash, ativo, criado_em)
                    VALUES (%s, %s, %s, %s, %s, TRUE, %s)
                """, (insc["id"], insc["email"], insc["cpf"], insc["nome"], generate_password_hash(senha), now_str()))

        flash("Conta criada com sucesso. Faça login de aluno.", "ok")
        return redirect(url_for("aluno_login"))

    conteudo = """
    <section class="card">
      <h2>Primeiro acesso do aluno</h2>
      <form method="POST">
        <label>E-mail usado na inscrição</label>
        <input type="email" name="email" required>

        <label>CPF usado na inscrição</label>
        <input type="text" name="cpf" required>

        <label>Criar senha</label>
        <input type="password" name="senha" required>

        <label>Confirmar senha</label>
        <input type="password" name="confirmar_senha" required>

        <button type="submit">Criar conta</button>
      </form>
    </section>
    """
    return render_pagina(conteudo, "Primeiro acesso do aluno", page="aluno_primeiro_acesso")


@app.route("/aluno/login", methods=["GET", "POST"])
def aluno_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "").strip()

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM alunos_users WHERE email = %s AND ativo = TRUE", (email,))
                aluno = cur.fetchone()

        if not aluno or not check_password_hash(aluno["senha_hash"], senha):
            flash("E-mail ou senha inválidos.", "erro")
            return redirect(url_for("aluno_login"))

        session["aluno_autenticado"] = True
        session["aluno_email"] = aluno["email"]
        session["aluno_nome"] = aluno["nome"]
        flash("Login de aluno realizado.", "ok")
        return redirect(url_for("aluno_dashboard"))

    conteudo = """
    <section class="card">
      <h2>Login do aluno</h2>
      <form method="POST">
        <label>E-mail</label>
        <input type="email" name="email" required>

        <label>Senha</label>
        <input type="password" name="senha" required>

        <button type="submit">Entrar</button>
      </form>
    </section>
    """
    return render_pagina(conteudo, "Login Aluno", page="aluno_login")


@app.route("/aluno/logout")
def aluno_logout():
    session.pop("aluno_autenticado", None)
    session.pop("aluno_email", None)
    session.pop("aluno_nome", None)
    flash("Logout de aluno realizado.", "ok")
    return redirect(url_for("aluno_login"))


@app.route("/aluno")
@aluno_required
def aluno_dashboard():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.conteudo,
                       COALESCE(a.nome, p.autor_email) AS autor_nome,
                       p.criado_em
                FROM postagens p
                LEFT JOIN admin_users a ON a.email = p.autor_email
                WHERE p.ativo = TRUE
                ORDER BY p.id DESC
            """)
            postagens = cur.fetchall()

    conteudo = """
    <section class="card">
      <h2>Mural de Postagens</h2>
      <p>Comunicados dos professores/admin:</p>
    </section>

    <section class="card">
      {% for p in postagens %}
        <div class="post">
          <small><strong>{{ p['autor_nome'] }}</strong> • {{ p['criado_em'] }}</small>
          <p>{{ p['conteudo'] }}</p>
        </div>
      {% else %}
        <p>Ainda não há postagens.</p>
      {% endfor %}
    </section>
    """
    return render_pagina(conteudo, "Mural do Aluno", page="aluno_dashboard", postagens=postagens)


@app.route("/aluno/info")
@aluno_required
def aluno_info():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.nome, a.email, a.cpf, a.criado_em, i.turma, i.status
                FROM alunos_users a
                LEFT JOIN inscricoes i ON i.id = a.inscricao_id
                WHERE a.email = %s AND a.ativo = TRUE
            """, (session.get("aluno_email"),))
            aluno = cur.fetchone()

    conteudo = """
    <section class="card">
      <h2>Informações da Conta (Aluno)</h2>
      <p><strong>Nome:</strong> {{ aluno['nome'] }}</p>
      <p><strong>E-mail:</strong> {{ aluno['email'] }}</p>
      <p><strong>CPF:</strong> {{ aluno['cpf'] }}</p>
      <p><strong>Turma:</strong> {{ aluno['turma'] or '-' }}</p>
      <p><strong>Status:</strong> {{ aluno['status'] or '-' }}</p>
      <p><strong>Criado em:</strong> {{ aluno['criado_em'] or '-' }}</p>
    </section>
    """
    return render_pagina(conteudo, "Informações Aluno", page="aluno_info", aluno=aluno)


@app.route("/aluno/config", methods=["GET", "POST"])
@aluno_required
def aluno_config():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM alunos_users WHERE email = %s AND ativo = TRUE", (session.get("aluno_email"),))
            aluno = cur.fetchone()

            if request.method == "POST":
                nome = request.form.get("nome", "").strip()
                senha_atual = request.form.get("senha_atual", "").strip()
                nova_senha = request.form.get("nova_senha", "").strip()
                confirmar_senha = request.form.get("confirmar_senha", "").strip()

                if not nome:
                    flash("Nome é obrigatório.", "erro")
                    return redirect(url_for("aluno_config"))

                if senha_atual or nova_senha or confirmar_senha:
                    if not check_password_hash(aluno["senha_hash"], senha_atual):
                        flash("Senha atual incorreta.", "erro")
                        return redirect(url_for("aluno_config"))
                    if len(nova_senha) < 6:
                        flash("Nova senha deve ter pelo menos 6 caracteres.", "erro")
                        return redirect(url_for("aluno_config"))
                    if nova_senha != confirmar_senha:
                        flash("Confirmação da nova senha não confere.", "erro")
                        return redirect(url_for("aluno_config"))

                    cur.execute("""
                        UPDATE alunos_users
                        SET nome = %s, senha_hash = %s
                        WHERE email = %s
                    """, (nome, generate_password_hash(nova_senha), aluno["email"]))
                else:
                    cur.execute("UPDATE alunos_users SET nome = %s WHERE email = %s", (nome, aluno["email"]))

                session["aluno_nome"] = nome
                flash("Configurações de aluno atualizadas.", "ok")
                return redirect(url_for("aluno_config"))

    conteudo = """
    <section class="card">
      <h2>Configurações da Conta (Aluno)</h2>
      <form method="POST">
        <label>Nome</label>
        <input type="text" name="nome" value="{{ aluno['nome'] }}" required>

        <h4 style="margin-top:18px;">Alterar senha (opcional)</h4>
        <label>Senha atual</label>
        <input type="password" name="senha_atual">

        <label>Nova senha</label>
        <input type="password" name="nova_senha">

        <label>Confirmar nova senha</label>
        <input type="password" name="confirmar_senha">

        <button type="submit">Salvar configurações</button>
      </form>
    </section>
    """
    return render_pagina(conteudo, "Configurações Aluno", page="aluno_config", aluno=aluno)


# Inicialização
init_db()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)