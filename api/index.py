import json
import os
import re
from datetime import datetime
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
            
            if current_user.subscription_expires_at and current_user.subscription_expires_at < datetime.utcnow():
                return jsonify({'error': 'Sua assinatura expirou. Renove para continuar usando.'}), 403
            
            # Passa o usuário atual para a rota
            return f(current_user, *args, **kwargs)
        finally:
            db.close()
            
    return decorated

@app.route('/auth/signup', methods=['POST'])
def signup():
    data = flask_request.get_json()
    email = data.get('email', '').lower().strip()
    password = data.get('password')
    nome = data.get('nome')
    crm = data.get('crm')

    if not email or not password or not nome:
        return jsonify({"error": "E-mail, senha e nome são obrigatórios"}), 400

    db = SessionLocal()
    try:
        if db.query(Medico).filter(Medico.email == email).first():
            return jsonify({"error": "E-mail já cadastrado"}), 400
        
        new_medico = Medico(
            email=email,
            nome=nome,
            crm=crm,
            password_hash=hash_password(password),
            is_active=False # Nasce inativo conforme o modelo híbrido
        )
        db.add(new_medico)
        db.commit()
        return jsonify({"status": "ok", "message": "Cadastro realizado! Aguarde a ativação da sua conta."}), 201
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
                "crm": medico.crm,
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
        medico = None
        if doctor_name:
            medico = db.query(Medico).filter(Medico.nome == doctor_name).first()
            if not medico:
                medico = Medico(nome=doctor_name, memed_token=token)
                db.add(medico)
                db.commit()
                db.refresh(medico)
            elif token and medico.memed_token != token:
                # Atualiza o token do médico caso tenha mudado
                medico.memed_token = token
                db.commit()

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

        consulta = None
        if medico and paciente:
            consulta = Consulta(paciente_id=paciente.id, medico_id=medico.id)
            db.add(consulta)
            db.commit()
            db.refresh(consulta)

        try:
            resp = requests.post(API_URL, headers=headers, json=payload_memed, timeout=10)
            
            if resp.status_code in [200, 201]:
                dados = resp.json()
                if consulta:
                    sync_log = SyncLog(consulta_id=consulta.id, status="SUCESSO")
                    db.add(sync_log)
                    db.commit()
                return jsonify({
                    "status": "created",
                    "name": nome,
                    "memed_id": dados.get('data', {}).get('id')
                }), 201

            elif resp.status_code == 422:
                if consulta:
                    sync_log = SyncLog(consulta_id=consulta.id, status="SUCESSO (JA_EXISTE)")
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
                    sync_log = SyncLog(consulta_id=consulta.id, status=f"ERRO_MEMED ({resp.status_code})")
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
