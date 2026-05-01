#!/usr/bin/env python3
"""
LINCE — Modulo de Baliza de Alerta
Mantiene una base de datos de avatares conocidos del acosador y lanza
alertas automaticas cuando detecta nuevas cuentas con la misma imagen.

Diferencia clave con watcher.py:
  watcher.py -> monitoriza si el usuario conocido reaparece en plataformas
  alerts.py  -> detecta CUENTAS NUEVAS/ALIAS del acosador por similitud de avatar,
                incluyendo variantes de nombre de usuario
"""

import os
import json
import time
import logging
import requests
from io import BytesIO
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR
from colorama import Fore, Style

from modules.utils import log_action

logging.getLogger('apscheduler').setLevel(logging.WARNING)

# Plataformas con URL directa de perfil y endpoint de imagen
BEACON_PLATFORMS = {
    'GitHub':       'https://github.com/{username}',
    'Reddit':       'https://reddit.com/user/{username}',
    'Telegram':     'https://t.me/{username}',
    'TikTok':       'https://tiktok.com/@{username}',
    'Twitch':       'https://twitch.tv/{username}',
    'Instagram':    'https://instagram.com/{username}',
    'Mastodon':     'https://mastodon.social/@{username}',
    'DevTo':        'https://dev.to/{username}',
    'GitLab':       'https://gitlab.com/{username}',
}


