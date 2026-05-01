#!/usr/bin/env python3
"""
Modulo de investigacion digital - rastreo de huella digital
Estrategia: API publica donde existe, HTML parsing donde no, manual para JS-only
"""

import requests
import time
import json
import os
import random
from datetime import datetime
from bs4 import BeautifulSoup
from tqdm import tqdm
from colorama import Fore, Style
from modules.utils import log_action, validate_url

# ---------------------------------------------------------------------------
# Plataformas con API publica fiable (no necesitan proxies, sin falsos positivos)
# ---------------------------------------------------------------------------
API_PLATFORMS = {
    'GitHub': {
        'api_url':    'https://api.github.com/users/{username}',
        'profile_url':'https://github.com/{username}',
        'headers':    {'Accept': 'application/vnd.github.v3+json'},
        # 200 = existe, 404 = no existe
    },
    'Reddit': {
        'api_url':    'https://www.reddit.com/user/{username}/about.json',
        'profile_url':'https://reddit.com/user/{username}',
        'headers':    {'User-Agent': 'cazador-cazado:v2.0 (investigacion legal)'},
        # 200 + kind=t2 = existe, 404 = no existe
    },
}

# ---------------------------------------------------------------------------
# Plataformas JS-only: sin API publica ni HTML util.
# Se muestran siempre para verificacion manual del investigador.
# ---------------------------------------------------------------------------
MANUAL_PLATFORMS = {
    'X (Twitter)':  'https://x.com/{username}',
    'Facebook':     'https://facebook.com/{username}',
    'LinkedIn':     'https://linkedin.com/in/{username}',
}

# ---------------------------------------------------------------------------
# Plataformas donde HTTP 404 = usuario no existe con total certeza
# No hace falta analizar HTML, el codigo de estado es suficiente
# ---------------------------------------------------------------------------
PLATFORMS_404 = {
    # Originales
    'BitBucket', 'DevTo', 'Kaggle', 'Replit', 'CodePen',
    'HackerNews', 'Keybase', 'Vimeo', 'Dribbble', 'Behance',
    # Nuevas (404 definitivo = usuario no existe; 200 = existe sin analizar HTML)
    'HuggingFace', 'PyPI', 'npm',
    'Last.fm', 'Wattpad', 'Letterboxd',
    'Duolingo', 'Lichess', 'AO3', 'itch.io',
}

CACHE_FILE = os.path.join('data', 'username_cache.json')


