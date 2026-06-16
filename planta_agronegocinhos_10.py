from flask import Flask, request, redirect, url_for, session, flash, render_template_string
from functools import wraps
import os
import re
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")

DATABASE_URL = os.getenv("DATABASE_URL")

LOGO_FILENAME = "planta_logo.jpeg"
EDITAL_FILENAME = "edital_inscricao_planta.pdf"

TURMAS_VALIDAS = ["1° Agronegócio", "2° Agronegócio", "3° Agronegócio"]

ADMIN_SEEDS = {
    "nelise.ruscheinsky@escola.pr.gov.br": {"nome": "Nelise Ruscheinsky", "senha": "agrocepem"},
    "alexandra.martinez@escola.pr.gov.br": {"nome": "Alexandra da Silva Martinez", "senha": "agrocepem"},
    "victor.luiz.marchi@escola.pr.gov.br": {"nome": "Victor Luiz Marchi", "senha": "agrocepem"},
    "s.claudinei@escola.pr.gov.br": {"nome": "Claudinei Ferreira da Silva", "senha": "agrocepem"},
}

MISSAO = "Desenvolver líderes capacitados, éticos e inovadores no agronegócio."
VISAO = "Ser referência na formação de lideranças do agronegócio."
VALORES = [
    "🌱 Sustentabilidade",
    "🤝 Ética",
    "🚜 Comprometimento",
    "💡 Inovação",
    "📚 Aprendizado contínuo",
    "👥 Trabalho em equipe",
    "🏆 Excelência",
    "🌎 Responsabilidade social",
]


