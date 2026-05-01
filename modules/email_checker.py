#!/usr/bin/env python3
"""
Modulo de verificacion de email - tecnica inspirada en Holehe
Detecta si un email esta registrado en una plataforma analizando
la respuesta del endpoint de recuperacion/reset de contrasena.
Sin necesidad de contraseñas ni autenticacion.
"""

import requests
import re
import time
import json
from bs4 import BeautifulSoup
from colorama import Fore, Style
from modules.utils import log_action

# ---------------------------------------------------------------------------
# Definicion de plataformas y sus endpoints de reset
# ---------------------------------------------------------------------------
# Formato de cada entrada:
#   'method'      : 'POST' o 'GET'
#   'url'         : endpoint de recuperacion
#   'data_field'  : nombre del campo de email en el form
#   'data_extra'  : campos adicionales fijos (dict)
#   'csrf_url'    : URL de donde extraer el token CSRF (opcional)
#   'csrf_field'  : nombre del campo CSRF (opcional)
#   'csrf_selector': selector CSS del input CSRF (opcional)
#   'found_strings'    : lista de textos que indican EMAIL REGISTRADO
#   'not_found_strings': lista de textos que indican EMAIL NO REGISTRADO
#   'notes'       : descripcion del metodo de deteccion

PLATFORMS = {
    'GitHub': {
        'method':       'POST',
        'url':          'https://github.com/password_reset',
        'data_field':   'email',
        'data_extra':   {},
        'csrf_url':     'https://github.com/password_reset',
        'csrf_field':   'authenticity_token',
        'csrf_selector':'input[name="authenticity_token"]',
        'found_strings':    ['check your email', 'we have sent', 'correo electronico'],
        'not_found_strings':['no account found', 'we couldn\'t find', 'no se encontro'],
        'notes': 'Respuesta diferente segun si el email existe o no',
    },
    'Instagram': {
        'method':       'POST',
        'url':          'https://www.instagram.com/accounts/account_recovery_send_ajax/',
        'data_field':   'email_or_username',
        'data_extra':   {},
        'csrf_url':     'https://www.instagram.com/accounts/password/reset/',
        'csrf_field':   'csrfmiddlewaretoken',
        'csrf_selector':'input[name="csrfmiddlewaretoken"]',
        'found_strings':    ['we sent a login link', 'sent an email', 'enviamos'],
        'not_found_strings':['no users found', 'no account found', 'no encontramos'],
        'notes': 'Endpoint AJAX de recuperacion de cuenta',
    },
    'Spotify': {
        'method':       'POST',
        'url':          'https://accounts.spotify.com/api/send-password-reset-email',
        'data_field':   'email',
        'data_extra':   {},
        'csrf_url':     None,
        'csrf_field':   None,
        'csrf_selector': None,
        'found_strings':    ['check your email', 'sent a link', 'we\'ve sent'],
        'not_found_strings':['no account', 'email not found', 'no existe'],
        'notes': 'API directa de reset de Spotify',
    },
    'Twitch': {
        'method':       'POST',
        'url':          'https://passport.twitch.tv/password_reset_request',
        'data_field':   'email',
        'data_extra':   {'client_id': 'kimne78kx3ncx6brgo4mv6wki5h1ko'},
        'csrf_url':     None,
        'csrf_field':   None,
        'csrf_selector': None,
        'found_strings':    ['check your email', 'correo enviado', 'email sent'],
        'not_found_strings':['email not found', 'no account', 'no user'],
        'notes': 'API passport de Twitch',
    },
    'Discord': {
        'method':       'POST',
        'url':          'https://discord.com/api/v9/auth/forgot',
        'data_field':   'email',
        'data_extra':   {},
        'csrf_url':     None,
        'csrf_field':   None,
        'csrf_selector': None,
        'found_strings':    [],   # Discord responde 200 sin mensaje aunque no exista
        'not_found_strings':[],
        'notes': 'Discord devuelve 200 siempre; usa analisis de status_code',
    },
    'Snapchat': {
        'method':       'POST',
        'url':          'https://accounts.snapchat.com/accounts/password_reset_request',
        'data_field':   'email',
        'data_extra':   {},
        'csrf_url':     'https://accounts.snapchat.com/accounts/password_reset_request',
        'csrf_field':   'xsrf_token',
        'csrf_selector': 'input[name="xsrf_token"]',
        'found_strings':    ['check your email', 'sent an email', 'email sent'],
        'not_found_strings':['no account', 'no encontramos', 'not registered'],
        'notes': 'Formulario web de reset de Snapchat',
    },
    'Duolingo': {
        'method':       'POST',
        'url':          'https://www.duolingo.com/api/1/password_reset_by_email',
        'data_field':   'email',
        'data_extra':   {},
        'csrf_url':     None,
        'csrf_field':   None,
        'csrf_selector': None,
        'found_strings':    ['check your email', 'email sent'],
        'not_found_strings':['no account', 'email not found'],
        'notes': 'API de reset de Duolingo',
    },
    'Steam': {
        'method':       'POST',
        'url':          'https://store.steampowered.com/password/forgetpassword',
        'data_field':   'email',
        'data_extra':   {},
        'csrf_url':     'https://store.steampowered.com/join/',
        'csrf_field':   'sessionid',
        'csrf_selector': None,
        'found_strings':    ['check your email', 'we\'ve sent', 'enviamos'],
        'not_found_strings':['no match', 'no account', 'no se encontro'],
        'notes': 'Formulario de reset de Steam',
    },
    'Patreon': {
        'method':       'POST',
        'url':          'https://www.patreon.com/api/auth?include=[]',
        'data_field':   'data[attributes][email]',
        'data_extra':   {'data[type]': 'user', 'data[attributes][forgot]': 'true'},
        'csrf_url':     None,
        'csrf_field':   None,
        'csrf_selector': None,
        'found_strings':    ['check your email', 'email sent'],
        'not_found_strings':['no account', 'not found'],
        'notes': 'API JSON de Patreon (formato JSON:API)',
    },
    'Adobe': {
        'method':       'POST',
        'url':          'https://auth.services.adobe.com/en_US/index.html#fromCSS',
        'data_field':   'email',
        'data_extra':   {},
        'csrf_url':     None,
        'csrf_field':   None,
        'csrf_selector': None,
        'found_strings':    ['we\'ve sent', 'check your email', 'email sent'],
        'not_found_strings':['account not found', 'no account', 'not exist'],
        'notes': 'Formulario de reset de Adobe',
    },
    'Dropbox': {
        'method':       'POST',
        'url':          'https://www.dropbox.com/forgot',
        'data_field':   'email',
        'data_extra':   {},
        'csrf_url':     'https://www.dropbox.com/forgot',
        'csrf_field':   't',
        'csrf_selector': 'input[name="t"]',
        'found_strings':    ['check your email', 'we sent', 'email sent'],
        'not_found_strings':['no account', 'email not found'],
        'notes': 'Formulario de reset de Dropbox',
    },
    'WordPress.com': {
        'method':       'GET',
        'url':          'https://wordpress.com/wp-login.php?action=lostpassword&redirect_to=&email={email}',
        'data_field':   'user_login',
        'data_extra':   {'action': 'lostpassword'},
        'csrf_url':     None,
        'csrf_field':   None,
        'csrf_selector': None,
        'found_strings':    ['check your email', 'we have sent', 'email sent'],
        'not_found_strings':['no account', 'invalid', 'no user'],
        'notes': 'Endpoint perdida de contrasena de WordPress.com',
    },
}


