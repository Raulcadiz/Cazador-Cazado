#!/usr/bin/env python3
"""
VictimWatcher — Monitor de proteccion de la victima

Fetching stack (prioridad):
  1. twscrape       — scraping directo Twitter via cookie (más fiable)
  2. Scrapling StealthyFetcher — Camoufox, bypasa Cloudflare
  3. Scrapling Fetcher          — TLS fingerprint spoof
  4. requests                   — fallback basico

Mejoras incluidas:
  - Nitter healthcheck: prueba instancias antes de usarlas
  - Wayback Machine: archiva automaticamente cada amenaza detectada
  - twscrape: scraping nativo de Twitter con token de sesion
  - Task Scheduler: ver setup_monitor.py
  - Exportar alertas a PDF: ver metodo export_alerts_pdf()
"""

import os
import re
import json
import time
import hashlib
import smtplib
import requests
import urllib3
from datetime import datetime
from colorama import Fore, Style

urllib3.disable_warnings()

# ---------------------------------------------------------------------------
# Dependencias opcionales
# ---------------------------------------------------------------------------
try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    APScheduler_OK = True
except ImportError:
    APScheduler_OK = False

try:
    from scrapling.fetchers import Fetcher as _ScraplingFetcher
    SCRAPLING_OK = True
except ImportError:
    SCRAPLING_OK = False

try:
    from scrapling.fetchers import StealthyFetcher as _StealthyFetcher
    SCRAPLING_STEALTH = True
except ImportError:
    SCRAPLING_STEALTH = False

# twscrape: pip install twscrape  (requiere cuenta Twitter)
try:
    import twscrape                     # noqa: F401
    TWSCRAPE_OK = True
except ImportError:
    TWSCRAPE_OK = False

from modules.utils import log_action

# ---------------------------------------------------------------------------
# CONFIGURACION
# ---------------------------------------------------------------------------
NITTER_INSTANCES = [
    "https://xcancel.com",
    "https://nitter.tiekoetter.com",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.cz",
    "https://nitter.net",
]
CF_INSTANCES = {"nitter.tiekoetter.com", "nitter.poast.org"}

_FALLBACK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Configurar Scrapling una sola vez (API v0.3+)
if SCRAPLING_OK:
    try:
        _ScraplingFetcher.configure(adaptive=False)
    except Exception:
        pass
if SCRAPLING_STEALTH:
    try:
        _StealthyFetcher.configure(adaptive=False)
    except Exception:
        pass

# Palabras clave de amenaza grave (Art. 169 CP)
KEYWORDS_AMENAZA = [
    "besar cuneta", "beses cuneta", "besas cuneta", "besakuneta",
    "te voy a matar", "te voy a hacer daño", "voy a matarte",
    "te mato", "os mato", "te voy a violar", "te voy a pegar",
    "te voy a encontrar", "se donde vives", "conozco tu direccion",
    "voy a ir a tu casa", "mereces morir", "ojala te mueras",
    "ojalá te mueras", "ojala te maten", "a ver si te mueres",
    "putilla", "puta de mierda", "zorra", "te voy a reventar",
    "voy a hacerte daño", "pistola", "cuchillo",
    "ojala te atropellen", "ojala te pille",
    "que te jodan", "te callas o", "calla o te",
]

# Palabras clave de vigilancia leve (Art. 173 CP)
KEYWORDS_VIGILANCIA = [
    "imbecil", "idiota", "estupida", "comunista", "roja",
    "fascista", "tonta", "ignorante", "callaos", "callate",
    "verguenza", "vergüenza", "ridicula", "ridícula",
    "paleta", "cateta", "analfabeta",
]


# ---------------------------------------------------------------------------
# MEJORA #2 — Nitter healthcheck
# ---------------------------------------------------------------------------
_nitter_health: dict = {}   # {base_url: (ok: bool, ts: float)}
_HEALTH_TTL = 300           # re-checkear cada 5 min


def _nitter_is_alive(base: str, timeout: int = 6) -> bool:
    """Comprueba si una instancia Nitter responde con contenido util."""
    now = time.time()
    cached = _nitter_health.get(base)
    if cached and now - cached[1] < _HEALTH_TTL:
        return cached[0]
    try:
        r = requests.get(base, headers=_FALLBACK_HEADERS,
                         timeout=timeout, verify=False, allow_redirects=True)
        alive = r.status_code == 200 and len(r.content) > 2000
    except Exception:
        alive = False
    _nitter_health[base] = (alive, now)
    log_action(f"Nitter health {base}: {'OK' if alive else 'DOWN'}", "INFO")
    return alive


