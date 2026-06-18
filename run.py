import os
import sys
import subprocess
import webbrowser
import time
import threading

def run_server():
    print("Iniciando SanHub Unified API...")
    subprocess.run([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"])

def open_browser():
    # Aguarda o servidor subir antes de abrir a aba
    time.sleep(2)
    print("Abrindo painel web em http://localhost:8000")
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    t_server = threading.Thread(target=run_server)
    t_server.daemon = True
    t_server.start()
    
    open_browser()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
