"""Start the local PostgreSQL-backed API and Streamlit in the same terminal."""

import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
from time import monotonic, sleep

import httpx2


ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"


def check_port(port: int) -> None:
    try:
        with socket.socket() as probe:
            probe.bind((HOST, port))
    except OSError:
        raise RuntimeError(f"A porta {port} está em uso. Feche o processo anterior ou escolha outra porta.") from None


def wait_for_api(process: subprocess.Popen, url: str) -> None:
    deadline = monotonic() + 25
    with httpx2.Client(base_url=url, timeout=6, trust_env=False) as client:
        while monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("O FastAPI encerrou na inicialização. Confira a saída acima.")
            try:
                response = client.get("/ready")
            except httpx2.RequestError:
                sleep(0.25)
                continue
            body = response.json()
            data = body.get("data", {})
            if response.is_success and data.get("persistence") == "postgres" and data.get("status") == "ready":
                return
            raise RuntimeError(body.get("error", {}).get("message", "A API PostgreSQL não está pronta."))
    raise RuntimeError("O FastAPI não ficou pronto dentro do tempo esperado.")


def start() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--streamlit-port", type=int, default=8501)
    args = parser.parse_args()
    if not (1 <= args.api_port <= 65535 and 1 <= args.streamlit_port <= 65535) or args.api_port == args.streamlit_port:
        parser.error("Informe duas portas diferentes entre 1 e 65535.")

    api = None
    frontend = None
    try:
        check_port(args.api_port)
        check_port(args.streamlit_port)
        url = f"http://{HOST}:{args.api_port}"
        api = subprocess.Popen(
            [sys.executable, "-B", "-m", "uvicorn", "api.main:app", "--host", HOST, "--port", str(args.api_port)],
            cwd=ROOT, env={**os.environ, "ROOMFLOW_PERSISTENCE": "postgres"},
        )
        wait_for_api(api, url)
        print(f"RoomFlow disponível em http://{HOST}:{args.streamlit_port} quando o Streamlit iniciar.", flush=True)
        frontend = subprocess.Popen(
            [sys.executable, "-B", "-m", "streamlit", "run", "main.py", "--server.address", HOST,
             "--server.port", str(args.streamlit_port), "--server.headless", "true"],
            cwd=ROOT, env={**os.environ, "ROOMFLOW_API_URL": url},
        )
        while frontend.poll() is None and api.poll() is None:
            sleep(0.25)
        if frontend.poll() is not None:
            return frontend.returncode
        raise RuntimeError("O FastAPI encerrou. Confira a saída acima.")
    except KeyboardInterrupt:
        return 0
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        for process in (frontend, api):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    raise SystemExit(start())
