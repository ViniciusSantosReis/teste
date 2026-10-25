"""normalizar() — busca sem acento e sem diferenciar maiúsculas."""

"""Funções auxiliares para manipulação de texto no domínio."""

import unicodedata


def normalizar(texto: str) -> str:
    """Remove acentos, converte para minúsculas e remove espaços extras.

    Utilizado para popular colunas de busca (ex: nome_busca) e viabilizar
    consultas rápidas sem acento no banco de dados.
    """
    if not texto:
        return ""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode()
    return sem_acento.lower().strip()
