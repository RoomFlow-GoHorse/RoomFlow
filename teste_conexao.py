# Teste de conexão banco de dados
# 
# TODO: Após a implementação de um login, remover este arquivo do projeto.

from sqlalchemy import text 
from config.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        print("deu tudo certo")
        print(result.scalar())

except Exception as error:
    print("nao deu certo porque: ")
    print(error)

finally:
    engine.dispose()

