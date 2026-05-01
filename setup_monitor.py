#!/usr/bin/env python3
"""
setup_monitor.py — Configura el monitor de víctima como tarea de Windows
para que arranque automaticamente sin tener el toolkit abierto.

Uso:
  python setup_monitor.py install   <- crea la tarea
  python setup_monitor.py remove    <- elimina la tarea
  python setup_monitor.py status    <- muestra el estado
  python setup_monitor.py run       <- ejecuta un ciclo ahora (para testing)
"""

import sys
import os
import json
import subprocess
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PYTHON      = sys.executable
TASK_NAME   = "LINCE_VictimMonitor"
CONFIG_FILE = os.path.join(BASE_DIR, "data", "monitor_config.json")


# ---------------------------------------------------------------------------
# Script que ejecuta el scheduler
# ---------------------------------------------------------------------------
MONITOR_SCRIPT = os.path.join(BASE_DIR, "run_monitor.py")

MONITOR_SCRIPT_CONTENT = '''#!/usr/bin/env python3
"""Ejecutado por el Task Scheduler — un ciclo de escaneo completo."""
import sys, os
sys.path.insert(0, "{base_dir}")
os.chdir("{base_dir}")

import json
from modules.victim_watcher import VictimWatcher

cfg_file = "{config_file}"
if not os.path.exists(cfg_file):
    print("Sin configuracion. Ejecuta setup_monitor.py configure primero.")
    sys.exit(0)

with open(cfg_file, encoding="utf-8") as f:
    cfg = json.load(f)

vw = VictimWatcher(cfg["case_id"], config=cfg.get("config", {{}}))
vw.victim          = cfg.get("victim", "")
vw.red_protegida   = cfg.get("red_protegida", [])

if not vw.victim:
    print("Victima no configurada.")
    sys.exit(0)

print(f"Iniciando escaneo de @{{vw.victim}} a {{__import__('datetime').datetime.now()}}")
alertas = vw.scan_now()
print(f"Ciclo completado. Alertas: {{len(alertas)}}")
'''


def _save_run_script():
    content = MONITOR_SCRIPT_CONTENT.format(
        base_dir=BASE_DIR.replace("\\", "\\\\"),
        config_file=CONFIG_FILE.replace("\\", "\\\\"),
    )
    with open(MONITOR_SCRIPT, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Script de monitor: {MONITOR_SCRIPT}")


def configure():
    """Guarda la configuracion del monitor (victima, caso, intervalo)."""
    print("\n=== CONFIGURAR MONITOR ===\n")
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    # Cargar config existente si hay
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    victim = input(f"  Victima a proteger [{cfg.get('victim','')}]: ").strip().lstrip("@")
    if victim:
        cfg["victim"] = victim

    case_id = input(f"  Case ID [{cfg.get('case_id','CASE-001')}]: ").strip()
    if case_id:
        cfg["case_id"] = case_id
    elif "case_id" not in cfg:
        cfg["case_id"] = "CASE-001"

    red = input(f"  Red protegida (comas) [{','.join(cfg.get('red_protegida',[]))}]: ").strip()
    if red:
        cfg["red_protegida"] = [u.strip().lstrip("@") for u in red.split(",") if u.strip()]
    elif "red_protegida" not in cfg:
        cfg["red_protegida"] = []

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"\n  Guardado en {CONFIG_FILE}")
    return cfg


def install(interval_hours: int = 4):
    """Instala la tarea en Windows Task Scheduler."""
    if sys.platform != "win32":
        print("Task Scheduler solo disponible en Windows.")
        print(f"En Linux/Mac usa: crontab -e")
        print(f"  0 */{interval_hours} * * * {PYTHON} {MONITOR_SCRIPT}")
        return

    _save_run_script()

    # Crear la tarea con schtasks
    trigger_hours = max(1, interval_hours)
    cmd = [
        "schtasks", "/create", "/f",
        "/tn", TASK_NAME,
        "/tr", f'"{PYTHON}" "{MONITOR_SCRIPT}"',
        "/sc", "HOURLY",
        "/mo", str(trigger_hours),
        "/ru", os.environ.get("USERNAME", ""),
        "/rl", "HIGHEST",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"\n  Tarea '{TASK_NAME}' instalada.")
            print(f"  Ejecutara cada {trigger_hours}h: {PYTHON} {MONITOR_SCRIPT}")
            print(f"\n  Para ver en Task Scheduler: taskschd.msc")
        else:
            print(f"\n  Error al crear tarea:")
            print(f"  {result.stderr.strip()}")
            print(f"\n  Alternativa manual: schtasks /create /tn {TASK_NAME}")
    except FileNotFoundError:
        print("  schtasks no encontrado. Abre 'Programador de tareas' manualmente.")


def remove():
    """Elimina la tarea del Task Scheduler."""
    if sys.platform != "win32":
        print("Edita tu crontab: crontab -e")
        return
    cmd = ["schtasks", "/delete", "/f", "/tn", TASK_NAME]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  Tarea '{TASK_NAME}' eliminada.")
    else:
        print(f"  {result.stderr.strip()}")


def status():
    """Muestra el estado de la tarea."""
    if sys.platform == "win32":
        cmd = ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="cp850")
        print(result.stdout if result.returncode == 0 else
              f"  Tarea '{TASK_NAME}' no encontrada.")
    else:
        print("  crontab -l")

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
        print(f"\n  Config actual:")
        print(f"    Victima:       @{cfg.get('victim','N/D')}")
        print(f"    Case ID:       {cfg.get('case_id','N/D')}")
        print(f"    Red protegida: {cfg.get('red_protegida',[])}")
    else:
        print(f"\n  Sin configuracion ({CONFIG_FILE})")


def run_now():
    """Ejecuta un ciclo de escaneo ahora mismo."""
    if not os.path.exists(CONFIG_FILE):
        print("Sin configuracion. Ejecuta primero: python setup_monitor.py configure")
        return
    _save_run_script()
    os.execv(PYTHON, [PYTHON, MONITOR_SCRIPT])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    print(f"\n{'='*55}")
    print(f"  LINCE — Monitor de Victima / Task Scheduler")
    print(f"{'='*55}\n")

    if cmd == "install":
        cfg = configure()
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        install(hours)
    elif cmd == "configure":
        configure()
    elif cmd == "remove":
        remove()
    elif cmd == "status":
        status()
    elif cmd == "run":
        run_now()
    else:
        print("  Uso:")
        print("    python setup_monitor.py install [horas]  <- instala Task Scheduler")
        print("    python setup_monitor.py configure        <- solo configura victima")
        print("    python setup_monitor.py remove           <- elimina la tarea")
        print("    python setup_monitor.py status           <- estado actual")
        print("    python setup_monitor.py run              <- escaneo inmediato")
        print()
        print("  Ejemplo rapido:")
        print("    python setup_monitor.py install 4")
        print("    -> monitorea @victima cada 4 horas en segundo plano")