def now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("Variável DATABASE_URL não configurada.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("admin_autenticado"):
            flash("Faça login admin.", "erro")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapped


def aluno_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("aluno_autenticado"):
            flash("Faça login de aluno.", "erro")
            return redirect(url_for("aluno_login"))
        return f(*args, **kwargs)
    return wrapped


def nav_items(page):
    if session.get("admin_autenticado"):
        return [
            ("Inscritos", url_for("admin_inscritos"), ""),
            ("Postagens", url_for("admin_postagens"), "sec"),
            ("Logout", url_for("admin_logout"), "danger"),
        ]
    if session.get("aluno_autenticado"):
        return [
            ("Mural", url_for("aluno_dashboard"), ""),
            ("Config", url_for("aluno_config"), "sec"),
            ("Logout", url_for("aluno_logout"), "danger"),
        ]

    base = []
    if page != "home":
        base.append(("Início", url_for("index"), ""))
    if page != "inscricao":
        base.append(("Inscrição", url_for("inscricao"), ""))
    if page != "consulta":
        base.append(("Consulta", url_for("consulta"), "sec"))
    if page != "aluno_primeiro":
        base.append(("Primeiro acesso", url_for("aluno_primeiro_acesso"), "sec"))
    if page != "aluno_login":
        base.append(("Login Aluno", url_for("aluno_login"), ""))
    if page != "admin_login":
        base.append(("Login Admin", url_for("admin_login"), "warn"))
    return base


LAYOUT_INI = """
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ titulo }}</title>
<style>
*{box-sizing:border-box;font-family:Arial,sans-serif}
body{margin:0;background:#f5f7f5;color:#1f2937;padding-top:64px}
.topbar{position:fixed;top:0;left:0;right:0;background:#111827;color:#fff;padding:10px 12px;z-index:99}
.topin{max-width:1100px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
.brand{font-weight:700}
.nav{display:flex;gap:8px;flex-wrap:wrap}
.btn{display:inline-block;padding:8px 12px;border-radius:8px;background:#166534;color:#fff;text-decoration:none;border:none;cursor:pointer}
.btn.sec{background:#374151}
.btn.warn{background:#92400e}
.btn.danger{background:#b91c1c}
.container{max-width:1100px;margin:22px auto;padding:0 14px}
.card{background:#fff;border-radius:12px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.08);margin-bottom:14px}
label{display:block;margin-top:10px;margin-bottom:6px;font-weight:700}
input,select,textarea{width:100%;padding:10px;border:1px solid #d1d5db;border-radius:8px}
textarea{min-height:100px}
.alert{padding:10px;border-radius:8px;margin-bottom:10px}
.alert.erro{background:#fee2e2;color:#991b1b}
.alert.ok{background:#dcfce7;color:#166534}
table{width:100%;border-collapse:collapse}
th,td{padding:8px;border-bottom:1px solid #e5e7eb;text-align:left;vertical-align:top}
th{background:#f3f4f6}
.badge{display:inline-block;padding:3px 8px;border-radius:999px;font-size:12px;font-weight:700}
.pendente{background:#fef3c7;color:#92400e}
.aceita{background:#dcfce7;color:#166534}
.negada{background:#fee2e2;color:#991b1b}
.espera{background:#e0e7ff;color:#3730a3}
.post{border:1px solid #e5e7eb;padding:10px;border-radius:10px;margin-bottom:10px}
small{color:#6b7280}
</style>
</head>
<body>
<div class="topbar">
  <div class="topin">
    <div class="brand">PLANTA • CEPEM</div>
    <div class="nav">
      {% for label, href, cls in nav %}
        <a class="btn {% if cls=='sec' %}sec{% elif cls=='warn' %}warn{% elif cls=='danger' %}danger{% endif %}" href="{{ href }}">{{ label }}</a>
      {% endfor %}
    </div>
  </div>
</div>
<div class="container">
  <div class="card" style="text-align:center">
    <img src="{{ url_for('static', filename=logo_filename) }}" alt="Logo" style="max-height:120px">
  </div>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat,msg in messages %}
      <div class="alert {{ cat }}">{{ msg }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}
"""

LAYOUT_FIM = """
</div>
</body>
</html>
"""


def render_page(html, titulo, page, **ctx):
    return render_template_string(
        LAYOUT_INI + html + LAYOUT_FIM,
        titulo=titulo,
        nav=nav_items(page),
        logo_filename=LOGO_FILENAME,
        missao=MISSAO,
        visao=VISAO,
        valores=VALORES,
        EDITAL_FILENAME=EDITAL_FILENAME,
        **ctx
    )


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
                    motivo_negacao TEXT,
                    posicao_espera INTEGER,
                    acesso_aluno_ativo BOOLEAN NOT NULL DEFAULT FALSE,
                    decidido_por TEXT,
                    data_decisao TEXT,
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

            for email, dados in ADMIN_SEEDS.items():
                cur.execute("""
                    INSERT INTO admin_users (email, nome, senha_hash, ativo, criado_em)
                    VALUES (%s, %s, %s, TRUE, %s)
                    ON CONFLICT (email) DO NOTHING
                """, (email.lower(), dados["nome"], generate_password_hash(dados["senha"]), now_str()))

        conn.commit()


# ---------------- PÚBLICO ---------------- #

@app.route("/")
def index():
    html = """
    <div class="card">
      <h2>Bem-vindo ao PLANTA</h2>
      <p>Programa Liderança de Alto Nível do Técnico em Agronegócio.</p>
      <a class="btn" href="{{ url_for('inscricao') }}">Fazer inscrição</a>
      <a class="btn sec" href="{{ url_for('consulta') }}">Consultar inscrição</a>
    </div>

    <div class="card">
      <h3>Edital</h3>
      <a class="btn warn" href="{{ url_for('static', filename=EDITAL_FILENAME) }}" target="_blank" rel="noopener">Abrir Edital (PDF)</a>
    </div>

    <div class="card">
      <h3>Missão</h3><p>{{ missao }}</p>
      <h3>Visão</h3><p>{{ visao }}</p>
      <h3>Valores</h3>
      <ul>{% for v in valores %}<li>{{ v }}</li>{% endfor %}</ul>
    </div>
    """
    return render_page(html, "Início - PLANTA", "home")


@app.route("/inscricao", methods=["GET", "POST"])
def inscricao():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        data_nascimento = request.form.get("data_nascimento", "").strip()
        cpf = re.sub(r"\D", "", request.form.get("cpf", "").strip())
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        turma = request.form.get("turma", "").strip()
        compromisso = request.form.get("compromisso_lider") == "on"

        if not all([nome, data_nascimento, cpf, email, telefone, turma]):
            flash("Preencha todos os campos.", "erro")
            return redirect(url_for("inscricao"))
        if len(cpf) != 11:
            flash("CPF inválido (11 dígitos).", "erro")
            return redirect(url_for("inscricao"))
        if turma not in TURMAS_VALIDAS:
            flash("Turma inválida.", "erro")
            return redirect(url_for("inscricao"))
        if not compromisso:
            flash("É obrigatório aceitar o Compromisso do Líder.", "erro")
            return redirect(url_for("inscricao"))

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO inscricoes
                    (nome, data_nascimento, cpf, email, telefone, turma, compromisso_lider, status, acesso_aluno_ativo, criado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pendente', FALSE, %s)
                """, (nome, data_nascimento, cpf, email, telefone, turma, compromisso, now_str()))
            conn.commit()

        flash("Inscrição enviada com sucesso.", "ok")
        return redirect(url_for("consulta"))

    html = """
    <div class="card">
      <h2>Formulário de Inscrição</h2>
      <form method="POST">
        <label>Nome</label><input name="nome" required>
        <label>Data de nascimento</label><input type="date" name="data_nascimento" required>
        <label>CPF</label><input name="cpf" required>
        <label>E-mail</label><input type="email" name="email" required>
        <label>Telefone</label><input name="telefone" required>
        <label>Turma</label>
        <select name="turma" required>
          <option value="">Selecione</option>
          {% for t in turmas %}<option value="{{t}}">{{t}}</option>{% endfor %}
        </select>
        <label style="margin-top:12px"><input type="checkbox" name="compromisso_lider" required> Li e aceito o Compromisso do Líder</label>
        <button class="btn" type="submit">Enviar inscrição</button>
      </form>
    </div>
    """
    return render_page(html, "Inscrição - PLANTA", "inscricao", turmas=TURMAS_VALIDAS)


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
                    WHERE email=%s AND cpf=%s
                    ORDER BY id DESC
                    LIMIT 1
                """, (email, cpf))
                resultado = cur.fetchone()

        if not resultado:
            flash("Inscrição não encontrada.", "erro")

    html = """
    <div class="card">
      <h2>Consulta de inscrição</h2>
      <form method="POST">
        <label>E-mail</label><input type="email" name="email" required>
        <label>CPF</label><input name="cpf" required>
        <button class="btn" type="submit">Consultar</button>
      </form>
    </div>

    {% if resultado %}
      <div class="card">
        <h3>Resultado</h3>
        <p><strong>Nome:</strong> {{ resultado['nome'] }}</p>
        <p><strong>Turma:</strong> {{ resultado['turma'] }}</p>
        <p><strong>Status:</strong>
          {% if resultado['status'] == 'Aceita' %}
            <span class="badge aceita">Aceita</span>
          {% elif resultado['status'] == 'Negada' %}
            <span class="badge negada">Negada</span>
          {% elif resultado['status'] == 'Lista de Espera' %}
            <span class="badge espera">Lista de Espera</span>
            {% if resultado['posicao_espera'] %} (posição {{resultado['posicao_espera']}}){% endif %}
          {% else %}
            <span class="badge pendente">Pendente</span>
          {% endif %}
        </p>
        {% if resultado['motivo_negacao'] %}
          <p><strong>Motivo:</strong> {{ resultado['motivo_negacao'] }}</p>
        {% endif %}
      </div>
    {% endif %}
    """
    return render_page(html, "Consulta - PLANTA", "consulta", resultado=resultado)


# ---------------- ADMIN ---------------- #

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "").strip()

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM admin_users WHERE email=%s AND ativo=TRUE", (email,))
                admin = cur.fetchone()

        if not admin or not check_password_hash(admin["senha_hash"], senha):
            flash("Credenciais inválidas.", "erro")
            return redirect(url_for("admin_login"))

        session["admin_autenticado"] = True
        session["admin_email"] = admin["email"]
        session["admin_nome"] = admin["nome"]
        flash("Login admin realizado.", "ok")
        return redirect(url_for("admin_inscritos"))

    html = """
    <div class="card">
      <h2>Login Admin</h2>
      <form method="POST">
        <label>E-mail</label><input type="email" name="email" required>
        <label>Senha</label><input type="password" name="senha" required>
        <button class="btn" type="submit">Entrar</button>
      </form>
    </div>
    """
    return render_page(html, "Login Admin", "admin_login")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Logout admin realizado.", "ok")
    return redirect(url_for("admin_login"))


