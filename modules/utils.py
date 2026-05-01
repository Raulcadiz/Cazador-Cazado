"""
Módulo de utilidades para Anti-Acoso Toolkit
"""

import os
import sys
import hashlib
from datetime import datetime
from colorama import Fore, Style

def clear_screen():
    """Limpiar la pantalla de la consola"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Imprimir banner de la aplicación"""
    # Definir letras ASCII para L Y N X
    L = [
        "██╗     ██╗",
        "██║     ██║",
        "██║     ██║",
        "██║     ██║",
        "███████╗██║",
        "╚══════╝╚═╝"
    ]
    Y = [
        "██╗   ██╗",
        "╚██╗ ██╔╝",
        " ╚████╔╝ ",
        "  ╚██╔╝  ",
        "   ██║   ",
        "   ╚═╝   "
    ]
    N = [
        "███╗   ██╗",
        "████╗  ██║",
        "██╔██╗ ██║",
        "██║╚██╗██║",
        "██║ ╚████║",
        "╚═╝  ╚═══╝"
    ]
    X = [
        "██╗  ██╗",
        "╚██╗██╔╝",
        " ╚███╔╝ ",
        " ██╔██╗ ",
        "██╔╝ ██╗",
        "╚═╝  ╚═╝"
    ]
    
    # Combinar letras en líneas
    lineas = []
    for i in range(6):
        linea = L[i] + " " + Y[i] + " " + N[i] + " " + X[i]
        lineas.append(linea)
    
    banner = f"""
{Fore.RED}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        {lineas[0]}         ║
║        {lineas[1]}         ║
║        {lineas[2]}         ║
║        {lineas[3]}         ║
║        {lineas[4]}         ║
║        {lineas[5]}         ║
║                                                              ║
║            HERRAMIENTA DE INVESTIGACIÓN DIGITAL             ║
║                VERSIÓN 2.0.0 - USO ÉTICO                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
"""
    print(banner)

def log_action(action, level="INFO"):
    """Registrar acción en el log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {action}\n"
    
    with open("activity.log", "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)

def calculate_hash(file_path):
    """Calcular hash SHA-256 de un archivo"""
    sha256_hash = hashlib.sha256()
    
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return None

def validate_url(url):
    """Validar formato de URL"""
    import re
    url_pattern = re.compile(
        r'^(https?://)?'  # http:// or https://
        r'(([A-Z0-9][A-Z0-9_-]*)(\.[A-Z0-9][A-Z0-9_-]*)+)'  # domain
        r'(:[0-9]+)?'  # optional port
        r'(/.*)?$', re.IGNORECASE)
    
    return re.match(url_pattern, url) is not None

def create_directory_structure():
    """Crear estructura de directorios necesaria"""
    directories = ["data", "reports", "data/evidences", "data/images", 
                   "data/screenshots", "reports/police", "reports/legal"]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    return True