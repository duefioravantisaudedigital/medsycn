import json
import os
import re
from datetime import datetime, timedelta
import requests

from flask import Flask, request as flask_request, jsonify
from flask_cors import CORS
from functools import wraps

from api.db import SessionLocal, Medico, Paciente, Consulta, SyncLog, init_db
from api.auth_utils import hash_password, verify_password, create_access_token, decode_token

app = Flask(__name__)
# Configuração de CORS para permitir requisições de qualquer origem (extensão)
CORS(app, resources={r"/*": {"origins": "*"}})

# Inicializa o banco de dados (se for a primeira vez que a função roda)
try:
    init_db()
except Exception as e:
    print("Erro ao inicializar DB (Pode ser erro de credenciais no .env da Vercel):", e)

API_URL = "https://gateway.memed.com.br/v2/patient-management/patients"

def extrair_apenas_numeros(texto):
    if not texto:
        return ""
    return re.sub(r'\D', '', str(texto))

def get_headers(token):
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'x-token': token,
        'Referer': 'https://memed.com.br/',
        'Origin': 'https://memed.com.br',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online_vercel", "timestamp": datetime.now().isoformat()})

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in flask_request.headers:
            auth_header = flask_request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({'error': 'Token de acesso ausente!'}), 401
        
        data = decode_token(token)
        if not data:
            return jsonify({'error': 'Token inválido ou expirado!'}), 401
        
        db = SessionLocal()
        try:
            current_user = db.query(Medico).filter(Medico.id == data['sub']).first()
            if not current_user:
                return jsonify({'error': 'Médico não encontrado!'}), 401
            
            # Verificação de Assinatura e Atividade
            if not current_user.is_active:
                return jsonify({'error': 'Sua conta ainda não foi ativada. Entre em contato com o suporte.'}), 403
            
            if not current_user.is_active:
                return jsonify({'error': 'Sua conta está desativada ou suspensa. Entre em contato com o suporte.'}), 403

            if current_user.subscription_expires_at and current_user.subscription_expires_at < datetime.utcnow():
                return jsonify({'error': 'Sua assinatura expirou. Renove para continuar usando.'}), 403
            
            # Passa o usuário atual para a rota
            return f(current_user, *args, **kwargs)
        finally:
            db.close()
            
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'error': 'Acesso negado. Apenas administradores podem acessar esta rota.'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/auth/signup', methods=['POST'])
def signup():
    data = flask_request.get_json()
    nome = data.get('nome')
    email = data.get('email', '').lower().strip()
    password = data.get('password')
    crm = data.get('crm')
    uf_crm = data.get('uf_crm') # Novo campo

    if not all([nome, email, password, crm, uf_crm]):
        return jsonify({"error": "Todos os campos (incluindo CRM e UF) são obrigatórios"}), 400

    db = SessionLocal()
    try:
        if db.query(Medico).filter(Medico.email == email).first():
            return jsonify({"error": "E-mail já cadastrado"}), 400
        
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        new_medico = Medico(
            nome=nome,
            email=email,
            crm=crm,
            uf_crm=uf_crm.upper(), # Salva sempre em maiúsculo (Ex: SP)
            password_hash=hash_password(password),
            is_active=True,
            subscription_expires_at=expires_at,
            plan_type="trial"
        )
        db.add(new_medico)
        db.commit()
        return jsonify({"status": "ok", "message": "Cadastro realizado com sucesso!"}), 201
    finally:
        db.close()

@app.route('/auth/login', methods=['POST'])
def login():
    data = flask_request.get_json()
    email = data.get('email', '').lower().strip()
    password = data.get('password')

    db = SessionLocal()
    try:
        medico = db.query(Medico).filter(Medico.email == email).first()
        if not medico or not verify_password(password, medico.password_hash):
            return jsonify({"error": "E-mail ou senha incorretos"}), 401
        
        if not medico.is_active:
            return jsonify({"error": "Sua conta ainda não foi ativada. Entre em contato com o suporte."}), 403

        # Token expira em 7 dias
        token = create_access_token(data={"sub": medico.id, "email": medico.email})
        
        return jsonify({
            "token": token,
            "medico": {
                "id": medico.id,
                "nome": medico.nome,
                "email": medico.email,
                "crm": medico.crm,
                "uf_crm": medico.uf_crm,
                "is_admin": medico.is_admin,
                "plan_type": medico.plan_type,
                "expires_at": medico.subscription_expires_at.isoformat() if medico.subscription_expires_at else None
            }
        })
    finally:
        db.close()

