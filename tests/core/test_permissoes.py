"""Testes da matriz de permissões por perfil funcional (Evidência de aceite RD002)."""

import pytest
from fastapi.params import Depends as DependsParam

from app.core.permissoes import (
    PERMISSOES,
    TODAS_AS_PERMISSOES,
    Permissao,
    exige,
    obter_permissoes_usuario,
    tem_permissao,
)
from app.modules.identidade.models import Usuario
from app.shared.exceptions import PermissaoNegada


@pytest.mark.parametrize(
    ("role", "acao_permitida", "acao_proibida"),
    [
        ("COLABORADOR", "conteudo:criar", "aviso:gerenciar"),
        ("COLABORADOR", "conteudo:proprio", "evento:gerenciar"),
        ("COLABORADOR", "denuncia:criar", "usuario:gerenciar"),
        ("COLABORADOR", "denuncia:criar", "setor:gerenciar"),
        ("RH", "usuario:gerenciar", "aviso:gerenciar"),
        ("RH", "setor:gerenciar", "categoria:gerenciar"),
        ("RH", "ramal:gerenciar", "publicacao:fixar"),
        ("RH", "conteudo:criar", "documento:gerenciar"),
        ("MARKETING", "aviso:gerenciar", "usuario:gerenciar"),
        ("MARKETING", "evento:gerenciar", "ramal:gerenciar"),
        ("MARKETING", "publicacao:fixar", "setor:gerenciar"),
        ("MARKETING", "categoria:gerenciar", "faq:gerenciar"),
        ("ADMIN", "usuario:gerenciar", None),
        ("ADMIN", "aviso:gerenciar", None),
        ("ADMIN", "qualquer:acao:do:sistema", None),
    ],
)
def test_matriz_permissoes_rd002(
    role: str,
    acao_permitida: str,
    acao_proibida: str | None,
) -> None:
    """Valida que cada papel funcional possui estritamente as ações autorizadas."""
    concedidas = PERMISSOES.get(role, set())

    # Se ADMIN, deve ter o curinga '*'
    if "*" in concedidas:
        assert True
    else:
        assert acao_permitida in concedidas

    if acao_proibida:
        assert acao_proibida not in concedidas


def test_obter_permissoes_usuario() -> None:
    """Valida a listagem ordenada de permissões associadas aos diferentes papéis."""
    # RH
    permissoes_rh = obter_permissoes_usuario("RH")
    assert Permissao.USUARIO_GERENCIAR in permissoes_rh
    assert Permissao.SETOR_GERENCIAR in permissoes_rh
    assert Permissao.RAMAL_GERENCIAR in permissoes_rh
    assert Permissao.AVISO_GERENCIAR not in permissoes_rh

    # Colaborador
    permissoes_colab = obter_permissoes_usuario("COLABORADOR")
    assert Permissao.CONTEUDO_CRIAR in permissoes_colab
    assert Permissao.CONTEUDO_PROPRIO in permissoes_colab
    assert Permissao.DENUNCIA_CRIAR in permissoes_colab
    assert Permissao.USUARIO_GERENCIAR not in permissoes_colab

    # Marketing
    permissoes_mkt = obter_permissoes_usuario("MARKETING")
    assert Permissao.AVISO_GERENCIAR in permissoes_mkt
    assert Permissao.EVENTO_GERENCIAR in permissoes_mkt
    assert Permissao.PUBLICACAO_FIXAR in permissoes_mkt
    assert Permissao.SETOR_GERENCIAR not in permissoes_mkt

    # Admin: deve incluir '*' e a totalidade das ações granulares do sistema
    permissoes_admin = obter_permissoes_usuario("ADMIN")
    assert "*" in permissoes_admin
    assert TODAS_AS_PERMISSOES.issubset(set(permissoes_admin))
    assert Permissao.USUARIO_GERENCIAR in permissoes_admin
    assert Permissao.FAQ_GERENCIAR in permissoes_admin
    assert Permissao.DOCUMENTO_GERENCIAR in permissoes_admin

    # Papel inválido/inexistente devolve lista vazia
    assert obter_permissoes_usuario("PAPEL_INEXISTENTE") == []