class DigitalInvestigator:
    """Clase para investigar la huella digital de un objetivo"""

    def __init__(self, case_id='CASE-DEFAULT'):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        })
        self._proxies = self._load_proxies()
        self._proxy_index = 0
        self._case_id = case_id

    # -----------------------------------------------------------------------
    # PROXY SUPPORT (opcional, configurable en config.yaml)
    # -----------------------------------------------------------------------
    def _load_proxies(self):
        """Carga lista de proxies desde config.yaml si esta configurada"""
        try:
            import yaml
            if os.path.exists('config.yaml'):
                with open('config.yaml', 'r', encoding='utf-8') as f:
                    cfg = yaml.safe_load(f)
                proxies = cfg.get('network', {}).get('proxies', [])
                if proxies:
                    return [p for p in proxies if p and isinstance(p, str)]
        except Exception:
            pass
        return []

    def _get_next_proxy(self):
        """Rota al siguiente proxy de la lista"""
        if not self._proxies:
            return None
        proxy = self._proxies[self._proxy_index % len(self._proxies)]
        self._proxy_index += 1
        return {'http': proxy, 'https': proxy}

    # -----------------------------------------------------------------------
    # CACHE POR USERNAME
    # -----------------------------------------------------------------------
    def _load_cache(self):
        """Carga el cache de busquedas previas"""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_cache(self, cache):
        """Guarda el cache de busquedas"""
        os.makedirs('data', exist_ok=True)
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # BUSQUEDA PRINCIPAL
    # -----------------------------------------------------------------------
    def search_username(self, username):
        """Buscar un nombre de usuario en multiples plataformas"""

        # Plataformas a chequear por HTML (65 plataformas organizadas por categoria)
        html_platforms = {
            # ── REDES SOCIALES GENERALES ───────────────────────────────────────
            'Instagram':     f'https://instagram.com/{username}',
            'TikTok':        f'https://tiktok.com/@{username}',
            'Pinterest':     f'https://pinterest.com/{username}',
            'Snapchat':      f'https://snapchat.com/add/{username}',
            'Tumblr':        f'https://{username}.tumblr.com',
            'VK':            f'https://vk.com/{username}',
            'OK':            f'https://ok.ru/{username}',
            'Minds':         f'https://www.minds.com/{username}',
            # ── MENSAJERIA / COMUNIDAD ────────────────────────────────────────
            'Telegram':      f'https://t.me/{username}',
            'Mastodon':      f'https://mastodon.social/@{username}',
            'Keybase':       f'https://keybase.io/{username}',
            # ── VIDEO / STREAMING ─────────────────────────────────────────────
            'Twitch':        f'https://twitch.tv/{username}',
            'Vimeo':         f'https://vimeo.com/{username}',
            'Dailymotion':   f'https://www.dailymotion.com/{username}',
            'Rumble':        f'https://rumble.com/user/{username}',
            # ── MUSICA ────────────────────────────────────────────────────────
            'SoundCloud':    f'https://soundcloud.com/{username}',
            'Spotify':       f'https://open.spotify.com/user/{username}',
            'Bandcamp':      f'https://{username}.bandcamp.com',
            'Last.fm':       f'https://www.last.fm/user/{username}',
            # ── FOTOGRAFIA / ARTE ─────────────────────────────────────────────
            'Flickr':        f'https://flickr.com/people/{username}',
            'DeviantArt':    f'https://www.deviantart.com/{username}',
            'ArtStation':    f'https://www.artstation.com/{username}',
            'Behance':       f'https://www.behance.net/{username}',
            'Dribbble':      f'https://dribbble.com/{username}',
            '500px':         f'https://500px.com/p/{username}',
            'Unsplash':      f'https://unsplash.com/@{username}',
            # ── BLOGS / ESCRITURA ─────────────────────────────────────────────
            'Medium':        f'https://medium.com/@{username}',
            'WordPress':     f'https://{username}.wordpress.com',
            'Blogger':       f'https://{username}.blogspot.com',
            'Substack':      f'https://{username}.substack.com',
            'Wattpad':       f'https://www.wattpad.com/user/{username}',
            'AO3':           f'https://archiveofourown.org/users/{username}',
            # ── ENLACES / PERFIL PUBLICO ──────────────────────────────────────
            'About.me':      f'https://about.me/{username}',
            'Linktree':      f'https://linktr.ee/{username}',
            # ── TECH / DESARROLLO ─────────────────────────────────────────────
            'GitLab':        f'https://gitlab.com/{username}',
            'BitBucket':     f'https://bitbucket.org/{username}',
            'StackOverflow': f'https://stackoverflow.com/users/{username}',
            'HackerNews':    f'https://news.ycombinator.com/user?id={username}',
            'CodePen':       f'https://codepen.io/{username}',
            'Replit':        f'https://replit.com/@{username}',
            'Kaggle':        f'https://kaggle.com/{username}',
            'DevTo':         f'https://dev.to/{username}',
            'Hashnode':      f'https://hashnode.com/@{username}',
            'HuggingFace':   f'https://huggingface.co/{username}',
            'npm':           f'https://www.npmjs.com/~{username}',
            'PyPI':          f'https://pypi.org/user/{username}/',
            'itch.io':       f'https://{username}.itch.io',
            # ── GAMING ────────────────────────────────────────────────────────
            'Steam':         f'https://steamcommunity.com/id/{username}',
            'Chess.com':     f'https://www.chess.com/member/{username}',
            'Lichess':       f'https://lichess.org/@/{username}',
            'Newgrounds':    f'https://{username}.newgrounds.com',
            # ── PROFESIONAL / FREELANCE ───────────────────────────────────────
            'ProductHunt':   f'https://producthunt.com/@{username}',
            'Fiverr':        f'https://www.fiverr.com/{username}',
            'AngelList':     f'https://angel.co/u/{username}',
            'Freelancer':    f'https://www.freelancer.com/u/{username}',
            # ── CROWDFUNDING / APOYO ──────────────────────────────────────────
            'Patreon':       f'https://patreon.com/{username}',
            'Ko-fi':         f'https://ko-fi.com/{username}',
            'Kickstarter':   f'https://www.kickstarter.com/profile/{username}',
            # ── OCIO / CULTURA ────────────────────────────────────────────────
            'Letterboxd':    f'https://letterboxd.com/{username}',
            'Duolingo':      f'https://www.duolingo.com/profile/{username}',
            'Goodreads':     f'https://www.goodreads.com/{username}',
        }

        # --- Cargar cache ---
        cache = self._load_cache()
        user_cache = cache.get(username, {})

        # Mostrar resultados del cache
        cached_found = {p: d for p, d in user_cache.items() if d['status'] == 'found'}
        if cached_found:
            print(f"\n{Fore.CYAN}[CACHE] Resultados previos para {username}:{Style.RESET_ALL}")
            for p, d in cached_found.items():
                print(f"  {Fore.GREEN}[+] {p}: {d['url']}  (cache {d['ts'][:10]}){Style.RESET_ALL}")

        # Decidir que plataformas verificar en esta sesion:
        # - found / not_found -> saltar (ya sabemos)
        # - blocked / error   -> reintentar
        # - ausente            -> verificar por primera vez
        skip_statuses = {'found', 'not_found'}

        api_to_check = {
            p: v for p, v in API_PLATFORMS.items()
            if user_cache.get(p, {}).get('status') not in skip_statuses
        }
        html_to_check = {
            p: u for p, u in html_platforms.items()
            if user_cache.get(p, {}).get('status') not in skip_statuses
        }
        manual_to_check = {
            p: u.format(username=username) for p, u in MANUAL_PLATFORMS.items()
            if user_cache.get(p, {}).get('status') not in skip_statuses
        }

        total_http = len(api_to_check) + len(html_to_check)
        skipped = len(user_cache) - len(
            [p for p, d in user_cache.items() if d['status'] not in skip_statuses]
        )

        if skipped:
            print(f"{Fore.YELLOW}  (Saltando {skipped} plataformas ya verificadas){Style.RESET_ALL}")

        print(f"\n{Fore.CYAN}Iniciando busqueda para: {username}{Style.RESET_ALL}\n")

        results = dict(cached_found)  # Incluir resultados del cache
        blocked = []

        # ---- PLATAFORMAS CON API PUBLICA ----
        for platform, pdata in api_to_check.items():
            api_url = pdata['api_url'].format(username=username)
            profile_url = pdata['profile_url'].format(username=username)
            extra_headers = pdata.get('headers', {})

            print(f"  {Fore.CYAN}[API] {platform:<22}{Style.RESET_ALL}", end=' ', flush=True)
            try:
                status, content = self._fetch_with_retry(
                    api_url, extra_headers=extra_headers
                )
                cache_entry = {'url': profile_url, 'ts': datetime.now().isoformat()}

                if status == 200:
                    # Para Reddit verificar que sea un usuario real (kind=t2)
                    if platform == 'Reddit':
                        try:
                            data = json.loads(content)
                            exists = data.get('kind') == 't2'
                        except Exception:
                            exists = True  # Si no parsea JSON, asumir encontrado
                    else:
                        exists = True

                    if exists:
                        results[platform] = profile_url
                        cache_entry['status'] = 'found'
                        # Extraer datos del perfil desde JSON de API
                        try:
                            api_json = json.loads(content) if content else {}
                            profile = {}
                            if platform == 'GitHub':
                                profile = {
                                    'display_name': api_json.get('name') or api_json.get('login', ''),
                                    'bio':          (api_json.get('bio') or '')[:400],
                                    'avatar_url':   api_json.get('avatar_url', ''),
                                    'followers':    api_json.get('followers', 0),
                                    'location':     api_json.get('location', ''),
                                }
                            elif platform == 'Reddit':
                                rd = api_json.get('data', {})
                                profile = {
                                    'display_name': rd.get('name', ''),
                                    'bio':          (rd.get('subreddit', {}).get('public_description') or '')[:400],
                                    'avatar_url':   rd.get('icon_img', ''),
                                    'followers':    rd.get('total_karma', 0),
                                }
                            profile = {k: v for k, v in profile.items() if v}
                            if profile:
                                cache_entry['profile'] = profile
                                name_str = f"  [{profile.get('display_name', '')}]" if profile.get('display_name') else ''
                                print(f"{Fore.GREEN}ENCONTRADO -> {profile_url}{name_str}{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.GREEN}ENCONTRADO -> {profile_url}{Style.RESET_ALL}")
                        except Exception:
                            print(f"{Fore.GREEN}ENCONTRADO -> {profile_url}{Style.RESET_ALL}")
                    else:
                        cache_entry['status'] = 'not_found'
                        print(f"{Fore.RED}no encontrado{Style.RESET_ALL}")

                elif status == 404:
                    cache_entry['status'] = 'not_found'
                    print(f"{Fore.RED}no existe (404){Style.RESET_ALL}")

                elif status in (429, 503):
                    cache_entry['status'] = 'blocked'
                    blocked.append(platform)
                    print(f"{Fore.YELLOW}bloqueado temporalmente{Style.RESET_ALL}")

                elif status in (401, 403):
                    cache_entry['status'] = 'blocked'
                    print(f"{Fore.YELLOW}acceso restringido{Style.RESET_ALL}")

                elif status is None:
                    cache_entry['status'] = 'error'
                    print(f"{Fore.RED}error de red{Style.RESET_ALL}")
                else:
                    cache_entry['status'] = 'error'
                    print(f"{Fore.RED}respuesta inesperada ({status}){Style.RESET_ALL}")

                user_cache[platform] = cache_entry
                log_action(f"[API] {platform}: status={status}", "INFO")
                time.sleep(0.4)

            except Exception as e:
                print(f"{Fore.RED}error: {e}{Style.RESET_ALL}")
                log_action(f"[API] {platform} excepcion: {e}", "ERROR")

        # ---- PLATAFORMAS HTML ----
        if html_to_check:
            bar_fmt = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            with tqdm(html_to_check.items(), total=len(html_to_check),
                      desc="  HTML  ", unit="sitio",
                      bar_format=bar_fmt, ncols=70) as pbar:

                for platform, url in pbar:
                    pbar.set_description(f"  {platform[:22]:<22}")
                    cache_entry = {'url': url, 'ts': datetime.now().isoformat()}

                    try:
                        proxy = self._get_next_proxy() if self._proxies else None
                        status, content = self._fetch_with_retry(url, proxies=proxy)

                        if status == 404:
                            cache_entry['status'] = 'not_found'
                            log_action(f"{platform}: 404", "INFO")

                        elif status in (429, 503):
                            cache_entry['status'] = 'blocked'
                            blocked.append(platform)
                            tqdm.write(
                                f"  {Fore.YELLOW}[!] {platform}: bloqueado "
                                f"(rate limit){Style.RESET_ALL}"
                            )

                        elif status in (401, 403):
                            cache_entry['status'] = 'blocked'
                            tqdm.write(
                                f"  {Fore.YELLOW}[~] {platform}: acceso restringido{Style.RESET_ALL}"
                            )

                        elif status == 200:
                            if platform in PLATFORMS_404:
                                # Para estas, 200 es suficiente
                                exists = True
                            else:
                                exists = self._check_platform_content(
                                    platform, content or '', username
                                )

                            if exists:
                                results[platform] = url
                                cache_entry['status'] = 'found'
                                # Extraer datos reales del perfil (og: + JSON-LD)
                                if content:
                                    profile = self._extract_profile_data(
                                        platform, content, username
                                    )
                                    if profile:
                                        cache_entry['profile'] = profile
                                        name_str = (
                                            f"  [{profile['display_name']}]"
                                            if profile.get('display_name') else ''
                                        )
                                        tqdm.write(
                                            f"  {Fore.GREEN}[+] {platform}: ENCONTRADO  -> {url}"
                                            f"{name_str}{Style.RESET_ALL}"
                                        )
                                    else:
                                        tqdm.write(
                                            f"  {Fore.GREEN}[+] {platform}: ENCONTRADO  -> {url}{Style.RESET_ALL}"
                                        )
                                    self.download_avatar(
                                        platform, content, username, self._case_id
                                    )
                                else:
                                    tqdm.write(
                                        f"  {Fore.GREEN}[+] {platform}: ENCONTRADO  -> {url}{Style.RESET_ALL}"
                                    )
                            else:
                                cache_entry['status'] = 'not_found'

                            log_action(f"{platform}: encontrado={exists}", "INFO")

                        elif status is None:
                            cache_entry['status'] = 'error'

                        user_cache[platform] = cache_entry
                        time.sleep(0.5)

                    except Exception as e:
                        cache_entry['status'] = 'error'
                        user_cache[platform] = cache_entry
                        log_action(f"Error en {platform}: {e}", "ERROR")

        # ---- PLATAFORMAS MANUALES (JS-only) ----
        if manual_to_check:
            print(f"\n{Fore.YELLOW}Plataformas con verificacion manual requerida "
                  f"(renderizado JavaScript):{Style.RESET_ALL}")
            for platform, url in manual_to_check.items():
                print(f"  {Fore.CYAN}[?] {platform:<16} -> {url}{Style.RESET_ALL}")
                user_cache[platform] = {
                    'status': 'manual',
                    'url': url,
                    'ts': datetime.now().isoformat()
                }

        # Guardar cache actualizado
        cache[username] = user_cache
        self._save_cache(cache)

        # ---- RESUMEN ----
        found_count = len([p for p in results if p not in cached_found])
        cached_count = len(cached_found)
        total_verified = len(user_cache)

        print(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}RESULTADOS: {username}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        if cached_count:
            print(f"{Fore.CYAN}  Del cache (sesiones previas) : {cached_count}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  Encontrados esta sesion      : {found_count}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  Total encontrados            : {len(results)}{Style.RESET_ALL}")
        print(f"{Fore.RED}  No encontrados               : "
              f"{len([p for p,d in user_cache.items() if d['status']=='not_found'])}{Style.RESET_ALL}")
        if blocked:
            print(f"{Fore.YELLOW}  Bloqueados (reintentar)      : {len(blocked)}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  -> {', '.join(blocked)}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Espera unos minutos y vuelve a buscar el mismo username.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Solo se reintentaran las plataformas bloqueadas.{Style.RESET_ALL}")
        if manual_to_check:
            print(f"{Fore.CYAN}  Verificar manualmente        : {len(manual_to_check)}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  (X, Facebook, LinkedIn requieren navegador){Style.RESET_ALL}")

        return results

    # -----------------------------------------------------------------------
    # FETCH CON REINTENTOS
    # -----------------------------------------------------------------------
    def _fetch_with_retry(self, url, retries=2, timeout=10,
                          extra_headers=None, proxies=None):
        """
        GET con reintentos. Devuelve (status_code, content) o (None, None).
        """
        headers = {}
        if extra_headers:
            headers.update(extra_headers)

        for attempt in range(retries):
            try:
                resp = self.session.get(
                    url,
                    timeout=timeout,
                    allow_redirects=True,
                    verify=True,
                    headers=headers if headers else None,
                    proxies=proxies,
                )
                return resp.status_code, resp.text
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    time.sleep(1.5)
                    continue
                return None, None
            except requests.exceptions.ConnectionError:
                return None, None
            except Exception as e:
                log_action(f"Fetch error {url}: {e}", "ERROR")
                return None, None

    # -----------------------------------------------------------------------
    # DETECCION DE CONTENIDO HTML
    # -----------------------------------------------------------------------
    def _check_platform_content(self, platform, content, username):
        """
        Determina si un perfil existe analizando el HTML.
        Capas:
          1. Patrones de 'no encontrado' (texto especifico) -> False
          2. Indicadores positivos especificos por plataforma -> True
          3. og:title / title con el username -> True
          4. Si no hay certeza -> False (conservador)
        """
        content_lower = content.lower()
        uname = username.lower().lstrip('@')

        # ---- CAPA 1: patrones de NO encontrado ----
        not_found_map = {
            # ── REDES SOCIALES ────────────────────────────────────────────────
            'Instagram': [
                "sorry, this page isn't available",
                "lo sentimos, esta pagina no esta disponible",
                "page not found",
            ],
            'TikTok': [
                "couldn't find this account",
                "this account does not exist",
                "page not found",
                "no se pudo encontrar esta cuenta",
            ],
            'Facebook': [
                "page not found",
                "this content isn't available",
                "the link you followed may have expired",
            ],
            'Pinterest': [
                "we couldn't find that page",
                "page not found",
            ],
            'Snapchat': [
                "page not found",
                "this page doesn't exist",
            ],
            'Tumblr': [
                "there's nothing here",
                "this tumblr doesn't exist",
            ],
            'VK': [
                "this page has been deleted",
                "user not found",
                "this profile is private",
            ],
            'OK': [
                "page not found",
                "user not found",
                "this page does not exist",
            ],
            'Minds': [
                "page not found",
                "this user does not exist",
                "channel not found",
            ],
            # ── MENSAJERIA / COMUNIDAD ────────────────────────────────────────
            'Mastodon': [
                "account not found",
                "this profile does not exist",
            ],
            # ── VIDEO / STREAMING ─────────────────────────────────────────────
            'Twitch': [
                "this channel doesn't exist",
                "sorry. unless you've",
                "page not found",
            ],
            'Dailymotion': [
                "this channel doesn't exist",
                "oops! we couldn't find",
                "page not found",
                "channel not found",
            ],
            'Rumble': [
                "page not found",
                "user not found",
                "channel not found",
            ],
            # ── MUSICA ────────────────────────────────────────────────────────
            'Spotify': [
                "page not found",
                "couldn't find that page",
                "pagina no encontrada",
            ],
            'Bandcamp': [
                "sorry, that something went wrong",
                "we couldn't find",
                "page not found",
                "there's nothing here",
            ],
            # ── FOTOGRAFIA / ARTE ─────────────────────────────────────────────
            'Flickr': [
                "the page you're looking for can't be found",
                "we couldn't find",
                "page not found",
                "this member doesn't exist",
            ],
            'DeviantArt': [
                "not a deviantart member",
                "we couldn't find",
                "page not found",
                "isn't a deviantart member",
            ],
            'ArtStation': [
                "page not found",
                "this page doesn't exist",
                "we couldn't find",
            ],
            '500px': [
                "page not found",
                "the page you requested was not found",
                "user not found",
            ],
            'Unsplash': [
                "we couldn't find that page",
                "page not found",
                "user not found",
            ],
            # ── BLOGS / ESCRITURA ─────────────────────────────────────────────
            'WordPress': [
                "doesn't exist",
                "this site does not exist",
                "no existe",
            ],
            'Blogger': [
                "blog not found",
                "this blog does not exist",
                "no existe",
            ],
            'Substack': [
                "this publication could not be found",
                "page not found",
                "doesn't exist",
                "no publication found",
            ],
            # ── ENLACES / PERFIL PUBLICO ──────────────────────────────────────
            'About.me': [
                "we couldn't find",
                "page not found",
                "this profile does not exist",
            ],
            'Linktree': [
                "sorry, this page doesn't exist",
                "page not found",
                "this linktree doesn't exist",
            ],
            # ── TECH / DESARROLLO ─────────────────────────────────────────────
            'GitLab': [
                "page not found",
                "404 - page not found",
                "the page you're looking for could not be found",
            ],
            'StackOverflow': [
                "page not found",
                "user not found",
            ],
            'Hashnode': [
                "this page could not be found",
                "page not found",
            ],
            # ── GAMING ────────────────────────────────────────────────────────
            'Steam': [
                "the specified profile could not be found",
                "error: no user",
                "profile not found",
                "no se encontro el perfil",
            ],
            'Chess.com': [
                "page not found",
                "we couldn't find this user",
                "user not found",
            ],
            'Newgrounds': [
                "there's nothing here",
                "page not found",
                "we can't find",
            ],
            # ── PROFESIONAL / FREELANCE ───────────────────────────────────────
            'ProductHunt': [
                "page not found",
                "we couldn't find",
            ],
            'Fiverr': [
                "this page isn't available",
                "page not found",
                "user not found",
            ],
            'AngelList': [
                "page not found",
                "we couldn't find",
                "user not found",
            ],
            'Freelancer': [
                "user not found",
                "page not found",
                "this user does not exist",
            ],
            # ── CROWDFUNDING / APOYO ──────────────────────────────────────────
            'Patreon': [
                "page not found",
                "this creator doesn't exist",
            ],
            'Ko-fi': [
                "this page could not be found",
                "page not found",
                "we couldn't find",
            ],
            'Kickstarter': [
                "page not found",
                "this profile doesn't exist",
                "user not found",
            ],
            # ── OCIO / CULTURA ────────────────────────────────────────────────
            'Goodreads': [
                "page not found",
                "user not found",
                "the page you requested doesn't exist",
            ],
        }

        for indicator in not_found_map.get(platform, []):
            if indicator in content_lower:
                return False

        # ---- CAPA 2: indicadores positivos especificos ----

        # Telegram: 'tgme_page_title' solo aparece en perfiles que EXISTEN
        if platform == 'Telegram':
            return 'tgme_page_title' in content

        # SoundCloud y Vimeo: usan og:url con el username
        if platform in ('SoundCloud', 'Vimeo'):
            try:
                soup = BeautifulSoup(content, 'html.parser')
                og_url = soup.find('meta', property='og:url')
                if og_url and uname in og_url.get('content', '').lower():
                    return True
                og_title = soup.find('meta', property='og:title')
                if og_title and uname in og_title.get('content', '').lower():
                    return True
            except Exception:
                pass
            return False

        # ---- CAPA 3: og:title o <title> con el username ----
        try:
            soup = BeautifulSoup(content, 'html.parser')

            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                if uname in og_title['content'].lower():
                    return True

            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                if uname in title_tag.string.lower():
                    return True

            h1 = soup.find('h1')
            if h1 and h1.get_text():
                if uname in h1.get_text().lower():
                    return True

        except Exception:
            pass

        # ---- CAPA 4: sin certeza -> no asumimos que existe ----
        return False

    # -----------------------------------------------------------------------
    # EXTRACCION DE DATOS DE PERFIL
    # -----------------------------------------------------------------------
    def _extract_profile_data(self, platform, content, username):
        """
        Extrae datos reales del perfil desde og: meta tags y JSON-LD.
        Retorna dict con: display_name, bio, avatar_url, followers, location.
        Funciona para cualquier plataforma que emita Open Graph tags.
        """
        data = {}
        try:
            soup = BeautifulSoup(content, 'html.parser')

            # ── og:title → display_name ──────────────────────────────────────
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content'].strip()
                # Eliminar sufijos genericos: " | Instagram", " • Twitter", etc.
                for sep in [' | ', ' • ', ' - ', ' – ', ' (@', ' (on ']:
                    if sep in title:
                        title = title.split(sep)[0].strip()
                if title and title.lower() not in ('page not found', '404', 'error'):
                    data['display_name'] = title

            # ── og:description → bio ─────────────────────────────────────────
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                bio = og_desc['content'].strip()
                if bio and len(bio) > 5:
                    data['bio'] = bio[:400]

            # Fallback bio: meta description
            if 'bio' not in data:
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    bio = meta_desc['content'].strip()
                    if bio and len(bio) > 5:
                        data['bio'] = bio[:400]

            # ── og:image → avatar_url ────────────────────────────────────────
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                img = og_img['content'].strip()
                if img.startswith('http'):
                    data['avatar_url'] = img

            # Fallback: twitter:image
            if 'avatar_url' not in data:
                tw_img = soup.find('meta', attrs={'name': 'twitter:image'})
                if tw_img and tw_img.get('content', '').startswith('http'):
                    data['avatar_url'] = tw_img['content'].strip()

            # ── JSON-LD (schema.org Person / ProfilePage) ────────────────────
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    raw = script.string or ''
                    if not raw.strip():
                        continue
                    jld = json.loads(raw)
                    # Puede ser lista o dict
                    items = jld if isinstance(jld, list) else [jld]
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        dtype = item.get('@type', '')
                        if dtype not in ('Person', 'ProfilePage', 'MusicGroup',
                                         'Organization', 'SportsTeam'):
                            continue
                        if 'name' in item and 'display_name' not in data:
                            data['display_name'] = str(item['name'])[:100]
                        if 'description' in item and 'bio' not in data:
                            data['bio'] = str(item['description'])[:400]
                        if 'image' in item and 'avatar_url' not in data:
                            img = item['image']
                            if isinstance(img, dict):
                                img = img.get('url', '')
                            if isinstance(img, str) and img.startswith('http'):
                                data['avatar_url'] = img
                        if 'address' in item and 'location' not in data:
                            addr = item['address']
                            if isinstance(addr, dict):
                                loc = addr.get('addressLocality', '')
                                if loc:
                                    data['location'] = loc
                        # Followers desde interactionStatistic
                        for stat in item.get('interactionStatistic', []):
                            if not isinstance(stat, dict):
                                continue
                            itype = stat.get('interactionType', '')
                            if 'Follow' in itype or 'Subscriber' in itype:
                                val = stat.get('userInteractionCount', 0)
                                try:
                                    data['followers'] = int(val)
                                except (ValueError, TypeError):
                                    pass
                except Exception:
                    continue

        except Exception as e:
            log_action(f"_extract_profile_data {platform}: {e}", "WARNING")

        return data

    # -----------------------------------------------------------------------
    # DESCARGA DE AVATAR
    # -----------------------------------------------------------------------
    def download_avatar(self, platform, content, username, case_id):
        """
        Intenta extraer og:image del HTML y guardar el avatar del perfil.
        Retorna la ruta local del archivo o None si no se pudo descargar.
        """
        try:
            soup = BeautifulSoup(content, 'html.parser')

            img_url = None
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                img_url = og_img['content']

            # Fallback: twitter:image
            if not img_url:
                tw_img = soup.find('meta', attrs={'name': 'twitter:image'})
                if tw_img and tw_img.get('content'):
                    img_url = tw_img['content']

            if not img_url or not img_url.startswith('http'):
                return None

            avatar_dir = os.path.join('data', case_id, 'avatars')
            os.makedirs(avatar_dir, exist_ok=True)

            resp = self.session.get(img_url, timeout=10, stream=True)
            if resp.status_code != 200:
                return None

            ct = resp.headers.get('content-type', 'image/jpeg').lower()
            ext = 'png' if 'png' in ct else 'gif' if 'gif' in ct else 'jpg'

            safe_platform = platform.lower().replace(' ', '_').replace('(', '').replace(')', '')
            fname = f"{safe_platform}_{username}.{ext}"
            fpath = os.path.join(avatar_dir, fname)

            with open(fpath, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)

            tqdm.write(
                f"  {Fore.CYAN}[avatar] {platform}: {fname}{Style.RESET_ALL}"
            )
            log_action(f"Avatar descargado: {fname}", "INFO")
            return fpath

        except Exception as e:
            log_action(f"Error descargando avatar de {platform}: {e}", "WARNING")
            return None

    # -----------------------------------------------------------------------
    # COMPARACION DE AVATARES (deteccion multi-cuenta)
    # -----------------------------------------------------------------------
    def compare_all_case_avatars(self, case_id, threshold=0.85):
        """
        Compara todos los avatares descargados en el caso usando pHash.
        Un similarity >= threshold indica que son la misma imagen (misma persona).
        Retorna lista de coincidencias: [{file1, file2, similarity, platform1, platform2}]
        """
        try:
            from PIL import Image
            import imagehash
        except ImportError:
            print(f"{Fore.RED}Instala imagehash: pip install imagehash{Style.RESET_ALL}")
            return []

        avatar_dir = os.path.join('data', case_id, 'avatars')
        if not os.path.exists(avatar_dir):
            return []

        files = [
            f for f in os.listdir(avatar_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))
        ]

        if len(files) < 2:
            return []

        # Calcular pHash de cada avatar
        hashes = {}
        for fname in files:
            try:
                img = Image.open(os.path.join(avatar_dir, fname)).convert('RGB')
                hashes[fname] = imagehash.phash(img)
            except Exception as e:
                log_action(f"No se pudo hashear {fname}: {e}", "WARNING")

        # Comparar todos los pares
        matches = []
        fnames = list(hashes.keys())
        for i in range(len(fnames)):
            for j in range(i + 1, len(fnames)):
                f1, f2 = fnames[i], fnames[j]
                h1, h2 = hashes[f1], hashes[f2]
                distance   = h1 - h2          # Distancia Hamming (0=identicas)
                similarity = 1.0 - distance / 64.0

                if similarity >= threshold:
                    # Extraer nombre de plataforma del nombre de archivo
                    plat1 = f1.split('_')[0].replace('-', ' ').title()
                    plat2 = f2.split('_')[0].replace('-', ' ').title()
                    matches.append({
                        'file1':      f1,
                        'file2':      f2,
                        'platform1':  plat1,
                        'platform2':  plat2,
                        'similarity': round(similarity * 100, 1),
                        'distance':   distance,
                    })
                    log_action(
                        f"Avatar similar: {f1} <-> {f2} sim={similarity:.0%}",
                        "WARNING"
                    )

        return matches

    def show_avatar_comparison(self, case_id, threshold=0.85):
        """Muestra en consola el resultado de la comparacion de avatares."""
        print(f"\n{Fore.CYAN}Comparando avatares del caso {case_id}...{Style.RESET_ALL}")
        matches = self.compare_all_case_avatars(case_id, threshold)

        avatar_dir = os.path.join('data', case_id, 'avatars')
        n_avatars = len(os.listdir(avatar_dir)) if os.path.exists(avatar_dir) else 0
        print(f"{Fore.CYAN}Avatares descargados: {n_avatars}{Style.RESET_ALL}")

        if not matches:
            print(f"{Fore.GREEN}No se detectaron avatares similares entre plataformas.{Style.RESET_ALL}")
            return []

        print(f"\n{Fore.RED}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.RED}  ALERTA: POSIBLE MULTI-CUENTA DETECTADA ({len(matches)} coincidencias){Style.RESET_ALL}")
        print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}\n")

        for m in matches:
            bar_len = int(m['similarity'] / 100 * 20)
            bar = '#' * bar_len + '-' * (20 - bar_len)
            print(
                f"  {Fore.YELLOW}{m['platform1']:<18}{Style.RESET_ALL}"
                f" <-> "
                f"{Fore.YELLOW}{m['platform2']:<18}{Style.RESET_ALL}"
                f"  [{bar}]  {m['similarity']}%"
            )
            print(f"    {m['file1']}  <->  {m['file2']}")

        print(f"\n{Fore.YELLOW}  Misma imagen en distintas plataformas = probable mismo individuo.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  Guarda esta comparacion como evidencia en el informe.{Style.RESET_ALL}\n")
        return matches

    # -----------------------------------------------------------------------
    # BUSQUEDA INVERSA DE IMAGEN
    # -----------------------------------------------------------------------
    def reverse_image_search(self, image_path, engine='1'):
        """Generar URL de busqueda inversa para abrir en navegador"""
        print(f"\n{Fore.CYAN}Busqueda inversa de imagen{Style.RESET_ALL}")

        engines = {
            '1': {'name': 'Google Images',
                  'url': 'https://www.google.com/searchbyimage?image_url={}&safe=off'},
            '2': {'name': 'Yandex Images',
                  'url': 'https://yandex.com/images/search?url={}&rpt=imageview'},
            '3': {'name': 'TinEye',
                  'url': 'https://www.tineye.com/search?url={}'},
            '4': {'name': 'Bing Visual',
                  'url': 'https://www.bing.com/images/search?q=imgurl:{}&view=detailv2'},
        }

        selected = engines.get(engine, engines['1'])
        print(f"{Fore.YELLOW}Motor: {selected['name']}{Style.RESET_ALL}")

        results = []
        if os.path.exists(image_path):
            image_size = os.path.getsize(image_path)
            print(f"{Fore.CYAN}Tamano: {image_size:,} bytes  |  Ruta: {image_path}{Style.RESET_ALL}")
            search_url = selected['url'].format(image_path)
            print(f"\n{Fore.GREEN}URL generada (abre en tu navegador):{Style.RESET_ALL}")
            print(f"  {search_url}")
            results.append(search_url)
            log_action(f"URL busqueda inversa generada: {image_path}", "INFO")
        else:
            print(f"{Fore.RED}La imagen no existe en esa ruta{Style.RESET_ALL}")

        return results

    # -----------------------------------------------------------------------
    # BUSQUEDA POR TELEFONO
    # -----------------------------------------------------------------------
    def search_phone_number(self, phone):
        """Buscar informacion publica de un numero de telefono"""
        print(f"\n{Fore.RED}ADVERTENCIA: requiere consentimiento legal{Style.RESET_ALL}")
        consent = input(
            f"{Fore.YELLOW}Tienes consentimiento para buscar este numero? (s/n): {Style.RESET_ALL}"
        )
        if consent.lower() != 's':
            print(f"{Fore.RED}Busqueda cancelada{Style.RESET_ALL}")
            return []

        public_sources = [
            f'https://www.truecaller.com/search/es/{phone}',
            f'https://www.whitepages.com/phone/{phone}',
        ]
        results = []
        for source in public_sources:
            try:
                r = self.session.get(source, timeout=8)
                if r.status_code == 200:
                    results.append(f'Posible informacion en: {source}')
            except Exception:
                pass
        return results
