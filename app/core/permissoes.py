"""Matriz e dependências de verificação de permissões por perfil (Requisito RD002).

Os papéis são funcionais por departamento conforme especificado no PROJETO.md (Seção 8):
- COLABORADOR: Consultar feed, POPs, FAQ, ramais e interagir socialmente.
- RH: Tudo de colaborador + gerenciar setores (RF014), ramais (RF015) e usuários (RF016).
- MARKETING: Tudo de colaborador + gerenciar avisos (RF012), eventos (RF013), fixação (RF008)
  e categorias.
- ADMIN: Acesso irrestrito a todas as funções ('*'), incluindo moderação, FAQ (RF017),
  documentos (RF018) e definição de papéis (RD002).

A regra de negócio exige que os endpoints declarem `exige('acao')`, sem espalhar
`if usuario.role in (...)` pelas rotas.
"""

from fastapi import Depends
from fastapi.params import Depends as DependsParam

from app.core.security import obter_usuario_atual
from app.modules.identidade.models import Usuario
from app.shared.exceptions import PermissaoNegada


class Permissao:
    """Identificadores de permissão granular conforme Seção 8.1 do PROJETO.md."""

    # Ações comuns (Colaborador, RH, Marketing, Admin)
    CONTEUDO_CRIAR = "conteudo:criar"
    CONTEUDO_PROPRIO = "conteudo:proprio"
    DENUNCIA_CRIAR = "denuncia:criar"

    # Ações específicas de RH
    SETOR_GERENCIAR = "setor:gerenciar"
    RAMAL_GERENCIAR = "ramal:gerenciar"
    USUARIO_GERENCIAR = "usuario:gerenciar"

    # Ações específicas de Marketing
    AVISO_GERENCIAR = "aviso:gerenciar"
    EVENTO_GERENCIAR = "evento:gerenciar"
    PUBLICACAO_FIXAR = "publicacao:fixar"
    CATEGORIA_GERENCIAR = "categoria:gerenciar"

    # Ações exclusivas de Administração (RF017, RF018, Moderação, RD002)
    FAQ_GERENCIAR = "faq:gerenciar"
    DOCUMENTO_GERENCIAR = "documento:gerenciar"
    DENUNCIA_RESOLVER = "denuncia:resolver"
    USUARIO_DEFINIR_PAPEL = "usuario:definir_papel"


TODAS_AS_PERMISSOES: frozenset[str] = frozenset({
    Permissao.CONTEUDO_CRIAR,
    Permissao.CONTEUDO_PROPRIO,
    Permissao.DENUNCIA_CRIAR,
    Permissao.SETOR_GERENCIAR,
    Permissao.RAMAL_GERENCIAR,
    Permissao.USUARIO_GERENCIAR,
    Permissao.AVISO_GERENCIAR,
    Permissao.EVENTO_GERENCIAR,
    Permissao.PUBLICACAO_FIXAR,
    Permissao.CATEGORIA_GERENCIAR,
    Permissao.FAQ_GERENCIAR,
    Permissao.DOCUMENTO_GERENCIAR,
    Permissao.DENUNCIA_RESOLVER,
    Permissao.USUARIO_DEFINIR_PAPEL,
})


PERMISSOES: dict[str, set[str]] = {
    "COLABORADOR": {
        Permissao.CONTEUDO_CRIAR,
        Permissao.CONTEUDO_PROPRIO,
        Permissao.DENUNCIA_CRIAR,
    },
    "RH": {
        Permissao.CONTEUDO_CRIAR,
        Permissao.CONTEUDO_PROPRIO,
        Permissao.DENUNCIA_CRIAR,
        Permissao.SETOR_GERENCIAR,
        Permissao.RAMAL_GERENCIAR,
        Permissao.USUARIO_GERENCIAR,
    },
    "MARKETING": {
        Permissao.CONTEUDO_CRIAR,
        Permissao.CONTEUDO_PROPRIO,
        Permissao.DENUNCIA_CRIAR,
        Permissao.AVISO_GERENCIAR,
        Permissao.EVENTO_GERENCIAR,
        Permissao.PUBLICACAO_FIXAR,
        Permissao.CATEGORIA_GERENCIAR,
    },
    "ADMIN": {
        "*",
    },
}


def tem_permissao(usuario_ou_role: Usuario | str, permissao: str) -> bool:
    """Verifica programaticamente se um usuário ou papel funcional possui a permissão requerida."""
    role = usuario_ou_role.role if isinstance(usuario_ou_role, Usuario) else usuario_ou_role
    concedidas = PERMISSOES.get(role, set())
    return "*" in concedidas or permissao in concedidas


def obter_permissoes_usuario(role: str) -> list[str]:
    """Retorna a lista ordenada de permissões concedidas a determinado papel funcional.

    Para o perfil ADMIN, inclui tanto o curinga '*' quanto o conjunto completo de
    permissões granulares do sistema para viabilizar validações transparentes no frontend.
    """
    concedidas = PERMISSOES.get(role, set())
    if "*" in concedidas:
        return sorted(list(concedidas | set(TODAS_AS_PERMISSOES)))
    return sorted(list(concedidas))


class PermissaoDependency(DependsParam):
    """Dependência FastAPI para validação de permissões por perfil funcional (RD002).

    Compatível com os três estilos suportados pelo FastAPI e definidos no PROJETO.md:
    1. dependencies=[exige("aviso:gerenciar")]
    2. usuario: Usuario = exige("aviso:gerenciar")
    3. usuario: Usuario = Depends(exige("aviso:gerenciar"))
    """

    def __init__(self, permissao: str) -> None:
        self.permissao = permissao

        def _verificar(
            usuario: Usuario = Depends(obter_usuario_atual),
        ) -> Usuario:
            if not tem_permissao(usuario, permissao):
                raise PermissaoNegada(permissao)
            return usuario

        self._verificar = _verificar
        super().__init__(dependency=_verificar)

    def __call__(
        self,
        usuario: Usuario = Depends(obter_usuario_atual),
    ) -> Usuario:
        return self._verificar(usuario)


def exige(permissao: str) -> PermissaoDependency:
    """Cria uma dependência FastAPI que assegura que o usuário logado possui a permissão requerida."""
    return PermissaoDependency(permissao)
