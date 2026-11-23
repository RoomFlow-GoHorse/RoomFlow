"""Centraliza a criação dos dados iniciais e de demonstração do PostgreSQL."""

import argparse
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from config.constants import ROLE_LABELS
from config.database import SessionLocal
from controllers.password_service import hash_password
from models.database_models import (
    ConflitoReserva,
    DestinatarioNotificacao,
    Espaco,
    EspacoRecurso,
    Instituicao,
    Notificacao,
    Recurso,
    Reserva,
    TipoUsuario,
    Usuario,
    UsuarioInstituicao,
)


def cadastrar_perfis(sessao: Session) -> None:
    comando = (
        insert(TipoUsuario)
        .values([{"name": perfil} for perfil in ROLE_LABELS])
        .on_conflict_do_nothing(index_elements=[TipoUsuario.name])
    )
    sessao.execute(comando)


def semear_perfis() -> None:
    with SessionLocal.begin() as sessao:
        cadastrar_perfis(sessao)


def criar_contas(sessao: Session, instituicao_id: int, senha: str) -> dict[str, Usuario]:
    perfis = dict(sessao.execute(select(TipoUsuario.name, TipoUsuario.id)).all())
    contas = {
        perfil: Usuario(
            name=f"{rotulo} Demo",
            email=f"{perfil}@roomflow",
            password_hash=hash_password(senha),
            role=perfil,
            tipo_usuario_id=perfis[perfil],
            institution_links=[
                UsuarioInstituicao(
                    institution_id=instituicao_id,
                    role=perfil,
                    registration_number=f"DEMO-{numero:02}",
                )
            ],
        )
        for numero, (perfil, rotulo) in enumerate(ROLE_LABELS.items(), start=1)
    }
    sessao.add_all(contas.values())
    sessao.flush()
    return contas


def criar_agenda(sessao: Session, sala: Espaco, contas: dict[str, Usuario]) -> None:
    fuso = ZoneInfo("America/Porto_Velho")
    amanha = datetime.now(fuso).date() + timedelta(days=1)
    inicio = datetime.combine(amanha, time(9), tzinfo=fuso)
    reservas = [
        Reserva(
            instituicao_id=sala.instituicao_id,
            espaco_id=sala.id,
            solicitante_id=contas["solicitante"].id,
            titulo=titulo,
            tipo="aula",
            inicio=inicio + timedelta(hours=hora),
            fim=inicio + timedelta(hours=hora + 1),
            quantidade_participantes=20,
            status=status,
            avaliado_por=contas["gerente"].id if status == "aprovada" else None,
            avaliado_em=datetime.now(fuso) if status == "aprovada" else None,
        )
        for titulo, hora, status in (
            ("Aula aprovada", 0, "aprovada"),
            ("Aula aguardando aprovação", 2, "pendente"),
            ("Aula com choque de horário", 0, "pendente"),
        )
    ]
    sessao.add_all(reservas)
    sessao.flush()
    aprovada, pendente, sobreposta = reservas
    reserva_a, reserva_b = sorted((aprovada.id, sobreposta.id))
    sessao.add(
        ConflitoReserva(
            instituicao_id=sala.instituicao_id,
            reserva_a_id=reserva_a,
            reserva_b_id=reserva_b,
            motivo="Duas solicitações para a mesma sala e horário.",
        )
    )

    destinatarios = [
        (aprovada, "Reserva aprovada", "A aula foi aprovada pelo gerente.", "solicitante"),
        (pendente, "Horário atualizado", "Confira o novo horário na agenda.", "participante"),
    ]
    for reserva, titulo, mensagem, perfil in destinatarios:
        aviso = Notificacao(
            instituicao_id=sala.instituicao_id,
            reserva_id=reserva.id,
            titulo=titulo,
            mensagem=mensagem,
            categoria="reserva",
        )
        sessao.add(aviso)
        sessao.flush()
        sessao.add(
            DestinatarioNotificacao(
                instituicao_id=sala.instituicao_id,
                notificacao_id=aviso.id,
                usuario_id=contas[perfil].id,
                lida_em=datetime.now(fuso) if perfil == "participante" else None,
            )
        )


def semear_demo(senha: str) -> bool:
    with SessionLocal.begin() as sessao:
        cadastrar_perfis(sessao)
        instituicao_id = sessao.scalar(
            insert(Instituicao)
            .values(
                name="Faculdade unisapiens",
                cnpj="00000000000000",
                institution_type="faculdade",
                city="Porto Velho",
                state="RO",
            )
            .on_conflict_do_nothing(index_elements=[Instituicao.cnpj])
            .returning(Instituicao.id)
        )
        if instituicao_id is None:
            return False

        contas = criar_contas(sessao, instituicao_id, senha)
        sala, laboratorio, auditorio = [
            Espaco(
                instituicao_id=instituicao_id,
                nome=nome,
                tipo=tipo,
                capacidade=capacidade,
                localizacao=localizacao,
            )
            for nome, tipo, capacidade, localizacao in (
                ("Sala 101", "sala", 30, "Bloco A, térreo"),
                ("Laboratório de Informática", "laboratório", 24, "Bloco B, térreo"),
                ("Auditório Principal", "auditório", 120, "Bloco A, primeiro andar"),
            )
        ]
        projetor = Recurso(instituicao_id=instituicao_id, nome="Projetor", quantidade_total=1)
        computadores = Recurso(instituicao_id=instituicao_id, nome="Computador", quantidade_total=24)
        sessao.add_all([sala, laboratorio, auditorio, projetor, computadores])
        sessao.flush()
        sessao.add_all(
            [
                EspacoRecurso(
                    instituicao_id=instituicao_id,
                    espaco_id=sala.id,
                    recurso_id=projetor.id,
                    quantidade=1,
                ),
                EspacoRecurso(
                    instituicao_id=instituicao_id,
                    espaco_id=laboratorio.id,
                    recurso_id=computadores.id,
                    quantidade=24,
                ),
            ]
        )
        criar_agenda(sessao, sala, contas)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Popula dados iniciais do RoomFlow no PostgreSQL.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="cria também instituição, contas e dados de demonstração",
    )
    args = parser.parse_args()

    if args.demo:
        senha = "123456789"
        if semear_demo(senha):
            print("Perfis e dados de demonstração cadastrados na Faculdade unisapiens.")
        else:
            print("Os perfis foram conferidos; a instituição de demonstração já está cadastrada.")
    else:
        semear_perfis()
        print("Perfis cadastrados: " + ", ".join(ROLE_LABELS.values()))


if __name__ == "__main__":
    main()