class EmailChecker:
    """
    Verifica si un email esta registrado en multiples plataformas
    usando la tecnica de analisis de endpoint de recuperacion de contrasena.
    No requiere autenticacion ni contrasena.
    """

    HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.0.0 Safari/537.36'
        ),
        'Accept':          'text/html,application/xhtml+xml,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.5,en;q=0.3',
        'DNT':             '1',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    # -----------------------------------------------------------------------
    # EXTRACCION DE TOKEN CSRF
    # -----------------------------------------------------------------------
    def _get_csrf_token(self, csrf_url, csrf_field, csrf_selector, timeout=8):
        """
        Carga la pagina de reset y extrae el token CSRF usando el selector CSS.
        Retorna el token como string o None si no se encuentra.
        """
        if not csrf_url:
            return None
        try:
            resp = self.session.get(csrf_url, timeout=timeout)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, 'html.parser')
            if csrf_selector:
                el = soup.select_one(csrf_selector)
                if el:
                    return el.get('value', '')
            # Fallback: buscar input con nombre = csrf_field
            if csrf_field:
                el = soup.find('input', {'name': csrf_field})
                if el:
                    return el.get('value', '')
            # Fallback: buscar en cookies
            if csrf_field and csrf_field in self.session.cookies:
                return self.session.cookies[csrf_field]
        except Exception as e:
            log_action(f"CSRF error en {csrf_url}: {e}", "WARNING")
        return None

    # -----------------------------------------------------------------------
    # ANALISIS DE RESPUESTA
    # -----------------------------------------------------------------------
    def _analyze_response(self, platform_cfg, status_code, response_text):
        """
        Determina si el email esta registrado segun la respuesta HTTP.
        Retorna: 'found' | 'not_found' | 'unknown'
        """
        content_lower = response_text.lower() if response_text else ''

        # Textos que confirman que el email EXISTE
        for pattern in platform_cfg.get('found_strings', []):
            if pattern.lower() in content_lower:
                return 'found'

        # Textos que confirman que el email NO existe
        for pattern in platform_cfg.get('not_found_strings', []):
            if pattern.lower() in content_lower:
                return 'not_found'

        # Sin coincidencias en texto → usar codigo HTTP como fallback
        if status_code == 200:
            return 'unknown'
        elif status_code in (400, 404, 422):
            return 'not_found'
        elif status_code in (500, 503):
            return 'error'

        return 'unknown'

    # -----------------------------------------------------------------------
    # VERIFICACION DE UN EMAIL EN UNA PLATAFORMA
    # -----------------------------------------------------------------------
    def check_platform(self, platform_name, email, timeout=10):
        """
        Verifica si el email esta registrado en una plataforma especifica.
        Retorna dict: {status, status_code, platform, email}
        """
        cfg = PLATFORMS.get(platform_name)
        if not cfg:
            return {'status': 'unsupported', 'platform': platform_name, 'email': email}

        result = {'platform': platform_name, 'email': email, 'status': 'unknown', 'status_code': None}

        try:
            # Paso 1: obtener CSRF si es necesario
            csrf_token = None
            if cfg.get('csrf_url'):
                csrf_token = self._get_csrf_token(
                    cfg['csrf_url'], cfg.get('csrf_field'), cfg.get('csrf_selector'), timeout
                )

            # Paso 2: preparar datos del formulario
            data = dict(cfg.get('data_extra', {}))
            data[cfg['data_field']] = email
            if csrf_token and cfg.get('csrf_field'):
                data[cfg['csrf_field']] = csrf_token

            # Paso 3: enviar la peticion
            method = cfg.get('method', 'POST').upper()
            url = cfg['url']

            if method == 'POST':
                resp = self.session.post(url, data=data, timeout=timeout, allow_redirects=True)
            else:
                # GET con email en URL si el template lo incluye
                url_final = url.format(email=email)
                resp = self.session.get(url_final, timeout=timeout, allow_redirects=True)

            result['status_code'] = resp.status_code

            # Paso 4: analizar respuesta
            result['status'] = self._analyze_response(cfg, resp.status_code, resp.text)

        except requests.exceptions.Timeout:
            result['status'] = 'timeout'
        except requests.exceptions.ConnectionError:
            result['status'] = 'connection_error'
        except Exception as e:
            result['status'] = 'error'
            log_action(f"EmailChecker {platform_name}: {e}", "ERROR")

        return result

    # -----------------------------------------------------------------------
    # VERIFICACION COMPLETA (todos los servicios)
    # -----------------------------------------------------------------------
    def check_email(self, email, delay=1.2):
        """
        Verifica el email en todas las plataformas configuradas.
        Muestra resultados en tiempo real y retorna lista de hallazgos.
        """
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  VERIFICACION DE EMAIL: {email}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  Tecnica: analisis de endpoint de recuperacion (Holehe){Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  Plataformas: {len(PLATFORMS)}{Style.RESET_ALL}\n")

        found      = []
        not_found  = []
        unknown    = []
        errors     = []

        for platform_name, cfg in PLATFORMS.items():
            print(
                f"  {Fore.CYAN}[~] {platform_name:<20}{Style.RESET_ALL}",
                end=' ', flush=True
            )

            result = self.check_platform(platform_name, email)
            status = result['status']
            code   = result.get('status_code', '?')

            if status == 'found':
                found.append(platform_name)
                print(f"{Fore.GREEN}REGISTRADO  (HTTP {code}){Style.RESET_ALL}")
                log_action(f"Email {email} encontrado en {platform_name}", "WARNING")

            elif status == 'not_found':
                not_found.append(platform_name)
                print(f"{Fore.RED}no registrado{Style.RESET_ALL}")

            elif status == 'timeout':
                errors.append(platform_name)
                print(f"{Fore.YELLOW}timeout{Style.RESET_ALL}")

            elif status in ('connection_error', 'error'):
                errors.append(platform_name)
                print(f"{Fore.RED}error de red{Style.RESET_ALL}")

            else:
                # unknown: no se pudo determinar
                unknown.append(platform_name)
                print(f"{Fore.YELLOW}sin datos (HTTP {code}){Style.RESET_ALL}")

            time.sleep(delay)

        # ---- RESUMEN ----
        print(f"\n{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  RESULTADOS PARA: {email}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")

        if found:
            print(f"\n{Fore.GREEN}  REGISTRADO EN ({len(found)}):{Style.RESET_ALL}")
            for p in found:
                print(f"  {Fore.GREEN}  [+] {p}{Style.RESET_ALL}")

        if not_found:
            print(f"\n{Fore.RED}  No registrado ({len(not_found)}):{Style.RESET_ALL}")
            for p in not_found:
                print(f"  {Fore.RED}  [-] {p}{Style.RESET_ALL}")

        if unknown:
            print(f"\n{Fore.YELLOW}  Sin datos ({len(unknown)}):{Style.RESET_ALL}")
            for p in unknown:
                print(f"  {Fore.YELLOW}  [?] {p}{Style.RESET_ALL}")

        if errors:
            print(f"\n{Fore.RED}  Errores de red ({len(errors)}):{Style.RESET_ALL}")
            for p in errors:
                print(f"  {Fore.RED}  [!] {p}{Style.RESET_ALL}")

        print(f"\n{Fore.CYAN}  Nota: los resultados 'sin datos' pueden necesitar{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  verificacion manual (captcha, JS requerido, etc.){Style.RESET_ALL}\n")

        return {
            'email':     email,
            'found':     found,
            'not_found': not_found,
            'unknown':   unknown,
            'errors':    errors,
        }