def _best_nitter() -> str:
    """Devuelve la primera instancia Nitter que responda, o '' si ninguna."""
    for inst in NITTER_INSTANCES:
        if _nitter_is_alive(inst):
            return inst
    return ""


# ---------------------------------------------------------------------------
# CAPA DE FETCHING
# ---------------------------------------------------------------------------

def _html_from_scrapling(page) -> str:
    body = getattr(page, "body", None)
    if body:
        return body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
    for attr in ("content", "html", "text"):
        val = getattr(page, attr, None)
        if val:
            return val.decode("utf-8", errors="replace") if isinstance(val, bytes) else str(val)
    return ""


def _scrapling_get(url: str, use_stealth: bool = False, timeout: int = 20):
    if not SCRAPLING_OK:
        return 0, ""
    try:
        if use_stealth and SCRAPLING_STEALTH:
            page = _StealthyFetcher.get(url, timeout=timeout, humanize=True)
        else:
            page = _ScraplingFetcher.get(url, stealthy_headers=True, timeout=timeout)
        status = int(getattr(page, "status", 0) or getattr(page, "status_code", 0))
        return status, _html_from_scrapling(page)
    except Exception as e:
        log_action(f"Scrapling error ({url[:55]}): {e}", "WARNING")
        return 0, ""


def _requests_get(url: str, timeout: int = 20):
    try:
        r = requests.get(url, headers=_FALLBACK_HEADERS,
                         timeout=timeout, verify=False)
        return r.status_code, r.text
    except Exception as e:
        log_action(f"requests error ({url[:55]}): {e}", "WARNING")
        return 0, ""


def _smart_get(url: str, nitter_base: str = "", timeout: int = 20):
    """Elige el mejor fetcher disponible y devuelve (status, html)."""
    is_cf = any(cf in nitter_base for cf in CF_INSTANCES)
    if SCRAPLING_OK:
        status, html = _scrapling_get(url, use_stealth=is_cf, timeout=timeout)
        if status == 200 and len(html) > 500:
            return status, html
        if is_cf and not SCRAPLING_STEALTH:
            status, html = _scrapling_get(url, use_stealth=False, timeout=timeout)
            if status == 200 and len(html) > 500:
                return status, html
    return _requests_get(url, timeout)


# ---------------------------------------------------------------------------
# MEJORA #1 — twscrape (scraping directo Twitter via cookie)
# ---------------------------------------------------------------------------

async def _twscrape_mentions(username: str, limit: int = 50) -> list:
    """
    Busca menciones de `username` en Twitter via twscrape.
    Requiere cuenta configurada: ver setup_twscrape() en este modulo.
    Devuelve lista de dicts compatibles con el resto del modulo.
    """
    if not TWSCRAPE_OK:
        return []
    results = []
    try:
        from twscrape import API
        api = API()
        async for tweet in api.search(f"@{username}", limit=limit):
            text = tweet.rawContent or ""
            tw_id = str(tweet.id)
            results.append({
                "id":         hashlib.md5(tw_id.encode()).hexdigest()[:12],
                "text":       text,
                "author":     f"@{tweet.user.username}" if tweet.user else "unknown",
                "date":       tweet.date.isoformat() if tweet.date else "",
                "url":        f"https://twitter.com/i/web/status/{tw_id}",
                "scraped_at": datetime.now().isoformat(),
                "source":     "twscrape",
            })
    except Exception as e:
        log_action(f"twscrape error: {e}", "WARNING")
    return results


def _run_twscrape_sync(username: str, limit: int = 50) -> list:
    """Wrapper sincrono para _twscrape_mentions."""
    if not TWSCRAPE_OK:
        return []
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_twscrape_mentions(username, limit))
        loop.close()
        return result
    except Exception as e:
        log_action(f"twscrape sync error: {e}", "WARNING")
        return []