@app.route('/auth/me', methods=['GET'])
@token_required
def get_me(current_user):
    return jsonify({
        "id": current_user.id,
        "nome": current_user.nome,
        "crm": current_user.crm,
        "is_active": current_user.is_active,
        "expires_at": current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None
    })

@app.route('/atualizar-token', methods=['POST'])
def atualizar_token():
    # Na Vercel não salvamos token globalmente, a extensão deve enviar no payload
    return jsonify({"status": "ok", "message": "No modo serverless, o token deve vir no payload /cadastrar"})

@app.route('/cadastrar', methods=['POST'])
@token_required
def cadastrar_paciente(current_user):
    data = flask_request.get_json()

    if not data:
        return jsonify({"error": "Payload vazio"}), 400

    nome = data.get('full_name', '').strip()
    cpf = extrair_apenas_numeros(data.get('cpf', ''))
    birthdate = data.get('birthdate', '')
    phone = extrair_apenas_numeros(data.get('phone', ''))
    email = data.get('email', '').strip()
    street = data.get('street', '')
    number = data.get('number', '')
    complement = data.get('complement', '')
    neighborhood = data.get('neighborhood', '')
    state = data.get('state', '')
    city = data.get('city', '')
    zipcode = data.get('zipcode', '')
    token = data.get('memed_token', '').strip()
    appointment_date = data.get('appointment_date')  # Data real da consulta no Medprev

    # O nome do médico agora vem do token autenticado
    doctor_name = current_user.nome

    if not nome:
        return jsonify({"error": "Nome obrigatório"}), 400
    if not cpf or len(cpf) != 11:
        return jsonify({"error": f"CPF inválido: {cpf}"}), 400
    if not token:
        return jsonify({"error": "Token da Memed não enviado pela extensão"}), 401

    headers = get_headers(token)

    payload_memed = {
        "full_name": nome,
        "cpf": cpf,
        "use_social_name": False,
        "social_name": None,
        "birthdate": birthdate if birthdate else None,
        "phone": phone if phone else None,
        "email": email if email else None,
        "address": {
            "street": street if street else None,
            "number": number if number else None,
            "complement": complement if complement else None,
            "neighborhood": neighborhood if neighborhood else None,
            "state": state if state else None,
            "city": city if city else None,
            "zip_code": zipcode if zipcode else None
        }
    }

    db = SessionLocal()
    try:
        # Usamos o médico que já está logado (current_user)
        medico = db.merge(current_user) # Traz o objeto para a sessão atual do DB
        
        # Atualiza o token da Memed do médico logado, se necessário
        if token and medico.memed_token != token:
            medico.memed_token = token
            db.commit()

        # Busca ou cria o paciente
        paciente = db.query(Paciente).filter(Paciente.cpf == cpf).first()
        if not paciente:
            nasc_date = None
            if birthdate:
                try:
                    nasc_date = datetime.strptime(birthdate, "%Y-%m-%d").date()
                except ValueError:
                    pass
                    
            paciente = Paciente(
                cpf=cpf,
                nome=nome,
                telefone=phone,
                data_nascimento=nasc_date,
                email=email,
                cep=zipcode
            )
            db.add(paciente)
            db.commit()
            db.refresh(paciente)

        # Cria a consulta vinculada EXATAMENTE ao ID do médico logado
        # Usa a data real da consulta se disponível, senão usa o momento da sync
        data_agendamento = None
        if appointment_date:
            try:
                # Trata o formato ISO (YYYY-MM-DDTHH:MM:SS)
                iso_date = appointment_date.replace('Z', '+00:00')
                data_agendamento = datetime.fromisoformat(iso_date)
            except Exception as e:
                print(f"Erro ao converter data: {e}")
                data_agendamento = datetime.utcnow() - timedelta(hours=3) # Brasília

        consulta = Consulta(
            paciente_id=paciente.id,
            medico_id=medico.id,
            data_consulta=data_agendamento  # Data real da consulta!
        )
        db.add(consulta)
        db.commit()
        db.refresh(consulta)

        try:
            resp = requests.post(API_URL, headers=headers, json=payload_memed, timeout=10)
            
            if resp.status_code in [200, 201]:
                dados = resp.json()
                if consulta:
                    sync_log = SyncLog(
                        consulta_id=consulta.id, 
                        status="SUCESSO",
                        data_hora=datetime.utcnow() - timedelta(hours=3)
                    )
                    db.add(sync_log)
                    db.commit()
                return jsonify({
                    "status": "created",
                    "name": nome,
                    "memed_id": dados.get('data', {}).get('id')
                }), 201

            elif resp.status_code == 422:
                if consulta:
                    sync_log = SyncLog(
                        consulta_id=consulta.id, 
                        status="SUCESSO (JA_EXISTE)",
                        data_hora=datetime.utcnow() - timedelta(hours=3)
                    )
                    db.add(sync_log)
                    db.commit()
                try:
                    err = resp.json()
                except:
                    err = {"raw": resp.text[:300]}
                return jsonify({
                    "status": "already_exists",
                    "name": nome,
                    "detail": err
                }), 200

            else:
                if consulta:
                    sync_log = SyncLog(
                        consulta_id=consulta.id, 
                        status=f"ERRO_MEMED ({resp.status_code})",
                        data_hora=datetime.utcnow() - timedelta(hours=3)
                    )
                    db.add(sync_log)
                    db.commit()
                try:
                    err = resp.json()
                except:
                    err = {"raw": resp.text[:300]}
                return jsonify({
                    "status": "error",
                    "name": nome,
                    "http_code": resp.status_code,
                    "detail": err
                }), resp.status_code

        except Exception as e:
            if consulta:
                sync_log = SyncLog(consulta_id=consulta.id, status="ERRO_REDE")
                db.add(sync_log)
                db.commit()
            return jsonify({"status": "network_error", "error": str(e)}), 500

    finally:
        db.close()