class AlertBeacon:
    """
    Sistema de baliza: detecta cuentas nuevas/alias del acosador
    comparando avatares contra la DB de hashes conocidos del acosador.
    """

    def __init__(self, case_id, config, session=None):
        self.case_id   = case_id
        self.config    = config
        self.scheduler = BackgroundScheduler(timezone='Europe/Madrid')
        self._running  = False
        self._session  = session or requests.Session()
        self._session.headers['User-Agent'] = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )

        m = config.get('monitoring', {})
        self.interval_hours   = m.get('interval_hours', 4)
        self.threshold        = m.get('avatar_similarity_threshold', 0.88)
        self.telegram_token   = m.get('telegram_bot_token', '')
        self.telegram_chat_id = m.get('telegram_chat_id', '')
        self.notify_telegram  = m.get('notify_telegram', False)

        self.scheduler.add_listener(self._on_error, EVENT_JOB_ERROR)

    # -----------------------------------------------------------------------
    # BASE DE DATOS DE AVATARES DEL ACOSADOR
    # -----------------------------------------------------------------------
    def _db_path(self):
        return os.path.join('data', self.case_id, 'harasser_db.json')

    def _load_db(self):
        """Carga la DB de avatares conocidos del acosador."""
        if os.path.exists(self._db_path()):
            try:
                with open(self._db_path(), 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'avatars': [], 'known_urls': []}

    def _save_db(self, db):
        """Guarda la DB de avatares."""
        os.makedirs(os.path.join('data', self.case_id), exist_ok=True)
        with open(self._db_path(), 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)

    def register_harasser_avatar(self, avatar_path_or_url, platform, username):
        """
        Registra un avatar del acosador en la DB.
        Acepta ruta local o URL directa.
        """
        try:
            from PIL import Image
            import imagehash

            if avatar_path_or_url.startswith('http'):
                resp = self._session.get(avatar_path_or_url, timeout=10)
                img = Image.open(BytesIO(resp.content)).convert('RGB')
            else:
                img = Image.open(avatar_path_or_url).convert('RGB')

            phash_val = str(imagehash.phash(img))

            db = self._load_db()

            # Evitar duplicados por hash
            existing = [e['hash'] for e in db['avatars']]
            if phash_val in existing:
                print(f"{Fore.YELLOW}  Avatar ya registrado en la DB.{Style.RESET_ALL}")
                return False

            entry = {
                'hash':      phash_val,
                'platform':  platform,
                'username':  username,
                'source':    avatar_path_or_url,
                'added_at':  datetime.now().isoformat(),
            }
            db['avatars'].append(entry)
            self._save_db(db)

            print(f"{Fore.GREEN}  Avatar registrado en DB del acosador: {platform}/@{username}{Style.RESET_ALL}")
            log_action(f"[BALIZA] Avatar registrado: {platform}/{username}", "INFO")
            return True

        except Exception as e:
            print(f"{Fore.RED}  Error registrando avatar: {e}{Style.RESET_ALL}")
            log_action(f"[BALIZA] Error registro avatar: {e}", "ERROR")
            return False

    def register_from_case_avatars(self):
        """
        Registra automaticamente todos los avatares ya descargados del caso en la DB.
        """
        avatar_dir = os.path.join('data', self.case_id, 'avatars')
        if not os.path.exists(avatar_dir):
            print(f"{Fore.YELLOW}  No hay avatares descargados en este caso todavia.{Style.RESET_ALL}")
            return 0

        files = [f for f in os.listdir(avatar_dir)
                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        registered = 0
        for fname in files:
            parts = fname.split('_', 1)
            platform = parts[0].title() if parts else 'Desconocida'
            username = parts[1].rsplit('.', 1)[0] if len(parts) > 1 else fname
            fpath = os.path.join(avatar_dir, fname)
            if self.register_harasser_avatar(fpath, platform, username):
                registered += 1

        print(f"{Fore.GREEN}  {registered} avatares registrados en la DB del acosador.{Style.RESET_ALL}")
        return registered

    def show_db(self):
        """Muestra el contenido de la DB de avatares del acosador."""
        db = self._load_db()
        avatars = db.get('avatars', [])
        print(f"\n{Fore.CYAN}  DB ACOSADOR — {len(avatars)} avatares registrados{Style.RESET_ALL}")
        if not avatars:
            print(f"  {Fore.YELLOW}Sin registros. Usa 'Registrar avatares' primero.{Style.RESET_ALL}")
            return
        for i, a in enumerate(avatars, 1):
            print(f"  {Fore.YELLOW}[{i}]{Style.RESET_ALL} "
                  f"{a['platform']:<16} @{a['username']:<20} "
                  f"hash={a['hash'][:12]}...  "
                  f"({a['added_at'][:10]})")

    # -----------------------------------------------------------------------
    # COMPARACION CONTRA DB
    # -----------------------------------------------------------------------
    def compare_image_against_db(self, img_source):
        """
        Compara una imagen (URL o ruta) contra todos los hashes de la DB.
        Retorna lista de matches [{db_entry, similarity}] ordenada por similitud.
        """
        try:
            from PIL import Image
            import imagehash

            if isinstance(img_source, str) and img_source.startswith('http'):
                resp = self._session.get(img_source, timeout=10)
                img = Image.open(BytesIO(resp.content)).convert('RGB')
            elif hasattr(img_source, 'read'):
                img = Image.open(img_source).convert('RGB')
            else:
                img = Image.open(img_source).convert('RGB')

            candidate_hash = imagehash.phash(img)
            db = self._load_db()
            matches = []

            for entry in db.get('avatars', []):
                db_hash   = imagehash.hex_to_hash(entry['hash'])
                distance  = candidate_hash - db_hash
                similarity = 1.0 - distance / 64.0
                if similarity >= self.threshold:
                    matches.append({
                        'entry':      entry,
                        'similarity': round(similarity * 100, 1),
                        'distance':   distance,
                    })

            return sorted(matches, key=lambda x: -x['similarity'])

        except Exception as e:
            log_action(f"[BALIZA] Error comparando imagen: {e}", "ERROR")
            return []

    # -----------------------------------------------------------------------
    # SCAN DE VARIANTES DE USERNAME
    # -----------------------------------------------------------------------
    @staticmethod
    def generate_username_variants(username):
        """
        Genera variantes comunes que un acosador puede usar al crear nueva cuenta.
        """
        u = username.lstrip('@')
        variants = [
            u,
            f"{u}2",       f"{u}_",      f"_{u}",
            f"{u}1",       f"{u}3",      f"{u}_2",
            f"{u}oficial", f"{u}_real",  f"real_{u}",
            f"{u}_backup", f"{u}_nuevo", f"nuevo_{u}",
            f"{u}vuelve",  f"{u}_v2",    f"{u}v2",
            f"{u}_alt",    f"alt_{u}",
        ]
        return list(dict.fromkeys(variants))  # sin duplicados

    # -----------------------------------------------------------------------
    # CICLO DE BALIZA
    # -----------------------------------------------------------------------
    def beacon_cycle(self, username):
        """
        Ciclo de escaneo:
        1. Genera variantes del username
        2. Para cada variante y plataforma descarga el og:image
        3. Compara contra la DB de hashes del acosador
        4. Alerta si similarity > threshold
        """
        from bs4 import BeautifulSoup

        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_action(f"[BALIZA] Ciclo iniciado para {username}", "INFO")
        db = self._load_db()

        if not db.get('avatars'):
            log_action("[BALIZA] DB vacia, omitiendo ciclo", "WARNING")
            return

        variants = self.generate_username_variants(username)
        alerts_fired = []

        for variant in variants:
            for platform, url_tpl in BEACON_PLATFORMS.items():
                url = url_tpl.format(username=variant)
                try:
                    resp = self._session.get(url, timeout=8, allow_redirects=True)
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.text, 'html.parser')
                    img_url = None
                    og = soup.find('meta', property='og:image')
                    if og and og.get('content', '').startswith('http'):
                        img_url = og['content']

                    if not img_url:
                        tw = soup.find('meta', attrs={'name': 'twitter:image'})
                        if tw and tw.get('content', '').startswith('http'):
                            img_url = tw['content']

                    if not img_url:
                        continue

                    matches = self.compare_image_against_db(img_url)
                    for m in matches:
                        alert_key = f"{platform}:{variant}"
                        if alert_key not in db.get('known_urls', []):
                            msg = (
                                f"[LINCE BALIZA] NUEVA CUENTA DETECTADA\n"
                                f"Plataforma : {platform}\n"
                                f"Variante   : @{variant}\n"
                                f"URL        : {url}\n"
                                f"Similitud  : {m['similarity']}%\n"
                                f"Referencia : {m['entry']['platform']}/@{m['entry']['username']}\n"
                                f"Hora       : {ts}"
                            )
                            alerts_fired.append({
                                'platform': platform, 'username': variant,
                                'url': url, 'similarity': m['similarity'],
                                'ts': ts,
                            })
                            self._send_beacon_alert(msg)
                            db.setdefault('known_urls', []).append(alert_key)
                            self._save_db(db)
                            log_action(
                                f"[BALIZA] MATCH {platform}/@{variant} sim={m['similarity']}%",
                                "WARNING"
                            )

                    time.sleep(0.4)

                except Exception as e:
                    log_action(f"[BALIZA] Error scan {platform}/{variant}: {e}", "ERROR")
                    continue

        if not alerts_fired:
            log_action(f"[BALIZA] Ciclo limpio para {username} — sin nuevas cuentas", "INFO")

        # Guardar log del ciclo
        self._save_cycle_log(ts, username, alerts_fired)
        return alerts_fired

    def _send_beacon_alert(self, message):
        """Envia alerta de baliza por Telegram si esta configurado."""
        if self.notify_telegram and self.telegram_token and self.telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                requests.post(
                    url,
                    json={'chat_id': self.telegram_chat_id, 'text': message},
                    timeout=10,
                )
                log_action("[BALIZA] Alerta Telegram enviada", "INFO")
            except Exception as e:
                log_action(f"[BALIZA] Error Telegram: {e}", "ERROR")
        else:
            # Solo consola
            print(f"\n{Fore.RED}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.RED}  [BALIZA] NUEVA CUENTA DETECTADA{Style.RESET_ALL}")
            print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}")
            for line in message.split('\n')[1:]:
                print(f"  {Fore.YELLOW}{line}{Style.RESET_ALL}")
            print()

    def _save_cycle_log(self, ts, username, alerts):
        log_file = os.path.join('data', self.case_id, 'beacon_log.json')
        cycles = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    cycles = json.load(f)
            except Exception:
                cycles = []
        cycles.append({'ts': ts, 'username': username, 'alerts': len(alerts)})
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(cycles[-100:], f, indent=2, ensure_ascii=False)

    # -----------------------------------------------------------------------
    # CONTROL DEL SCHEDULER
    # -----------------------------------------------------------------------
    def start(self, username):
        if self._running:
            print(f"{Fore.YELLOW}  Baliza ya activa.{Style.RESET_ALL}")
            return
        self.scheduler.add_job(
            self.beacon_cycle,
            'interval',
            hours=self.interval_hours,
            args=[username],
            id='lince_beacon',
            misfire_grace_time=300,
        )
        self.scheduler.start()
        self._running = True
        log_action(f"[BALIZA] Iniciada para {username} c/{self.interval_hours}h", "INFO")
        print(f"{Fore.GREEN}  Baliza activa para @{username} "
              f"(cada {self.interval_hours}h){Style.RESET_ALL}")

    def stop(self):
        if not self._running:
            return
        try:
            self.scheduler.shutdown(wait=False)
        except Exception:
            pass
        self._running = False
        log_action("[BALIZA] Detenida", "INFO")
        print(f"{Fore.YELLOW}  Baliza detenida.{Style.RESET_ALL}")

    def is_running(self):
        return self._running

    def _on_error(self, event):
        log_action(f"[BALIZA] Error scheduler: {event.exception}", "ERROR")

    def show_status(self):
        db = self._load_db()
        n_hashes = len(db.get('avatars', []))
        log_file = os.path.join('data', self.case_id, 'beacon_log.json')
        n_cycles = 0
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    n_cycles = len(json.load(f))
            except Exception:
                pass

        print(f"\n{Fore.CYAN}  ESTADO DE LA BALIZA{Style.RESET_ALL}")
        print(f"  Hashes en DB      : {n_hashes}")
        print(f"  Estado            : "
              + (f"{Fore.GREEN}ACTIVA{Style.RESET_ALL}" if self._running
                 else f"{Fore.RED}INACTIVA{Style.RESET_ALL}"))
        print(f"  Intervalo         : {self.interval_hours}h")
        print(f"  Umbral similitud  : {self.threshold*100:.0f}%")
        print(f"  Ciclos ejecutados : {n_cycles}")
        print(f"  Telegram          : "
              + (f"{Fore.GREEN}Configurado{Style.RESET_ALL}" if self.telegram_token
                 else f"{Fore.YELLOW}No configurado (solo consola){Style.RESET_ALL}"))