@app.route("/admin/inscritos")
@admin_required
def admin_inscritos():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM inscricoes ORDER BY id DESC")
            rows = cur.fetchall()

    html = """
    <div class="card">
      <h2>Inscritos</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th><th>Nome</th><th>E-mail</th><th>Turma</th><th>Status</th><th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {% for i in rows %}
          <tr>
            <td>{{ i['id'] }}</td>
            <td>{{ i['nome'] }}<br><small>CPF {{ i['cpf'] }} | {{ i['telefone'] }}</small></td>
            <td>{{ i['email'] }}</td>
            <td>{{ i['turma'] }}</td>
            <td>
              {% if i['status']=='Aceita' %}
                <span class="badge aceita">Aceita</span>
              {% elif i['status']=='Negada' %}
                <span class="badge negada">Negada</span>
              {% elif i['status']=='Lista de Espera' %}
                <span class="badge espera">Lista de Espera</span> {% if i['posicao_espera'] %}(#{{i['posicao_espera']}}){% endif %}
              {% else %}
                <span class="badge pendente">Pendente</span>
              {% endif %}
            </td>
            <td>
              <form style="margin-bottom:6px" method="POST" action="{{ url_for('aceitar_inscricao', inscricao_id=i['id']) }}">
                <button class="btn" type="submit">Aceitar</button>
              </form>
              <form style="margin-bottom:6px" method="POST" action="{{ url_for('lista_espera_inscricao', inscricao_id=i['id']) }}">
                <input name="posicao_espera" type="number" min="1" placeholder="Posição">
                <button class="btn warn" type="submit">Lista espera</button>
              </form>
              <form method="POST" action="{{ url_for('negar_inscricao', inscricao_id=i['id']) }}">
                <input name="motivo" placeholder="Motivo (opcional)">
                <button class="btn danger" type="submit">Negar</button>
              </form>
            </td>
          </tr>
          {% else %}
          <tr><td colspan="6">Sem inscritos.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    """
    return render_page(html, "Inscritos - Admin", "admin_inscritos", rows=rows)