def setup_twscrape(username: str, password: str,
                   email: str, email_password: str):
    """
    Configura una cuenta Twitter para twscrape.
    Ejecutar una vez antes de usar el monitor:
      from modules.victim_watcher import setup_twscrape
      setup_twscrape('mi_usuario', 'mi_pass', 'mi@email.com', 'email_pass')
    """
    if not TWSCRAPE_OK:
        print("Instala twscrape: pip install twscrape")
        return False
    import asyncio
    from twscrape import API

    async def _setup():
        api = API()
        await api.pool.add_account(username, password, email, email_password)
        await api.pool.login_all()
        print(f"Cuenta @{username} configurada en twscrape.")

    asyncio.run(_setup())
    return True


# ---------------------------------------------------------------------------
# SCRAPING NITTER
# ---------------------------------------------------------------------------

def _parse_nitter_html(html: str, limit: int = 50) -> list:
    if not BS4_OK or not html:
        return []
    results = []
    soup = BeautifulSoup(html, "html.parser")
    for tw in soup.select(".timeline-item")[:limit]:
        try:
            content_el = tw.select_one(".tweet-content")
            if not content_el:
                continue
            text = content_el.get_text(" ", strip=True)
            if not text:
                continue
            author_el = tw.select_one(".username")
            author    = author_el.get_text(strip=True) if author_el else "unknown"
            date_el   = tw.select_one(".tweet-date a")
            date_str  = ""
            tweet_url = ""
            if date_el:
                date_str  = date_el.get("title", "")
                href      = date_el.get("href", "")
                tweet_url = f"https://twitter.com{href}" if href.startswith("/") else href
            tw_id = hashlib.md5(text.encode()).hexdigest()[:12]
            results.append({
                "id":         tw_id,
                "text":       text,
                "author":     author,
                "date":       date_str,
                "url":        tweet_url,
                "scraped_at": datetime.now().isoformat(),
                "source":     "nitter",
            })
        except Exception:
            continue
    return results


def _fetch_nitter(username: str, base: str, timeout: int = 20) -> list:
    url = f"{base}/search?q=%40{username.lstrip('@')}&f=tweets"
    status, html = _smart_get(url, nitter_base=base, timeout=timeout)
    return _parse_nitter_html(html) if status == 200 and len(html) > 500 else []


