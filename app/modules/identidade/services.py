"""Camada Service: Regras de negócio de autenticação, rotação de tokens e auditoria.

Controla a transação, orquestra repositórios e serviços de infraestrutura (Redis).
Não depende de Request/Response ou códigos HTTP e lança apenas exceções de domínio.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.permissoes import obter_permissoes_usuario
from app.core.redis import (
    adicionar_blacklist,
    esta_na_blacklist,
    limpar_falhas_login,
    registrar_falha_login,
    registrar_tentativa_login,
)
from app.core.security import (
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
    verificar_senha,
)
from app.modules.identidade.models import Usuario
from app.modules.identidade.repositories import UsuarioRepository
from app.modules.identidade.schemas import (
    SetorResumo,
    TokenResponse,
    UsuarioOut,
)
from app.shared.exceptions import (
    CredenciaisInvalidas,
    TentativasExcedidas,
    TokenRevogado,
    UsuarioInativo,
)

settings = get_settings()


class IdentidadeService:
    """Regras de negócio de autenticação e gestão de sessão de colaboradores."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = UsuarioRepository(session)

    def _montar_usuario_out(self, usuario: Usuario) -> UsuarioOut:
        """Serializa o modelo Usuario no schema UsuarioOut com suas permissões associadas."""
        setor_dto = None
        if usuario.setor:
            setor_dto = SetorResumo.model_validate(usuario.setor)

        return UsuarioOut(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            role=usuario.role,
            cargo=usuario.cargo,
            ramal=usuario.ramal,
            foto_object_key=usuario.foto_object_key,
            id_setor=usuario.id_setor,
            setor=setor_dto,
            data_nascimento=usuario.data_nascimento,
            bio=usuario.bio,
            ultimo_login_em=usuario.ultimo_login_em,
            permissoes=obter_permissoes_usuario(usuario.role),
        )

    def autenticar(
        self,
        email: str,
        senha: str,
        ip_origem: str | None = None,
        request_id: str | None = None,
    ) -> tuple[TokenResponse, str, int]:
        """Autentica o usuário pelo e-mail e senha com Argon2id.

        Aplica proteção contra força bruta (rate limiting), validação de status
        ativo, atualização do último login e gravação da auditoria.

        Retorna:
            tuple[TokenResponse, refresh_token, segundos_expiracao_refresh]
        """
        identificador_ip = ip_origem or "desconhecido"
        email_normalizado = email.lower().strip()

        # 1. Rate limiting: 5 tentativas/min por IP e por e-mail
        tentativas_ip = registrar_tentativa_login(f"ip:{identificador_ip}")
        tentativas_email = registrar_tentativa_login(f"email:{email_normalizado}")
        if (
            tentativas_ip > settings.LOGIN_MAX_TENTATIVAS
            or tentativas_email > settings.LOGIN_MAX_TENTATIVAS
        ):
            raise TentativasExcedidas(
                "Muitas tentativas de login em curto intervalo. Aguarde 1 minuto."
            )

        # 2. Busca do usuário pelo e-mail corporativo
        usuario = self.repository.obter_por_email(email_normalizado)

        # 3. Validação de credenciais com Argon2id
        senha_valida = False
        if usuario:
            senha_valida = verificar_senha(senha, usuario.senha_hash)

        if not usuario or not senha_valida:
            # Incrementa contadores de falhas consecutivas
            falhas = registrar_falha_login(f"email:{email_normalizado}")
            registrar_falha_login(f"ip:{identificador_ip}")

            # Registra auditoria de falha de login
            self.repository.registrar_auditoria(
                entidade="usuarios",
                entidade_id=usuario.id if usuario else 0,
                acao="LOGIN_FALHA",
                id_usuario=usuario.id if usuario else None,
                request_id=request_id,
                ip_origem=ip_origem,
                diff=f'{{"motivo": "credenciais_invalidas", "falhas_consecutivas": {falhas}}}',
            )
            self.session.commit()

            if falhas >= 10:
                raise TentativasExcedidas(
                    "Acesso temporariamente bloqueado por 10 falhas consecutivas. "
                    "Aguarde 15 minutos ou contate o suporte de TI."
                )

            raise CredenciaisInvalidas("E-mail ou senha incorretos.")

        # 4. Verificação de status do usuário (ativo e não desligado)
        if not usuario.ativo or usuario.desligado_em is not None:
            raise UsuarioInativo(
                "Colaborador inativo ou desligado. Acesso à intranet não autorizado."
            )

        # 5. Sucesso: limpa contador de falhas
        limpar_falhas_login(f"email:{email_normalizado}")
        limpar_falhas_login(f"ip:{identificador_ip}")

        # 6. Atualização de último login e registro de auditoria
        agora = datetime.now(timezone.utc)
        self.repository.atualizar_ultimo_login(usuario, agora)
        self.repository.registrar_auditoria(
            entidade="usuarios",
            entidade_id=usuario.id,
            acao="LOGIN",
            id_usuario=usuario.id,
            request_id=request_id,
            ip_origem=ip_origem,
        )
        self.session.commit()
        self.session.refresh(usuario)

        # 7. Geração de tokens: Access Token (15m) e Refresh Token (7d)
        access_token = criar_access_token({
            "sub": str(usuario.id),
            "email": usuario.email,
            "nome": usuario.nome,
            "role": usuario.role,
        })
        refresh_token, _jti, exp_segundos = criar_refresh_token(usuario.id)

        usuario_out = self._montar_usuario_out(usuario)
        resposta_token = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_MINUTOS * 60,
            usuario=usuario_out,
        )
        return resposta_token, refresh_token, exp_segundos

    def renovar_sessao(self, token_antigo: str) -> tuple[TokenResponse, str, int]:
        """Rotaciona o refresh token: invalida o anterior e emite um novo par de tokens.

        O token antigo vai para a blacklist no Redis com o tempo de vida restante.
        """
        payload = decodificar_token(token_antigo, tipo_esperado="refresh")
        jti = payload.get("jti")
        sub = payload.get("sub")
        exp = payload.get("exp")

        if not jti or not sub or not exp:
            raise TokenRevogado("Token de atualização incompleto.")

        # Verifica se o refresh token já foi revogado
        if esta_na_blacklist(jti):
            raise TokenRevogado("Sessão revogada ou já renovada. Faça login novamente.")

        # Invalida o token anterior adicionando-o à blacklist no Redis
        agora_timestamp = datetime.now(timezone.utc).timestamp()
        segundos_restantes = int(exp - agora_timestamp)
        if segundos_restantes > 0:
            adicionar_blacklist(jti, segundos_restantes)

        # Valida existência e status do usuário
        usuario = self.repository.obter_por_id(int(sub))
        if not usuario or not usuario.ativo or usuario.desligado_em is not None:
            raise UsuarioInativo("Usuário não encontrado ou inativo.")

        # Emite novo par com rotação de segredo
        novo_access_token = criar_access_token({
            "sub": str(usuario.id),
            "email": usuario.email,
            "nome": usuario.nome,
            "role": usuario.role,
        })
        novo_refresh_token, _novo_jti, novo_exp_segundos = criar_refresh_token(usuario.id)

        usuario_out = self._montar_usuario_out(usuario)
        resposta_token = TokenResponse(
            access_token=novo_access_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_MINUTOS * 60,
            usuario=usuario_out,
        )
        return resposta_token, novo_refresh_token, novo_exp_segundos

    def encerrar_sessao(self, refresh_token: str | None) -> None:
        """Invalida a sessão atual adicionando o refresh token à blacklist no Redis."""
        if not refresh_token:
            return

        try:
            payload = decodificar_token(refresh_token, tipo_esperado="refresh")
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                agora_timestamp = datetime.now(timezone.utc).timestamp()
                segundos_restantes = int(exp - agora_timestamp)
                if segundos_restantes > 0:
                    adicionar_blacklist(jti, segundos_restantes)
        except Exception:
            # No logout, erros ao decodificar token inválido/expirado são silenciados
            pass

    def obter_perfil(self, usuario: Usuario) -> UsuarioOut:
        """Retorna as informações completas e permissões do usuário conectado."""
        return self._montar_usuario_out(usuario)