@app.route("/admin/aceitar/<int:inscricao_id>", methods=["POST"])
@admin_required
def aceitar_inscricao(inscricao_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE inscricoes
                SET status='Aceita',
                    posicao_espera=NULL,
                    motivo_negacao=NULL,
                    acesso_aluno_ativo=TRUE,
                    decidido_por=%s,
                    data_decisao=%s
                WHERE id=%s
            """, (session.get("admin_email"), now_str(), inscricao_id))
        conn.commit()

    flash(f"Inscrição #{inscricao_id} aceita.", "ok")
    return redirect(url_for("admin_inscritos"))


@app.route("/admin/lista-espera/<int:inscricao_id>", methods=["POST"])
@admin_required
def lista_espera_inscricao(inscricao_id):
    pos = request.form.get("posicao_espera", "").strip()
    if not pos.isdigit() or int(pos) < 1:
        flash("Posição inválida.", "erro")
        return redirect(url_for("admin_inscritos"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE inscricoes
                SET status='Lista de Espera',
                    posicao_espera=%s,
                    acesso_aluno_ativo=FALSE,
                    decidido_por=%s,
                    data_decisao=%s
                WHERE id=%s
            """, (int(pos), session.get("admin_email"), now_str(), inscricao_id))
            cur.execute("UPDATE alunos_users SET ativo=FALSE WHERE inscricao_id=%s", (inscricao_id,))
        conn.commit()

    flash(f"Inscrição #{inscricao_id} em lista de espera.", "ok")
    return redirect(url_for("admin_inscritos"))