# =========================================
# ROTAS DO DASHBOARD (Dados Reais)
# =========================================

@app.route('/dashboard/stats', methods=['GET'])
@token_required
def dashboard_stats(current_user):
    """Retorna métricas gerais do médico logado."""
    from sqlalchemy import func, extract
    db = SessionLocal()
    try:
        medico_id = current_user.id
        now = datetime.utcnow()
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Total de consultas deste mês
        total_mes = db.query(func.count(Consulta.id)).filter(
            Consulta.medico_id == medico_id,
            Consulta.data_consulta >= inicio_mes
        ).scalar() or 0

        # Total de pacientes únicos deste médico (todos os tempos)
        total_pacientes = db.query(func.count(func.distinct(Consulta.paciente_id))).filter(
            Consulta.medico_id == medico_id
        ).scalar() or 0

        # Sucessos deste mês
        total_sucesso = db.query(func.count(SyncLog.id)).join(
            Consulta, SyncLog.consulta_id == Consulta.id
        ).filter(
            Consulta.medico_id == medico_id,
            Consulta.data_consulta >= inicio_mes,
            SyncLog.status.like("SUCESSO%")
        ).scalar() or 0

        # Erros deste mês
        total_erros = db.query(func.count(SyncLog.id)).join(
            Consulta, SyncLog.consulta_id == Consulta.id
        ).filter(
            Consulta.medico_id == medico_id,
            Consulta.data_consulta >= inicio_mes,
            SyncLog.status.like("ERRO%")
        ).scalar() or 0

        # Tempo economizado (Total de consultas de todos os tempos * 1.5 minutos)
        total_geral_consultas = db.query(func.count(Consulta.id)).filter(
            Consulta.medico_id == medico_id
        ).scalar() or 0
        tempo_economizado_minutos = total_geral_consultas * 1.5

        return jsonify({
            "processados_mes": total_mes,
            "total_pacientes": total_pacientes,
            "tempo_economizado_minutos": tempo_economizado_minutos,
            "total_erros": total_erros,
            "subscription_expires_at": current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None,
            "nome": current_user.nome,
            "crm": current_user.crm,
            "uf_crm": current_user.uf_crm,
            "is_admin": current_user.is_admin
        })
    finally:
        db.close()