def _fetch_ddg(username: str, max_results: int = 30) -> list:
    results = []
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return results
    queries = [
        f'"@{username.lstrip("@")}" amenaza OR acoso OR insulto',
        f'"{username.lstrip("@")}" (site:twitter.com OR site:x.com)',
    ]
    seen: set = set()
    try:
        d = DDGS()
        for q in queries:
            try:
                for item in d.text(q, max_results=max_results // 2):
                    url  = item.get("href", "")
                    text = f"{item.get('title','')} {item.get('body','')}".strip()
                    if not text or url in seen:
                        continue
                    seen.add(url)
                    tw_id  = hashlib.md5(text.encode()).hexdigest()[:12]
                    author = "desconocido"
                    m = re.search(r"twitter\.com/([^/]+)/status", url)
                    if m:
                        author = f"@{m.group(1)}"
                    results.append({
                        "id": tw_id, "text": text[:500], "author": author,
                        "date": "", "url": url,
                        "scraped_at": datetime.now().isoformat(), "source": "ddg",
                    })
            except Exception:
                pass
    except Exception as e:
        log_action(f"DDG error: {e}", "WARNING")
    return results


# ---------------------------------------------------------------------------
# MEJORA #8 — Wayback Machine: archivar amenazas
# ---------------------------------------------------------------------------

def _wayback_archive(url: str, timeout: int = 30) -> str:
    """
    Envia una URL al Wayback Machine para preservarla como evidencia permanente.
    Devuelve la URL del archivo o '' si falla.
    """
    if not url or not url.startswith("http"):
        return ""
    try:
        save_url = f"https://web.archive.org/save/{url}"
        r = requests.post(
            save_url,
            headers={**_FALLBACK_HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
            data={"url": url, "capture_all": "on"},
            timeout=timeout,
            allow_redirects=True,
        )
        if r.status_code in (200, 302):
            # La URL archivada suele ser la URL final (redirect)
            archived = r.url if "web.archive.org/web/" in r.url else ""
            if not archived:
                # Intentar extraer de cabeceras
                loc = r.headers.get("Location", "")
                archived = loc if "web.archive.org/web/" in loc else ""
            return archived
    except Exception as e:
        log_action(f"Wayback archive error ({url[:55]}): {e}", "WARNING")
    return ""


# ---------------------------------------------------------------------------
# CLASIFICADOR
# ---------------------------------------------------------------------------

def _clasificar(text: str):
    txt = text.lower()
    for kw in KEYWORDS_AMENAZA:
        if kw in txt:
            return "AMENAZA"
    for kw in KEYWORDS_VIGILANCIA:
        if kw in txt:
            return "VIGILANCIA"
    return None


# ---------------------------------------------------------------------------
# VictimWatcher
# ---------------------------------------------------------------------------

class VictimWatcher:
    """Monitor de proteccion activo con healthcheck, Wayback y twscrape."""

    def __init__(self, case_id: str, config: dict = None):
        self.case_id        = case_id
        self.config         = config or {}
        self.victim         = None
        self.red_protegida  = []
        self.interval_h     = self.config.get("shield_interval_hours", 4)
        self._scheduler     = None
        self._seen_ids: set = set()
        self._alert_log     = []
        self._data_dir      = os.path.join("data", self.case_id, "shield")
        os.makedirs(self._data_dir, exist_ok=True)
        self._load_seen_ids()

    # ── Persistencia ────────────────────────────────────────────────────────
    def _load_seen_ids(self):
        p = os.path.join(self._data_dir, "seen_ids.json")
        try:
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    self._seen_ids = set(json.load(f))
        except Exception:
            self._seen_ids = set()

    def _save_seen_ids(self):
        p = os.path.join(self._data_dir, "seen_ids.json")
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(list(self._seen_ids)[-2000:], f)
        except Exception:
            pass

    def _guardar_amenaza(self, alert: dict) -> str:
        fname = f"alerta_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{alert['nivel']}.json"
        fpath = os.path.join(self._data_dir, fname)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(alert, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_action(f"Save error: {e}", "ERROR")
        return fpath

    def listar_amenazas(self) -> list:
        alerts = []
        try:
            for fname in sorted(os.listdir(self._data_dir), reverse=True):
                if fname.startswith("alerta_") and fname.endswith(".json"):
                    with open(os.path.join(self._data_dir, fname), encoding="utf-8") as f:
                        alerts.append(json.load(f))
        except Exception:
            pass
        return alerts

    # ── Notificaciones ───────────────────────────────────────────────────────
    def _telegram(self, msg: str):
        tg = self.config.get("telegram", {})
        token, chat = tg.get("bot_token", ""), tg.get("chat_id", "")
        if not token or not chat:
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat, "text": msg, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception as e:
            log_action(f"Telegram error: {e}", "WARNING")

    def _email(self, subject: str, body: str):
        em = self.config.get("email", {})
        if not em.get("enabled"):
            return
        try:
            with smtplib.SMTP_SSL(em["smtp_host"], em.get("smtp_port", 465)) as s:
                s.login(em["username"], em["password"])
                raw = (f"From: {em['from']}\r\nTo: {em['to']}\r\n"
                       f"Subject: {subject}\r\n\r\n{body}")
                s.sendmail(em["from"], em["to"], raw.encode("utf-8"))
        except Exception as e:
            log_action(f"Email error: {e}", "WARNING")

    def _send_alert(self, nivel: str, tweet: dict, victima: str):
        icon = "🚨" if nivel == "AMENAZA" else "⚠️"
        archived = tweet.get("archived_url", "")
        archive_line = f"\nArchivado: {archived}" if archived else ""
        msg = (
            f"{icon} <b>{nivel}</b> contra @{victima}\n"
            f"Autor: {tweet['author']}\n"
            f"Texto: {tweet['text'][:280]}\n"
            f"URL: {tweet.get('url', '')}{archive_line}\n"
            f"Fecha: {tweet.get('date', '')}"
        )
        self._telegram(msg)
        self._email(f"[LINCE] {nivel} contra @{victima}",
                    msg.replace("<b>", "").replace("</b>", ""))

    # ── Escaneo ──────────────────────────────────────────────────────────────
    def _collect_tweets(self, username: str) -> list:
        """
        Reune tweets de todas las fuentes disponibles, sin duplicados.
        Prioridad: twscrape > Nitter (mejor instancia) > DDG
        """
        tweets: list  = []
        seen_ids: set = set()

        def _add(batch):
            for tw in batch:
                if tw["id"] not in seen_ids:
                    tweets.append(tw)
                    seen_ids.add(tw["id"])

        # 1. twscrape (más fiable si está configurado)
        if TWSCRAPE_OK:
            t = _run_twscrape_sync(username, limit=50)
            if t:
                _add(t)
                log_action(f"twscrape: {len(t)} tweets @{username}", "INFO")

        # 2. Nitter — solo instancias vivas (healthcheck)
        if not tweets:
            best = _best_nitter()
            if best:
                t = _fetch_nitter(username, best)
                if t:
                    _add(t)
                    src = "Scrapling" if SCRAPLING_OK else "requests"
                    log_action(f"Nitter ({best}): {len(t)} tweets @{username} via {src}", "INFO")
            else:
                log_action("Nitter: ninguna instancia disponible", "WARNING")

        # 3. DDG como complemento siempre
        t = _fetch_ddg(username)
        _add(t)
        if t:
            log_action(f"DDG: {len(t)} resultados @{username}", "INFO")

        return tweets

    def _scan_user(self, username: str) -> list:
        nuevas = []
        tweets = self._collect_tweets(username)

        src_label = (
            "twscrape" if TWSCRAPE_OK else
            ("Scrapling+stealth" if SCRAPLING_STEALTH else
             ("Scrapling" if SCRAPLING_OK else "requests"))
        )
        if tweets:
            print(f"{Fore.CYAN}    {len(tweets)} entradas — {src_label}{Style.RESET_ALL}")

        for tw in tweets:
            if tw["id"] in self._seen_ids:
                continue
            self._seen_ids.add(tw["id"])

            nivel = _clasificar(tw["text"])
            if not nivel:
                continue

            # MEJORA #8: archivar automaticamente en Wayback Machine
            archived_url = ""
            if tw.get("url"):
                print(f"{Fore.CYAN}    Archivando evidencia en Wayback Machine...{Style.RESET_ALL}")
                archived_url = _wayback_archive(tw["url"])
                if archived_url:
                    print(f"{Fore.GREEN}    Archivado: {archived_url}{Style.RESET_ALL}")

            alert = {
                "nivel":        nivel,
                "victima":      username,
                "autor":        tw["author"],
                "texto":        tw["text"],
                "url":          tw["url"],
                "archived_url": archived_url,
                "fecha":        tw["date"],
                "source":       tw.get("source", "nitter"),
                "detectado":    datetime.now().isoformat(),
            }
            self._guardar_amenaza(alert)
            self._alert_log.append(alert)
            tw["archived_url"] = archived_url
            self._send_alert(nivel, tw, username)
            nuevas.append(alert)
            log_action(
                f"ALERTA {nivel} | {tw['author']} -> @{username} | "
                f"{tw['text'][:60]}", "CRITICAL"
            )

        self._save_seen_ids()
        return nuevas

    def _detect_coordination(self, alertas: list):
        if len(alertas) < 3:
            return
        autores = set(a["autor"] for a in alertas)
        if len(autores) >= 3:
            msg = (f"COORDINACION DETECTADA: {len(autores)} cuentas "
                   f"atacando:\n" + "\n".join(autores))
            self._telegram(msg)
            self._email("[LINCE] ATAQUE COORDINADO", msg)
            log_action(f"Coordinacion: {autores}", "CRITICAL")
            self._guardar_amenaza({
                "nivel": "COORDINACION",
                "autores": list(autores),
                "n_ataques": len(alertas),
                "detectado": datetime.now().isoformat(),
            })

    def scan_now(self) -> list:
        if not self.victim:
            print(f"{Fore.RED}  Error: victima no definida.{Style.RESET_ALL}")
            return []

        print(f"\n{Fore.CYAN}  Escaneando @{self.victim}...{Style.RESET_ALL}")
        todas = self._scan_user(self.victim)

        for amigo in self.red_protegida:
            print(f"{Fore.CYAN}  Escaneando red: @{amigo}...{Style.RESET_ALL}")
            todas += self._scan_user(amigo)
            time.sleep(2)

        self._detect_coordination(todas)

        n_am = sum(1 for a in todas if a["nivel"] == "AMENAZA")
        n_vi = sum(1 for a in todas if a["nivel"] == "VIGILANCIA")
        n_ar = sum(1 for a in todas if a.get("archived_url"))

        print(f"\n{Fore.YELLOW}  Resultado:{Style.RESET_ALL}")
        print(f"  {'Amenazas graves (Art.169)':.<32} {Fore.RED}{n_am}{Style.RESET_ALL}")
        print(f"  {'Vigilancia leve (Art.173)':.<32} {Fore.YELLOW}{n_vi}{Style.RESET_ALL}")
        print(f"  {'Archivadas en Wayback':.<32} {Fore.GREEN}{n_ar}{Style.RESET_ALL}")

        if todas:
            print(f"\n{Fore.RED}  ALERTAS:{Style.RESET_ALL}")
            for a in todas:
                c = Fore.RED if a["nivel"] == "AMENAZA" else Fore.YELLOW
                print(f"  {c}[{a['nivel']}]{Style.RESET_ALL} {a['autor']}: {a['texto'][:75]}")
                if a.get("archived_url"):
                    print(f"    {Fore.GREEN}Wayback: {a['archived_url']}{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.GREEN}  Sin nuevas alertas.{Style.RESET_ALL}")

        return todas

    # ── MEJORA #4 — Exportar alertas a PDF ─────────────────────────────────
    def export_alerts_pdf(self, output_path: str = "") -> str:
        """
        Exporta todas las alertas guardadas a un .docx listo para imprimir.
        (python-docx ya esta instalado; usamos docx en vez de reportlab)
        """
        try:
            from docx import Document
            from docx.shared import Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            print(f"{Fore.RED}  python-docx no instalado.{Style.RESET_ALL}")
            return ""

        alertas = self.listar_amenazas()
        if not alertas:
            print(f"{Fore.YELLOW}  No hay alertas para exportar.{Style.RESET_ALL}")
            return ""

        doc = Document()
        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Portada
        titulo = doc.add_paragraph()
        titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = titulo.add_run("REGISTRO DE AMENAZAS DIGITALES")
        r.bold, r.font.size = True, Pt(18)
        r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)

        doc.add_paragraph()
        info = doc.add_paragraph()
        info.alignment = WD_ALIGN_PARAGRAPH.CENTER
        info.add_run(
            f"Victima: @{self.victim or 'N/D'} | "
            f"Caso: {self.case_id} | Generado: {now}"
        )
        doc.add_page_break()

        # Tabla resumen
        n_am = sum(1 for a in alertas if a.get("nivel") == "AMENAZA")
        n_vi = sum(1 for a in alertas if a.get("nivel") == "VIGILANCIA")
        n_co = sum(1 for a in alertas if a.get("nivel") == "COORDINACION")
        n_ar = sum(1 for a in alertas if a.get("archived_url"))

        doc.add_heading("1. Resumen", level=1)
        t = doc.add_table(rows=5, cols=2)
        t.style = "Table Grid"
        for i, (k, v) in enumerate([
            ("Total alertas",           str(len(alertas))),
            ("Amenazas graves (Art.169 CP)", str(n_am)),
            ("Vigilancia leve (Art.173 CP)", str(n_vi)),
            ("Ataques coordinados",     str(n_co)),
            ("Archivadas Wayback",      str(n_ar)),
        ]):
            t.cell(i, 0).text = k
            t.cell(i, 1).text = v
            t.cell(i, 0).paragraphs[0].runs[0].bold = True

        doc.add_page_break()
        doc.add_heading("2. Detalle de alertas", level=1)

        for i, a in enumerate(alertas, 1):
            nivel = a.get("nivel", "?")
            color = (RGBColor(0xC0, 0x00, 0x00) if nivel == "AMENAZA"
                     else RGBColor(0xC0, 0x80, 0x00))
            p = doc.add_paragraph()
            h = p.add_run(f"[{i}] {nivel} — {a.get('detectado','')[:16]}")
            h.bold = True
            try:
                h.font.color.rgb = color
            except Exception:
                pass

            rows = [
                ("Autor",     a.get("autor", "")),
                ("Victima",   f"@{a.get('victima','')}"),
                ("Texto",     a.get("texto", "")),
                ("URL",       a.get("url", "")),
                ("Archivado", a.get("archived_url", "N/D")),
                ("Fuente",    a.get("source", "")),
                ("Fecha",     a.get("fecha", "")),
            ]
            if nivel == "COORDINACION":
                rows = [
                    ("Autores",   ", ".join(a.get("autores", []))),
                    ("N ataques", str(a.get("n_ataques", 0))),
                    ("Detectado", a.get("detectado", "")),
                ]

            tbl = doc.add_table(rows=len(rows), cols=2)
            tbl.style = "Table Grid"
            for j, (k, v) in enumerate(rows):
                tbl.cell(j, 0).text = k
                tbl.cell(j, 1).text = str(v)[:200]
                tbl.cell(j, 0).paragraphs[0].runs[0].bold = True
            doc.add_paragraph()

        # Guardar
        if not output_path:
            report_dir = os.path.join("reports", self.case_id)
            os.makedirs(report_dir, exist_ok=True)
            output_path = os.path.join(
                report_dir,
                f"alertas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            )
        doc.save(output_path)
        log_action(f"Alertas exportadas: {output_path}", "INFO")
        print(f"{Fore.GREEN}  Exportado: {output_path}{Style.RESET_ALL}")
        return output_path

    # ── Scheduler ────────────────────────────────────────────────────────────
    def start(self) -> bool:
        if not APScheduler_OK:
            print(f"{Fore.RED}  pip install apscheduler{Style.RESET_ALL}")
            return False
        if self._scheduler and self._scheduler.running:
            print(f"{Fore.YELLOW}  Ya en ejecucion.{Style.RESET_ALL}")
            return False
        if not self.victim:
            print(f"{Fore.RED}  Define la victima primero.{Style.RESET_ALL}")
            return False
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(
            self.scan_now, "interval",
            hours=self.interval_h, id="victim_watcher", max_instances=1,
        )
        self._scheduler.start()
        log_action(f"Monitor iniciado @{self.victim} c/{self.interval_h}h", "INFO")
        return True

    def stop(self):
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        log_action("Monitor detenido", "INFO")

    def is_running(self) -> bool:
        return bool(self._scheduler and self._scheduler.running)

    # ── Display ──────────────────────────────────────────────────────────────
    def show_status(self):
        estado = (f"{Fore.GREEN}ACTIVO{Style.RESET_ALL}"
                  if self.is_running() else f"{Fore.RED}INACTIVO{Style.RESET_ALL}")
        fetch_label = (
            f"{Fore.GREEN}twscrape{Style.RESET_ALL}" if TWSCRAPE_OK else
            f"{Fore.GREEN}Scrapling+Stealth{Style.RESET_ALL}" if SCRAPLING_STEALTH else
            f"{Fore.YELLOW}Scrapling{Style.RESET_ALL}" if SCRAPLING_OK else
            f"{Fore.RED}requests{Style.RESET_ALL}"
        )
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  VICTIM WATCHER — Estado{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"  {'Estado':.<28} {estado}")
        print(f"  {'Fetcher':.<28} {fetch_label}")
        print(f"  {'Victima':.<28} {('@' + self.victim) if self.victim else 'No definida'}")
        print(f"  {'Red protegida':.<28} {len(self.red_protegida)} cuentas")
        print(f"  {'Intervalo':.<28} cada {self.interval_h}h")

        alertas = self.listar_amenazas()
        n_am = sum(1 for a in alertas if a.get("nivel") == "AMENAZA")
        n_vi = sum(1 for a in alertas if a.get("nivel") == "VIGILANCIA")
        n_co = sum(1 for a in alertas if a.get("nivel") == "COORDINACION")
        n_ar = sum(1 for a in alertas if a.get("archived_url"))

        print(f"  {'Alertas totales':.<28} {len(alertas)}")
        print(f"  {'  Amenazas (Art.169)':.<28} {Fore.RED}{n_am}{Style.RESET_ALL}")
        print(f"  {'  Vigilancia (Art.173)':.<28} {Fore.YELLOW}{n_vi}{Style.RESET_ALL}")
        print(f"  {'  Coordinadas':.<28} {Fore.MAGENTA}{n_co}{Style.RESET_ALL}")
        print(f"  {'  Archivadas Wayback':.<28} {Fore.GREEN}{n_ar}{Style.RESET_ALL}")

        if alertas:
            print(f"\n{Fore.YELLOW}  Ultimas 5:{Style.RESET_ALL}")
            for a in alertas[:5]:
                nivel = a.get("nivel", "?")
                c  = Fore.RED if nivel == "AMENAZA" else (
                     Fore.MAGENTA if nivel == "COORDINACION" else Fore.YELLOW)
                ts = a.get("detectado", "")[:16]
                autor = a.get("autor", str(a.get("autores", "")))
                texto = a.get("texto", "")[:55]
                wb = " [WB]" if a.get("archived_url") else ""
                print(f"    {c}[{nivel}]{Style.RESET_ALL} {ts} | {autor}{wb}")
                if texto:
                    print(f"      {texto}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
