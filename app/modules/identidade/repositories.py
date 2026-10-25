"""Camada Repository para persistência e consulta de usuários e auditoria.

Executa consultas e gravações no banco de dados via SQLAlchemy 2.0.
Não decide regras de negócio e não emite commits por conta própria.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identidade.models import Auditoria, Usuario


class UsuarioRepository:
    """Repositório de acesso a dados da entidade Usuario e Auditoria."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def obter_por_email(self, email: str) -> Usuario | None:
        """Localiza um usuário através de seu e-mail corporativo."""
        email_limpo = email.lower().strip()
        stmt = select(Usuario).where(Usuario.email == email_limpo)
        return self.session.scalars(stmt).first()

    def obter_por_id(self, usuario_id: int) -> Usuario | None:
        """Localiza um usuário através do seu identificador numérico (ID)."""
        return self.session.get(Usuario, usuario_id)

    def atualizar_ultimo_login(self, usuario: Usuario, quando: datetime) -> None:
        """Atualiza o registro de timestamp do último acesso bem-sucedido."""
        usuario.ultimo_login_em = quando

    def registrar_auditoria(
        self,
        entidade: str,
        entidade_id: int,
        acao: str,
        id_usuario: int | None = None,
        request_id: str | None = None,
        ip_origem: str | None = None,
        diff: str | None = None,
    ) -> Auditoria:
        """Registra uma entrada na tabela de auditoria (ex: LOGIN, LOGIN_FALHA)."""
        auditoria = Auditoria(
            entidade=entidade,
            entidade_id=entidade_id,
            acao=acao,
            id_usuario=id_usuario,
            request_id=request_id,
            ip_origem=ip_origem,
            diff=diff,
        )
        self.session.add(auditoria)
        return auditoria

    def criar(self, usuario: Usuario) -> Usuario:
        """Adiciona um novo usuário na sessão do banco de dados."""
        self.session.add(usuario)
        return usuario
