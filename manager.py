"""Ponto de entrada principal da aplicação MatexUnB.

Inicia o servidor Web (Flask).
"""

import os
import sys
import logging
from web_app import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    """Inicia o servidor web do MatexUnB."""
    port = int(os.environ.get('PORT', 5050))
    host = os.environ.get('HOST', '0.0.0.0')

    print("=" * 60)
    print("⚡ MatexUnB Web Server Rodando!")
    print("Acesse no seu navegador:")
    print(f"👉 http://127.0.0.1:{port}")
    print(f"👉 http://localhost:{port}")
    print("Pressione CTRL+C no terminal para encerrar o servidor.")
    print("=" * 60)

    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
