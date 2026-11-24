"""Start the Streamlit monolith with the configured PostgreSQL database."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def start() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--streamlit-port', type=int, default=8501)
    args = parser.parse_args()
    if not 1 <= args.streamlit_port <= 65535:
        parser.error('Informe uma porta entre 1 e 65535.')
    try:
        return subprocess.call([
            sys.executable, '-m', 'streamlit', 'run', 'main.py',
            '--server.address', '127.0.0.1', '--server.port', str(args.streamlit_port),
        ], cwd=ROOT)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    raise SystemExit(start())