def test_tem_permissao_por_papel_e_usuario(
    usuario_colaborador: Usuario,
    usuario_admin: Usuario,
    usuario_rh: Usuario,
    usuario_marketing: Usuario,
) -> None:
    """Valida a função utilitária tem_permissao aceitando string de role ou objeto Usuario."""
    # Teste por string de role
    assert tem_permissao("COLABORADOR", Permissao.CONTEUDO_CRIAR) is True
    assert tem_permissao("COLABORADOR", Permissao.AVISO_GERENCIAR) is False
    assert tem_permissao("RH", Permissao.USUARIO_GERENCIAR) is True
    assert tem_permissao("RH", Permissao.AVISO_GERENCIAR) is False
    assert tem_permissao("MARKETING", Permissao.AVISO_GERENCIAR) is True
    assert tem_permissao("MARKETING", Permissao.SETOR_GERENCIAR) is False
    assert tem_permissao("ADMIN", "qualquer:acao:arbitraria") is True

    # Teste por objeto Usuario
    assert tem_permissao(usuario_colaborador, Permissao.CONTEUDO_CRIAR) is True
    assert tem_permissao(usuario_colaborador, Permissao.USUARIO_GERENCIAR) is False
    assert tem_permissao(usuario_rh, Permissao.SETOR_GERENCIAR) is True
    assert tem_permissao(usuario_marketing, Permissao.PUBLICACAO_FIXAR) is True
    assert tem_permissao(usuario_admin, Permissao.FAQ_GERENCIAR) is True


def test_exige_autorizado(
    usuario_colaborador: Usuario,
    usuario_admin: Usuario,
    usuario_rh: Usuario,
    usuario_marketing: Usuario,
) -> None:
    """Valida que a dependência exige('...') permite acesso a usuários com permissão."""
    # Colaborador criando post
    assert exige(Permissao.CONTEUDO_CRIAR)(usuario=usuario_colaborador) == usuario_colaborador

    # RH gerenciando usuário
    assert exige(Permissao.USUARIO_GERENCIAR)(usuario=usuario_rh) == usuario_rh

    # Marketing gerenciando aviso
    assert exige(Permissao.AVISO_GERENCIAR)(usuario=usuario_marketing) == usuario_marketing

    # Admin acessando qualquer recurso
    assert exige(Permissao.FAQ_GERENCIAR)(usuario=usuario_admin) == usuario_admin
    assert exige("qualquer:permissao")(usuario=usuario_admin) == usuario_admin


def test_exige_negado(
    usuario_colaborador: Usuario,
    usuario_rh: Usuario,
    usuario_marketing: Usuario,
) -> None:
    """Valida que a dependência exige('...') lança PermissaoNegada (403) para perfis não autorizados."""
    # Colaborador tentando gerenciar aviso
    with pytest.raises(PermissaoNegada) as exc_info:
        exige(Permissao.AVISO_GERENCIAR)(usuario=usuario_colaborador)

    assert exc_info.value.status_code == 403
    assert exc_info.value.codigo == "PERMISSAO_NEGADA"
    assert exc_info.value.permissao == Permissao.AVISO_GERENCIAR

    # RH tentando fixar publicação
    with pytest.raises(PermissaoNegada):
        exige(Permissao.PUBLICACAO_FIXAR)(usuario=usuario_rh)

    # Marketing tentando gerenciar setores
    with pytest.raises(PermissaoNegada):
        exige(Permissao.SETOR_GERENCIAR)(usuario=usuario_marketing)


def test_exige_compatibilidade_fastapi() -> None:
    """Valida que exige('...') atende aos requisitos do FastAPI para injeção de dependências."""
    dep = exige("aviso:gerenciar")

    # Requisito 1: deve ser uma instância de DependsParam para uso em dependencies=[exige(...)]
    assert isinstance(dep, DependsParam)

    # Requisito 2: deve ser chamável para uso em Depends(exige(...))
    assert callable(dep)

    # Requisito 3: dependency interna existe e é chamável
    assert callable(dep.dependency)
