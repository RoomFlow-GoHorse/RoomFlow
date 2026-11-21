def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_cnpj(cnpj: str) -> str:
    return "".join(character for character in cnpj if character.isdigit())