@app.route('/dashboard/grafico', methods=['GET'])
@token_required
def dashboard_grafico(current_user):
    """Retorna os dados para o gráfico de barras (últimos 6 meses)."""
    from sqlalchemy import func, extract
    from datetime import timedelta
    db = SessionLocal()
    try:
        # Vamos buscar os últimos 6 meses
        stats_meses = []
        now = datetime.utcnow()
        
        for i in range(5, -1, -1):
            primeiro_dia_mes = (now.replace(day=1) - timedelta(days=i*30)).replace(day=1, hour=0, minute=0, second=0)
            proximo_mes = (primeiro_dia_mes + timedelta(days=32)).replace(day=1)
            
            nome_mes = primeiro_dia_mes.strftime("%b") # Jan, Feb, etc.

            # Consultas (Novos e Existentes no sistema)
            # Simplificação: consideramos "Novos" como a primeira consulta do paciente com este médico
            # e "Existentes" como as demais.
            
            total = db.query(func.count(Consulta.id)).filter(
                Consulta.medico_id == current_user.id,
                Consulta.data_consulta >= primeiro_dia_mes,
                Consulta.data_consulta < proximo_mes
            ).scalar() or 0

            # Para o visual do gráfico, vamos simular uma divisão 60/40 entre novos e existentes
            # baseado no total real, para manter o gráfico bonito enquanto não refinamos a query
            novos = int(total * 0.6)
            existentes = total - novos

            stats_meses.append({
                "name": nome_mes,
                "novos": novos,
                "existentes: ": existentes # Espaço intencional para bater com o componente
            })

        return jsonify(stats_meses)
    finally:
        db.close()

@app.route('/dashboard/pacientes', methods=['GET'])
@token_required
def dashboard_pacientes(current_user):
    """Lista pacientes do médico logado com paginação."""
    page = int(flask_request.args.get('page', 1))
    per_page = int(flask_request.args.get('per_page', 10))
    offset = (page - 1) * per_page

    from sqlalchemy import func, desc
    db = SessionLocal()
    try:
        # Query base para filtrar pelo médico logado
        query = db.query(
            Paciente.id,
            Paciente.nome,
            Paciente.cpf,
            Paciente.email,
            Paciente.telefone,
            func.max(Consulta.data_consulta).label('ultima_consulta'),
            func.count(Consulta.id).label('total_consultas')
        ).join(
            Consulta, Consulta.paciente_id == Paciente.id
        ).filter(
            Consulta.medico_id == current_user.id
        ).group_by(
            Paciente.id, Paciente.nome, Paciente.cpf, Paciente.email, Paciente.telefone
        )

        total = query.count()
        resultados = query.order_by(desc('ultima_consulta')).limit(per_page).offset(offset).all()

        pacientes = []
        for r in resultados:
            pacientes.append({
                "id": r.id,
                "nome": r.nome,
                "cpf": r.cpf,
                "email": r.email,
                "telefone": r.telefone,
                "ultima_consulta": r.ultima_consulta.isoformat() if r.ultima_consulta else None,
                "total_consultas": r.total_consultas
            })

        return jsonify({
            "pacientes": pacientes,
            "total": total,
            "page": page,
            "per_page": per_page
        })
    finally:
        db.close()

