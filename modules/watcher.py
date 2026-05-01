#!/usr/bin/env python3
"""
Modulo de vigilancia automatica - LINCE Watcher
Monitoriza periodicamente si el acosador crea nuevas cuentas
y envia alertas por Telegram o email cuando detecta actividad nueva.

Requiere: apscheduler, imagehash, Pillow
Configuracion en config.yaml seccion 'monitoring'
"""

import os
import json
import smtplib
import logging
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from colorama import Fore, Style

from modules.utils import log_action

# Silenciar logs verbosos de APScheduler en consola
logging.getLogger('apscheduler').setLevel(logging.WARNING)


class CaseWatcher:
    """
    Vigilante de caso en segundo plano.
    Cada X horas re-verifica las plataformas del objetivo y compara
    avatares para detectar cuentas nuevas del acosador.
    """

    def __init__(self, case_id, username, config, investigator, analyzer):
        self.case_id    = case_id
        self.username   = username
        self.config     = config
        self.inv        = investigator
        self.analyzer   = analyzer
        self.scheduler  = BackgroundScheduler(timezone='Europe/Madrid')
        self._running   = False
        self._job       = None

        # Configuracion de monitoring desde config.yaml
        m = config.get('monitoring', {})
        self.interval_hours    = m.get('interval_hours', 6)
        self.notify_telegram   = m.get('notify_telegram', False)
        self.telegram_token    = m.get('telegram_bot_token', '')
        self.telegram_chat_id  = m.get('telegram_chat_id', '')
        self.notify_email      = m.get('notify_email', False)
        self.email_cfg         = {
            'host':     m.get('email_smtp_host', 'smtp.gmail.com'),
            'port':     m.get('email_smtp_port', 465),
            'user':     m.get('email_username', ''),
            'password': m.get('email_password', ''),
            'to':       m.get('email_to', ''),
        }

        # Escuchar errores del scheduler
        self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

    # -----------------------------------------------------------------------
    # CONTROL DEL WATCHER
    # -----------------------------------------------------------------------
    def start(self):
        """Inicia la vigilancia en segundo plano."""
        if self._running:
            print(f"{Fore.YELLOW}El watcher ya esta activo.{Style.RESET_ALL}")
            return

        self._job = self.scheduler.add_job(
            func=self._watch_cycle,
            trigger='interval',
            hours=self.interval_hours,
            id='lince_watcher',
            next_run_time=None,   # Primera ejecucion manual o en el intervalo
            misfire_grace_time=300,
        )
        self.scheduler.start()
        self._running = True

        log_action(
            f"Watcher iniciado: {self.username} | intervalo={self.interval_hours}h",
            "INFO"
        )
        print(
            f"\n{Fore.GREEN}Vigilancia activa para @{self.username} "
            f"cada {self.interval_hours}h{Style.RESET_ALL}"
        )

        # Guardar estado en disco
        self._save_state()

    def stop(self):
        """Detiene el scheduler y limpia."""
        if not self._running:
            return
        try:
            self.scheduler.shutdown(wait=False)
        except Exception:
            pass
        self._running = False
        log_action("Watcher detenido", "INFO")
        print(f"{Fore.YELLOW}Vigilancia detenida.{Style.RESET_ALL}")

    def run_now(self):
        """Ejecuta un ciclo de vigilancia de forma inmediata (en primer plano)."""
        print(f"\n{Fore.CYAN}Ejecutando ciclo de vigilancia ahora...{Style.RESET_ALL}")
        self._watch_cycle()

    def is_running(self):
        return self._running

    # -----------------------------------------------------------------------
    # CICLO DE VIGILANCIA
    # -----------------------------------------------------------------------
    def _watch_cycle(self):
        """
        Ciclo principal:
        1. Re-busca el username (solo plataformas bloqueadas/desconocidas)
        2. Compara avatares nuevos vs existentes
        3. Calcula riesgo actualizado
        4. Envia alerta si hay novedades
        """
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_action(f"[WATCHER] Ciclo iniciado para {self.username}", "INFO")

        # --- 1. Re-busqueda de username ---
        prev_found = self._load_previous_found()
        new_results = self.inv.search_username(self.username)

        # Detectar plataformas NUEVAS encontradas en este ciclo
        new_platforms = {
            p: u for p, u in new_results.items()
            if p not in prev_found
        }

        # --- 2. Comparacion de avatares ---
        avatar_matches = self.inv.compare_all_case_avatars(self.case_id)
        new_matches = [
            m for m in avatar_matches
            if not self._was_reported(m)
        ]

        # --- 3. Evaluar si hay novedades ---
        novelties = []

        if new_platforms:
            for p, u in new_platforms.items():
                msg = f"Nueva cuenta detectada en {p}: {u}"
                novelties.append(msg)
                log_action(f"[WATCHER] {msg}", "WARNING")

        if new_matches:
            for m in new_matches:
                msg = (
                    f"Avatar identico en {m['platform1']} y {m['platform2']} "
                    f"({m['similarity']}% similitud) -> probable multi-cuenta"
                )
                novelties.append(msg)
                log_action(f"[WATCHER] {msg}", "WARNING")
                self._mark_reported(m)

        # --- 4. Alerta si hay novedades ---
        if novelties:
            risk = self.analyzer.calculate_risk_level(
                evidences=[],
                username_results=new_results,
            )
            self._send_alert(novelties, risk, ts)

        # Guardar ciclo
        self._save_cycle_log(ts, new_platforms, new_matches, novelties)

    # -----------------------------------------------------------------------
    # NOTIFICACIONES
    # -----------------------------------------------------------------------
    def _send_alert(self, novelties, risk, timestamp):
        """Envia alerta por Telegram y/o email con las novedades detectadas."""
        header = (
            f"[LINCE] ALERTA — @{self.username}\n"
            f"Fecha: {timestamp}\n"
            f"Nivel de riesgo: {risk['level']} ({risk['score']}/100)\n\n"
            "NOVEDADES DETECTADAS:\n"
        )
        body = header + "\n".join(f"• {n}" for n in novelties)

        sent = False

        if self.notify_telegram and self.telegram_token and self.telegram_chat_id:
            sent = self._notify_telegram(body) or sent

        if self.notify_email and self.email_cfg.get('user'):
            sent = self._notify_email(body) or sent

        if not sent:
            # Fallback: solo en consola
            print(f"\n{Fore.RED}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.RED}  [WATCHER] ALERTA DETECTADA{Style.RESET_ALL}")
            print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}")
            for n in novelties:
                print(f"  {Fore.YELLOW}> {n}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Configura Telegram o email en config.yaml para alertas automaticas.{Style.RESET_ALL}\n")

    def _notify_telegram(self, message):
        """Envia mensaje via Telegram Bot API."""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            resp = requests.post(
                url,
                json={
                    'chat_id':    self.telegram_chat_id,
                    'text':       message,
                    'parse_mode': 'HTML',
                },
                timeout=10,
            )
            if resp.ok:
                log_action("Alerta Telegram enviada", "INFO")
                return True
            else:
                log_action(f"Error Telegram: {resp.text}", "ERROR")
        except Exception as e:
            log_action(f"Error enviando Telegram: {e}", "ERROR")
        return False

    def _notify_email(self, body):
        """Envia alerta por email via SMTP SSL."""
        try:
            cfg = self.email_cfg
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[LINCE ALERTA] @{self.username} — nueva actividad detectada"
            msg['From']    = cfg['user']
            msg['To']      = cfg['to']

            # Parte texto plano
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Parte HTML con formato
            html_body = (
                f"<pre style='font-family:monospace'>{body}</pre>"
                f"<hr><small>LINCE - Investigacion Forense Digital</small>"
            )
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            with smtplib.SMTP_SSL(cfg['host'], cfg['port']) as server:
                server.login(cfg['user'], cfg['password'])
                server.send_message(msg)

            log_action(f"Alerta email enviada a {cfg['to']}", "INFO")
            return True
        except Exception as e:
            log_action(f"Error enviando email: {e}", "ERROR")
        return False

    # -----------------------------------------------------------------------
    # ESTADO Y PERSISTENCIA
    # -----------------------------------------------------------------------
    def _state_file(self):
        return os.path.join('data', self.case_id, 'watcher_state.json')

    def _save_state(self):
        os.makedirs(os.path.join('data', self.case_id), exist_ok=True)
        state = {
            'username':        self.username,
            'interval_hours':  self.interval_hours,
            'started_at':      datetime.now().isoformat(),
            'reported_matches': getattr(self, '_reported', []),
        }
        with open(self._state_file(), 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def _load_previous_found(self):
        """Carga plataformas ya conocidas del cache de username."""
        from modules.investigator import CACHE_FILE
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                user_data = cache.get(self.username, {})
                return {
                    p: d['url'] for p, d in user_data.items()
                    if d.get('status') == 'found'
                }
        except Exception:
            pass
        return {}

    def _was_reported(self, match):
        """Comprueba si esta coincidencia de avatar ya fue notificada."""
        reported = getattr(self, '_reported', [])
        key = f"{match['file1']}:{match['file2']}"
        return key in reported

    def _mark_reported(self, match):
        if not hasattr(self, '_reported'):
            self._reported = []
        key = f"{match['file1']}:{match['file2']}"
        if key not in self._reported:
            self._reported.append(key)
        self._save_state()

    def _save_cycle_log(self, ts, new_platforms, new_matches, novelties):
        """Guarda el log del ciclo de vigilancia."""
        log_dir  = os.path.join('data', self.case_id)
        log_file = os.path.join(log_dir, 'watcher_log.json')
        os.makedirs(log_dir, exist_ok=True)

        cycles = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    cycles = json.load(f)
            except Exception:
                cycles = []

        cycles.append({
            'timestamp':     ts,
            'new_platforms': new_platforms,
            'avatar_matches': len(new_matches),
            'novelties':     novelties,
        })

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(cycles[-50:], f, indent=2, ensure_ascii=False)  # Max 50 ciclos

    def _on_job_error(self, event):
        log_action(f"[WATCHER] Error en job: {event.exception}", "ERROR")

    # -----------------------------------------------------------------------
    # RESUMEN DEL ESTADO
    # -----------------------------------------------------------------------
    def show_status(self):
        """Muestra el estado actual del watcher en consola."""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  ESTADO DEL WATCHER{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"  Objetivo    : @{self.username}")
        print(f"  Caso        : {self.case_id}")
        print(f"  Estado      : "
              f"{Fore.GREEN}ACTIVO{Style.RESET_ALL}" if self._running
              else f"{Fore.RED}INACTIVO{Style.RESET_ALL}")
        print(f"  Intervalo   : cada {self.interval_hours} horas")

        if self._running and self._job:
            next_run = self.scheduler.get_job('lince_watcher')
            if next_run and next_run.next_run_time:
                nrt = next_run.next_run_time.strftime('%d/%m/%Y %H:%M')
                print(f"  Proxima ejecucion: {nrt}")

        # Alertas configuradas
        alerts = []
        if self.notify_telegram and self.telegram_token:
            alerts.append('Telegram')
        if self.notify_email and self.email_cfg.get('user'):
            alerts.append('Email')
        print(f"  Alertas     : {', '.join(alerts) if alerts else 'Solo consola'}")

        # Historial de ciclos
        log_file = os.path.join('data', self.case_id, 'watcher_log.json')
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    cycles = json.load(f)
                print(f"  Ciclos ejecutados: {len(cycles)}")
                if cycles:
                    last = cycles[-1]
                    print(f"  Ultimo ciclo: {last['timestamp']}")
                    if last.get('novelties'):
                        print(f"  Novedades ultimas: {len(last['novelties'])}")
                        for n in last['novelties']:
                            print(f"    {Fore.YELLOW}> {n}{Style.RESET_ALL}")
            except Exception:
                pass
        print()
