"""Exceções de domínio: RecursoNaoEncontrado, PermissaoNegada, RegraDeNegocioViolada."""

"""Exceções de domínio da aplicação.

Conforme a arquitetura de três camadas, a camada Service nunca lança
HTTPException e não conhece códigos HTTP. Ela lança exceções de domínio,
que são capturadas e convertidas em respostas HTTP padronizadas pelo
manipulador global de exceções no FastAPI.
"""


class IntranetException(Exception):
    """Exceção base do domínio da Intranet Decós."""

    def __init__(
        self,
        mensagem: str = "Erro interno da aplicação.",
        codigo: str = "ERRO_INTERNO",
        status_code: int = 500,
    ) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo
        self.status_code = status_code


class CredenciaisInvalidas(IntranetException):
    """Lançada quando o e-mail ou a senha informados não conferem."""

    def __init__(self, mensagem: str = "E-mail ou senha incorretos.") -> None:
        super().__init__(
            mensagem=mensagem,
            codigo="CREDENCIAIS_INVALIDAS",
            status_code=401,
        )


class UsuarioInativo(IntranetException):
    """Lançada quando um usuário desativado ou desligado tenta efetuar login."""

    def __init__(self, mensagem: str = "Usuário inativo ou desligado.") -> None:
        super().__init__(
            mensagem=mensagem,
            codigo="USUARIO_INATIVO",
            status_code=403,
        )


class TokenInvalido(IntranetException):
    """Lançada quando o token JWT é inválido, expirado ou malformado."""

    def __init__(self, mensagem: str = "Token de autenticação inválido ou expirado.") -> None:
        super().__init__(
            mensagem=mensagem,
            codigo="TOKEN_INVALIDO",
            status_code=401,
        )


class TokenRevogado(IntranetException):
    """Lançada quando um refresh token na blacklist é reutilizado."""

    def __init__(self, mensagem: str = "Sessão revogada. Faça login novamente.") -> None:
        super().__init__(
            mensagem=mensagem,
            codigo="TOKEN_REVOGADO",
            status_code=401,
        )


class PermissaoNegada(IntranetException):
    """Lançada pela dependência exige('...') quando o perfil não tem a permissão requerida."""

    def __init__(
        self,
        permissao: str,
        mensagem: str | None = None,
    ) -> None:
        msg = mensagem or f"Permissão necessária não concedida: {permissao}."
        super().__init__(
            mensagem=msg,
            codigo="PERMISSAO_NEGADA",
            status_code=403,
        )
        self.permissao = permissao


class TentativasExcedidas(IntranetException):
    """Lançada quando o limite de tentativas de login é excedido (rate limit / força bruta)."""

    def __init__(
        self,
        mensagem: str = "Muitas tentativas de login. Aguarde um momento antes de tentar novamente.",
    ) -> None:
        super().__init__(
            mensagem=mensagem,
            codigo="TENTATIVAS_EXCEDIDAS",
            status_code=429,
        )


class RecursoNaoEncontrado(IntranetException):
    """Lançada quando uma entidade solicitada não existe."""

    def __init__(
        self,
        entidade: str = "Recurso",
        identificador: str | int | None = None,
    ) -> None:
        msg = (
            f"{entidade} com identificador '{identificador}' não foi encontrado."
            if identificador is not None
            else f"{entidade} não encontrado."
        )
        super().__init__(
            mensagem=msg,
            codigo="RECURSO_NAO_ENCONTRADO",
            status_code=404,
        )
        self.entidade = entidade
        self.identificador = identificador


class RegraDeNegocioViolada(IntranetException):
    """Lançada quando uma regra de negócio específica é violada."""

    def __init__(
        self,
        mensagem: str,
        codigo: str = "REGRA_NEGOCIO_VIOLADA",
    ) -> None:
        super().__init__(
            mensagem=mensagem,
            codigo=codigo,
            status_code=400,
        )