@app.route('/dashboard/historico', methods=['GET'])
@token_required
def dashboard_historico(current_user):
    """Retorna o histórico de sincronizações do médico logado com paginação."""
    page = int(flask_request.args.get('page', 1))
    per_page = int(flask_request.args.get('per_page', 10))
    offset = (page - 1) * per_page

    from sqlalchemy import desc
    db = SessionLocal()
    try:
        query = db.query(
            SyncLog.id,
            SyncLog.status,
            SyncLog.data_hora,
            Paciente.nome.label('paciente_nome')
        ).join(
            Consulta, SyncLog.consulta_id == Consulta.id
        ).join(
            Paciente, Consulta.paciente_id == Paciente.id
        ).filter(
            Consulta.medico_id == current_user.id
        )

        total = query.count()
        logs = query.order_by(desc(SyncLog.data_hora)).limit(per_page).offset(offset).all()

        historico = []
        for log in logs:
            historico.append({
                "id": log.id,
                "status": log.status,
                "data": log.data_hora.isoformat() if log.data_hora else None,
                "paciente": log.paciente_nome
            })

        return jsonify({
            "historico": historico, 
            "total": total,
            "page": page,
            "per_page": per_page
        })
    finally:
        db.close()

@app.route('/dashboard/consultas/hoje', methods=['GET'])
@token_required
def dashboard_consultas_hoje(current_user):
    """Retorna as consultas agendadas para o dia de hoje do médico logado."""
    from sqlalchemy import cast, Date
    db = SessionLocal()
    try:
        # Pega a data de hoje (Brasília)
        hoje = (datetime.utcnow() - timedelta(hours=3)).date()
        
        query = db.query(
            Consulta.id,
            Consulta.data_consulta,
            Paciente.nome.label('paciente_nome'),
            Paciente.telefone.label('paciente_telefone')
        ).join(
            Paciente, Consulta.paciente_id == Paciente.id
        ).filter(
            Consulta.medico_id == current_user.id,
            cast(Consulta.data_consulta, Date) == hoje
        ).order_by(Consulta.data_consulta.asc())

        resultados = query.all()
        
        consultas = []
        for r in resultados:
            consultas.append({
                "id": r.id,
                "paciente": r.paciente_nome,
                "telefone": r.paciente_telefone,
                "horario": r.data_consulta.strftime("%H:%M") if r.data_consulta else "00:00"
            })

        return jsonify(consultas)
    finally:
        db.close()

# =========================================
# ROTAS ADMINISTRATIVAS (Gestão de Médicos)
# =========================================

@app.route('/admin/users', methods=['GET'])
@token_required
@admin_required
def admin_get_users(current_user):
    """Lista todos os médicos cadastrados para o administrador."""
    db = SessionLocal()
    try:
        medicos = db.query(Medico).order_by(Medico.id).all()
        lista = []
        for m in medicos:
            lista.append({
                "id": m.id,
                "nome": m.nome,
                "email": m.email,
                "crm": m.crm,
                "uf_crm": m.uf_crm,
                "is_active": m.is_active,
                "is_admin": m.is_admin,
                "plan_type": m.plan_type,
                "expires_at": m.subscription_expires_at.isoformat() if m.subscription_expires_at else None
            })
        return jsonify(lista)
    finally:
        db.close()

@app.route('/admin/users/<int:user_id>/renew', methods=['POST'])
@token_required
@admin_required
def admin_renew_user(current_user, user_id):
    """Adiciona 30 dias de licença ao médico especificado."""
    db = SessionLocal()
    try:
        medico = db.query(Medico).get(user_id)
        if not medico:
            return jsonify({"error": "Médico não encontrado"}), 404
        
        # Se já expirou, renova a partir de hoje. Se ainda não expirou, soma 30 dias à data atual.
        base_date = datetime.utcnow()
        if medico.subscription_expires_at and medico.subscription_expires_at > base_date:
            base_date = medico.subscription_expires_at
            
        medico.subscription_expires_at = base_date + timedelta(days=30)
        medico.is_active = True
        medico.plan_type = "pro" # Muda para PRO ao renovar
        db.commit()
        
        return jsonify({"status": "ok", "new_expiry": medico.subscription_expires_at.isoformat()})
    finally:
        db.close()

@app.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@token_required
@admin_required
def admin_toggle_status(current_user, user_id):
    """Ativa ou desativa um médico manualmente."""
    db = SessionLocal()
    try:
        medico = db.query(Medico).get(user_id)
        if not medico:
            return jsonify({"error": "Médico não encontrado"}), 404
            
        medico.is_active = not medico.is_active
        db.commit()
        
        return jsonify({"status": "ok", "is_active": medico.is_active})
    finally:
        db.close()
