from api.db import SessionLocal, Medico
from api.index import hash_password
from datetime import datetime, timedelta

def promote_admin(email, password):
    db = SessionLocal()
    try:
        medico = db.query(Medico).filter(Medico.email == email).first()
        if medico:
            print(f"Usuário {email} encontrado. Promovendo a admin...")
            medico.is_admin = True
            medico.is_active = True
            if password:
                medico.password_hash = hash_password(password)
            medico.subscription_expires_at = datetime.utcnow() + timedelta(days=3650) # 10 anos de acesso
            db.commit()
            print("Sucesso!")
        else:
            print(f"Usuário {email} não encontrado. Criando novo admin...")
            expires_at = datetime.utcnow() + timedelta(days=3650)
            novo_admin = Medico(
                nome="Admin Due",
                email=email,
                password_hash=hash_password(password),
                crm="000000",
                uf_crm="SP",
                is_active=True,
                is_admin=True,
                subscription_expires_at=expires_at
            )
            db.add(novo_admin)
            db.commit()
            print("Admin criado com sucesso!")
    finally:
        db.close()

if __name__ == "__main__":
    promote_admin("duefioravantisaudedigital@gmail.com", "Atestt@26")