@app.route("/admin/negar/<int:inscricao_id>", methods=["POST"])
@admin_required
def negar_inscricao(inscricao_id):
    motivo = request.form.get("motivo", "").strip()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE inscricoes
                SET status='Negada',
                    posicao_espera=NULL,
                    acesso_aluno_ativo=FALSE,
                    motivo_negacao=%s,
                    decidido_por=%s,
                    data_decisao=%s
                WHERE id=%s
            """, (motivo, session.get("admin_email"), now_str(), inscricao_id))
            cur.execute("UPDATE alunos_users SET ativo=FALSE WHERE inscricao_id=%s", (inscricao_id,))
        conn.commit()

    flash(f"Inscrição #{inscricao_id} negada.", "ok")
    return redirect(url_for("admin_inscritos"))


@app.route("/admin/postagens", methods=["GET", "POST"])
@admin_required
def admin_postagens():
    if request.method == "POST":
        txt = request.form.get("conteudo", "").strip()
        if txt:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO postagens (conteudo, autor_email, criado_em, ativo)
                        VALUES (%s, %s, %s, TRUE)
                    """, (txt, session.get("admin_email"), now_str()))
                conn.commit()
            flash("Postagem publicada.", "ok")
        else:
            flash("Digite uma mensagem.", "erro")
        return redirect(url_for("admin_postagens"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.*, COALESCE(a.nome, p.autor_email) AS autor_nome
                FROM postagens p
                LEFT JOIN admin_users a ON a.email = p.autor_email
                WHERE p.ativo=TRUE
                ORDER BY p.id DESC
            """)
            posts = cur.fetchall()

    html = """
    <div class="card">
      <h2>Postagens</h2>
      <form method="POST">
        <label>Mensagem</label>
        <textarea name="conteudo" required></textarea>
        <button class="btn" type="submit">Publicar</button>
      </form>
    </div>

    <div class="card">
      {% for p in posts %}
      <div class="post">
        <small><strong>{{ p['autor_nome'] }}</strong> • {{ p['criado_em'] }}</small>
        <p>{{ p['conteudo'] }}</p>
      </div>
      {% else %}
      <p>Sem postagens.</p>
      {% endfor %}
    </div>
    """
    return render_page(html, "Postagens Admin", "admin_postagens", posts=posts)


# ---------------- ALUNO ---------------- #

@app.route("/aluno/primeiro-acesso", methods=["GET", "POST"])
def aluno_primeiro_acesso():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        cpf = re.sub(r"\D", "", request.form.get("cpf", "").strip())
        senha = request.form.get("senha", "").strip()
        confirmar = request.form.get("confirmar_senha", "").strip()

        if len(senha) < 6:
            flash("Senha deve ter pelo menos 6 caracteres.", "erro")
            return redirect(url_for("aluno_primeiro_acesso"))
        if senha != confirmar:
            flash("Confirmação de senha não confere.", "erro")
            return redirect(url_for("aluno_primeiro_acesso"))

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM inscricoes
                    WHERE email=%s AND cpf=%s
                    ORDER BY id DESC
                    LIMIT 1
                """, (email, cpf))
                ins = cur.fetchone()

                if not ins:
                    flash("Inscrição não encontrada.", "erro")
                    return redirect(url_for("aluno_primeiro_acesso"))

                if ins["status"] != "Aceita" or not ins["acesso_aluno_ativo"]:
                    flash("Acesso indisponível. Verifique o status da inscrição.", "erro")
                    return redirect(url_for("consulta"))

                cur.execute("SELECT id FROM alunos_users WHERE inscricao_id=%s", (ins["id"],))
                exists = cur.fetchone()
                if exists:
                    flash("Conta já criada. Faça login.", "ok")
                    return redirect(url_for("aluno_login"))

                cur.execute("""
                    INSERT INTO alunos_users (inscricao_id, email, cpf, nome, senha_hash, ativo, criado_em)
                    VALUES (%s, %s, %s, %s, %s, TRUE, %s)
                """, (
                    ins["id"],
                    ins["email"],
                    ins["cpf"],
                    ins["nome"],
                    generate_password_hash(senha),
                    now_str()
                ))
            conn.commit()

        flash("Conta criada com sucesso.", "ok")
        return redirect(url_for("aluno_login"))

    html = """
    <div class="card">
      <h2>Primeiro acesso do aluno</h2>
      <form method="POST">
        <label>E-mail da inscrição</label><input type="email" name="email" required>
        <label>CPF da inscrição</label><input name="cpf" required>
        <label>Senha</label><input type="password" name="senha" required>
        <label>Confirmar senha</label><input type="password" name="confirmar_senha" required>
        <button class="btn" type="submit">Criar conta</button>
      </form>
    </div>
    """
    return render_page(html, "Primeiro acesso", "aluno_primeiro")


@app.route("/aluno/login", methods=["GET", "POST"])
def aluno_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "").strip()

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM alunos_users WHERE email=%s AND ativo=TRUE", (email,))
                aluno = cur.fetchone()

        if not aluno or not check_password_hash(aluno["senha_hash"], senha):
            flash("E-mail ou senha inválidos.", "erro")
            return redirect(url_for("aluno_login"))

        session["aluno_autenticado"] = True
        session["aluno_email"] = aluno["email"]
        session["aluno_nome"] = aluno["nome"]
        flash("Login realizado.", "ok")
        return redirect(url_for("aluno_dashboard"))

    html = """
    <div class="card">
      <h2>Login aluno</h2>
      <form method="POST">
        <label>E-mail</label><input type="email" name="email" required>
        <label>Senha</label><input type="password" name="senha" required>
        <button class="btn" type="submit">Entrar</button>
      </form>
    </div>
    """
    return render_page(html, "Login Aluno", "aluno_login")


@app.route("/aluno/logout")
def aluno_logout():
    session.pop("aluno_autenticado", None)
    session.pop("aluno_email", None)
    session.pop("aluno_nome", None)
    flash("Logout realizado.", "ok")
    return redirect(url_for("aluno_login"))


@app.route("/aluno")
@aluno_required
def aluno_dashboard():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.*, COALESCE(a.nome, p.autor_email) AS autor_nome
                FROM postagens p
                LEFT JOIN admin_users a ON a.email = p.autor_email
                WHERE p.ativo=TRUE
                ORDER BY p.id DESC
            """)
            posts = cur.fetchall()

    html = """
    <div class="card"><h2>Mural do aluno</h2></div>
    <div class="card">
      {% for p in posts %}
        <div class="post">
          <small><strong>{{ p['autor_nome'] }}</strong> • {{ p['criado_em'] }}</small>
          <p>{{ p['conteudo'] }}</p>
        </div>
      {% else %}
        <p>Sem postagens ainda.</p>
      {% endfor %}
    </div>
    """
    return render_page(html, "Mural", "aluno_dash", posts=posts)


@app.route("/aluno/config", methods=["GET", "POST"])
@aluno_required
def aluno_config():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM alunos_users WHERE email=%s AND ativo=TRUE", (session.get("aluno_email"),))
            aluno = cur.fetchone()

            if not aluno:
                flash("Aluno não encontrado.", "erro")
                return redirect(url_for("aluno_logout"))

            if request.method == "POST":
                nome = request.form.get("nome", "").strip()
                senha_atual = request.form.get("senha_atual", "").strip()
                nova = request.form.get("nova_senha", "").strip()
                conf = request.form.get("confirmar_senha", "").strip()

                if not nome:
                    flash("Nome obrigatório.", "erro")
                    return redirect(url_for("aluno_config"))

                if senha_atual or nova or conf:
                    if not check_password_hash(aluno["senha_hash"], senha_atual):
                        flash("Senha atual incorreta.", "erro")
                        return redirect(url_for("aluno_config"))
                    if len(nova) < 6:
                        flash("Nova senha muito curta.", "erro")
                        return redirect(url_for("aluno_config"))
                    if nova != conf:
                        flash("Confirmação não confere.", "erro")
                        return redirect(url_for("aluno_config"))

                    cur.execute("""
                        UPDATE alunos_users
                        SET nome=%s, senha_hash=%s
                        WHERE email=%s
                    """, (nome, generate_password_hash(nova), aluno["email"]))
                else:
                    cur.execute("""
                        UPDATE alunos_users
                        SET nome=%s
                        WHERE email=%s
                    """, (nome, aluno["email"]))

                conn.commit()
                session["aluno_nome"] = nome
                flash("Configurações atualizadas.", "ok")
                return redirect(url_for("aluno_config"))

    html = """
    <div class="card">
      <h2>Configurações do aluno</h2>
      <form method="POST">
        <label>Nome</label>
        <input name="nome" value="{{ aluno['nome'] }}" required>

        <h4>Alterar senha (opcional)</h4>
        <label>Senha atual</label><input type="password" name="senha_atual">
        <label>Nova senha</label><input type="password" name="nova_senha">
        <label>Confirmar nova senha</label><input type="password" name="confirmar_senha">

        <button class="btn" type="submit">Salvar</button>
      </form>
    </div>
    """
    return render_page(html, "Config aluno", "aluno_config", aluno=aluno)


# ---------------- START ---------------- #

init_db()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)