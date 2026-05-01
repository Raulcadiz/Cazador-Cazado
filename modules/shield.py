#!/usr/bin/env python3
"""
LINCE — Modulo Escudo de Proteccion
Dashboard en vivo, guia de privacidad para Espana,
plantillas de denuncia por plataforma y documento legal PDF/DOCX.
"""

import os
import json
import time
from datetime import datetime
from colorama import Fore, Style

from modules.utils import log_action

# -----------------------------------------------------------------------
# MARCO LEGAL ESPANOL (actualizado 2026)
# -----------------------------------------------------------------------
MARCO_LEGAL = {
    'Codigo Penal': [
        ('Art. 169-171 CP', 'Amenazas — pena hasta 5 anos prison'),
        ('Art. 172 CP',     'Coacciones'),
        ('Art. 173 CP',     'Trato degradante / acoso (stalking) — hasta 2 anos'),
        ('Art. 172 ter CP', 'Acoso reiterado (stalking digital) — hasta 5 anos si victima vulnerable'),
        ('Art. 197 CP',     'Descubrimiento y revelacion de secretos (privacidad)'),
        ('Art. 197 bis CP', 'Acceso ilegal a sistemas informaticos'),
        ('Art. 208-210 CP', 'Injurias y calumnias publicas'),
        ('Art. 183 ter CP', 'Grooming / ciberacoso a menores'),
    ],
    'Proteccion de Datos': [
        ('LOPD-GDD (LO 3/2018)', 'Ley Organica de Proteccion de Datos Personales'),
        ('RGPD (EU 2016/679)',   'Reglamento General de Proteccion de Datos'),
        ('AEPD',                 'Agencia Espanola de Proteccion de Datos — denuncia en aepd.es'),
    ],
    'Recursos de Ayuda': [
        ('016',                      'Violencia de genero (llamada gratuita, 24h)'),
        ('GDT - Policia Nacional',   'Grupo de Delitos Telematicos: www.policia.es/denuncia_web'),
        ('INCIBE',                   'Instituto Nac. Ciberseguridad: incibe.es | 017'),
        ('AEPD',                     'Agencia Espanola Proteccion Datos: aepd.es'),
        ('Fiscalia',                 'Fiscalia de Violencia sobre la Mujer: fiscal.es'),
        ('OSI',                      'Oficina Seguridad Internauta: osi.es'),
    ],
}

# -----------------------------------------------------------------------
# PLANTILLAS DE DENUNCIA POR PLATAFORMA
# -----------------------------------------------------------------------
REPORT_TEMPLATES = {
    'Instagram': {
        'url':  'https://www.instagram.com/support',
        'path': 'Perfil → ··· → Denunciar → Acoso o intimidacion',
        'api_url': 'https://www.instagram.com/abusive_content_reporting/',
        'consejos': [
            'Captura la URL completa del perfil denunciado',
            'Guarda screenshot de cada mensaje/publicacion ofensiva',
            'Usa "Denunciar publicacion" en cada contenido individualmente',
            'Selecciona: Acoso → Me acosa o acosa a alguien que conozco',
            'Bloquea el perfil DESPUES de denunciar (no antes, pierdes evidencia)',
        ],
    },
    'X (Twitter)': {
        'url':  'https://help.twitter.com/forms/abusiveuser',
        'path': 'Perfil → ··· → Denunciar → Acoso',
        'api_url': 'https://help.twitter.com/en/safety-and-security/report-abusive-behavior',
        'consejos': [
            'Descarga el archivo de datos del acosador si es cuenta publica',
            'Denuncia cada tweet individualmente + el perfil',
            'Solicita suspension de cuenta en el formulario de abuso',
            'Si hay amenazas directas: usa "Amenaza de violencia"',
            'Guarda el numero de caso que te asigna Twitter al denunciar',
        ],
    },
    'TikTok': {
        'url':  'https://www.tiktok.com/legal/report/user',
        'path': 'Perfil → Compartir → Denunciar → Acoso/Intimidacion',
        'api_url': 'https://www.tiktok.com/legal/report/user',
        'consejos': [
            'Denuncia cada video por separado y el perfil',
            'Selecciona: Acoso e intimidacion → Amenazas o me asusta',
            'Si es menor de edad el acosado: marca proteccion de menores',
            'TikTok tiene equipo de seguridad 24h para casos urgentes',
        ],
    },
    'Facebook': {
        'url':  'https://www.facebook.com/help/contact/274459462613911',
        'path': 'Perfil → ··· → Buscar soporte o denunciar',
        'api_url': 'https://www.facebook.com/help/323..',
        'consejos': [
            'Denuncia el perfil Y cada publicacion/mensaje por separado',
            'Usa el Centro de ayuda para reportar casos graves directamente',
            'Si hay suplantacion de identidad: formulario especifico de Meta',
            'Guarda el ID de perfil (numerico) para la denuncia policial',
        ],
    },
    'YouTube': {
        'url':  'https://support.google.com/youtube/answer/2802027',
        'path': 'Video → ··· → Informar → Acoso o bullying',
        'api_url': 'https://support.google.com/youtube/troubleshooter/2672146',
        'consejos': [
            'Denuncia canal + cada video individualmente',
            'Guarda URL completa de cada video como evidencia',
            'Si hay doxxing (publicacion datos personales): urgente',
            'Los canales monetizados son revisados mas rapidamente',
        ],
    },
    'Telegram': {
        'url':  'https://telegram.org/support',
        'path': 'Perfil → ··· → Denunciar spam',
        'api_url': 'https://t.me/notoscam',
        'consejos': [
            'Reenviar mensajes a @notoscam para denunciar bots/spam',
            'Para acoso en grupos: denuncia el grupo a spam@telegram.org',
            'Incluye el username y mensajes en el email',
            'Telegram no tiene soporte por telefono, solo email/bot',
        ],
    },
}

# -----------------------------------------------------------------------
# CONSEJOS DE PRIVACIDAD Y SEGURIDAD
# -----------------------------------------------------------------------
PRIVACY_TIPS = [
    # Configuracion inmediata
    ('URGENTE - Hacer ahora', [
        'Cambia tu contrasena de email y activa autenticacion en 2 pasos (2FA)',
        'Haz privadas TODAS tus cuentas de redes sociales',
        'Elimina tu numero de telefono de los perfiles publicos',
        'Desactiva la geolocalizacion en fotos antes de publicar',
        'Revisa que apps tienen acceso a tu ubicacion (revoca las innecesarias)',
        'Bloquea al acosador en TODAS las plataformas donde te encontraste',
        'Alerta a amigos y familiares cercanos sobre la situacion',
    ]),
    # Configuraciones de privacidad por plataforma
    ('Configuracion de Privacidad', [
        'Instagram: Configuracion → Privacidad → Cuenta privada [ON]',
        'Instagram: Desactiva "Mostrar estado de actividad"',
        'X/Twitter: Configuracion → Privacidad → Proteger tus Tweets [ON]',
        'TikTok: Perfil → Privacidad → Cuenta privada [ON]',
        'Facebook: Configuracion → Privacidad → Solo yo (para busqueda) [ON]',
        'WhatsApp: Ultima vez → Solo mis contactos | Foto → Solo mis contactos',
        'Google: myaccount.google.com → Datos y privacidad → eliminar rastreadores',
    ]),
    # Evidencia legal
    ('Preservacion de Evidencias', [
        'NO borres NADA: los mensajes borrados son mas dificiles de probar',
        'Haz screenshots con URL visible y fecha del sistema operativo',
        'Guarda los IDs numericos de perfiles (no solo el username)',
        'Exporta historial de chats (WhatsApp → Ajustes → Chats → Exportar)',
        'Pide a testigos que capturen tambien y guarden sus evidencias',
        'Haz copias en 2+ dispositivos diferentes o en la nube cifrada',
        'Anota fecha/hora exacta de cada incidente en un diario',
    ]),
    # Seguridad personal
    ('Seguridad Personal', [
        'Si recibes amenazas fisicas: llama al 112 inmediatamente',
        'Informa a policia local para registro de la situacion',
        'Comunica la situacion a tu trabajo/universidad si es necesario',
        'Considera cambiar rutinas temporalmente si hay acoso fisico',
        'No respondas al acosador: cualquier respuesta puede escalar',
        'Guarda todos los numeros de telefono de emergencia locales',
        'Contacta 016 (violencia de genero) o INCIBE 017 (ciberacoso)',
    ]),
]


class ProtectionShield:
    """
    Escudo de proteccion: dashboard en vivo, guia legal,
    plantillas de denuncia y generacion de documento legal.
    """

    def __init__(self, case_id, analyzer, evidence_collector):
        self.case_id  = case_id
        self.analyzer = analyzer
        self.evidence = evidence_collector

    # -----------------------------------------------------------------------
    # DASHBOARD EN VIVO
    # -----------------------------------------------------------------------
    def live_dashboard(self, investigator, refresh_secs=30, max_cycles=None):
        """
        Dashboard que se refresca automaticamente cada N segundos.
        Muestra riesgo, evidencias, plataformas y alertas en tiempo real.
        Pulsa Ctrl+C para salir.
        """
        from modules.investigator import CACHE_FILE

        cycle = 0
        print(f"{Fore.CYAN}  Dashboard en vivo activo. Ctrl+C para salir.{Style.RESET_ALL}")
        time.sleep(1)

        try:
            while True:
                if max_cycles and cycle >= max_cycles:
                    break

                os.system('cls' if os.name == 'nt' else 'clear')

                now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                evidences = self.evidence.get_all_evidence() if hasattr(self.evidence, 'get_all_evidence') else []

                # Cargar plataformas del cache
                username_results = {}
                try:
                    if os.path.exists(CACHE_FILE):
                        import json as _j
                        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                            cache = _j.load(f)
                        # Buscar el username de cualquier caso activo
                        for uname, data in cache.items():
                            found = {p: d['url'] for p, d in data.items() if d.get('status') == 'found'}
                            if found:
                                username_results.update(found)
                except Exception:
                    pass

                risk = self.analyzer.calculate_risk_level(
                    evidences=evidences,
                    username_results=username_results,
                )

                rcolor = risk['color']
                rlevel = risk['level']
                rscore = risk['score']

                # Header
                print(f"{rcolor}{'='*70}{Style.RESET_ALL}")
                print(f"{rcolor}  LINCE — DASHBOARD EN VIVO  |  {now}  |  Actualizando c/{refresh_secs}s{Style.RESET_ALL}")
                print(f"{rcolor}{'='*70}{Style.RESET_ALL}")

                # Semaforo compacto
                s_alto = f"{Fore.RED}[#]{Style.RESET_ALL}"   if rlevel == 'ALTO'  else "[ ]"
                s_med  = f"{Fore.YELLOW}[#]{Style.RESET_ALL}" if rlevel == 'MEDIO' else "[ ]"
                s_bajo = f"{Fore.GREEN}[#]{Style.RESET_ALL}"  if rlevel == 'BAJO'  else "[ ]"

                print(f"\n  {s_alto} ALTO   {s_med} MEDIO   {s_bajo} BAJO     "
                      f"Score: {rcolor}{rscore}/100  {risk['urgencia']}{Style.RESET_ALL}\n")

                # Stats
                n_ev   = len(evidences)
                n_plat = len(username_results)

                print(f"  {'Evidencias':.<28} {n_ev}")
                print(f"  {'Plataformas confirmadas':.<28} {n_plat}")

                if username_results:
                    print(f"\n  {Fore.GREEN}Cuentas detectadas:{Style.RESET_ALL}")
                    for p, u in list(username_results.items())[:8]:
                        print(f"    {Fore.GREEN}+{Style.RESET_ALL} {p:<18} {u}")

                # Factores de riesgo
                if risk['factors']:
                    print(f"\n  {Fore.CYAN}Factores activos:{Style.RESET_ALL}")
                    for fac in risk['factors']:
                        print(f"    {rcolor}>{Style.RESET_ALL} {fac}")

                if risk['threats']:
                    print(f"\n  {Fore.RED}Lenguaje amenazante detectado: {', '.join(risk['threats'])}{Style.RESET_ALL}")

                # Avatares
                avatar_dir = os.path.join('data', self.case_id, 'avatars')
                if os.path.exists(avatar_dir):
                    n_av = len(os.listdir(avatar_dir))
                    if n_av:
                        print(f"\n  {Fore.CYAN}Avatares descargados: {n_av}{Style.RESET_ALL}")

                print(f"\n{rcolor}{'='*70}{Style.RESET_ALL}")
                print(f"  {Fore.YELLOW}Ctrl+C para salir del dashboard{Style.RESET_ALL}")

                cycle += 1
                time.sleep(refresh_secs)

        except KeyboardInterrupt:
            print(f"\n{Fore.CYAN}  Dashboard cerrado.{Style.RESET_ALL}")

    # -----------------------------------------------------------------------
    # GUIA DE PRIVACIDAD
    # -----------------------------------------------------------------------
    def show_privacy_guide(self):
        """Muestra la guia completa de privacidad y seguridad."""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  GUIA DE PROTECCION Y PRIVACIDAD — ESPANA{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

        for categoria, tips in PRIVACY_TIPS:
            if 'URGENTE' in categoria:
                print(f"\n  {Fore.RED}!!! {categoria} !!!{Style.RESET_ALL}")
            else:
                print(f"\n  {Fore.YELLOW}--- {categoria} ---{Style.RESET_ALL}")
            for tip in tips:
                print(f"    {Fore.GREEN}>{Style.RESET_ALL} {tip}")

        print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"\n  {Fore.YELLOW}MARCO LEGAL:{Style.RESET_ALL}")
        for seccion, items in MARCO_LEGAL.items():
            print(f"\n  {Fore.CYAN}{seccion}:{Style.RESET_ALL}")
            for codigo, desc in items:
                print(f"    {Fore.WHITE}{codigo:<28}{Style.RESET_ALL} {desc}")

        print()

    # -----------------------------------------------------------------------
    # PLANTILLAS DE DENUNCIA EN PLATAFORMAS
    # -----------------------------------------------------------------------
    def show_report_templates(self):
        """Muestra las plantillas de denuncia por plataforma."""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  COMO DENUNCIAR EN CADA PLATAFORMA{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

        plats = list(REPORT_TEMPLATES.keys())
        for i, p in enumerate(plats, 1):
            print(f"  {Fore.GREEN}[{i}]{Style.RESET_ALL} {p}")
        print(f"  {Fore.GREEN}[0]{Style.RESET_ALL} Volver")

        print(f"\n{Fore.CYAN}{'─'*70}{Style.RESET_ALL}")
        opt = input(f"{Fore.YELLOW}Plataforma: {Style.RESET_ALL}").strip()

        try:
            idx = int(opt) - 1
            if idx < 0:
                return
            plat_name = plats[idx]
            tmpl = REPORT_TEMPLATES[plat_name]

            print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  DENUNCIA EN {plat_name.upper()}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
            print(f"\n  {Fore.CYAN}URL de denuncia:{Style.RESET_ALL}")
            print(f"    {tmpl['url']}")
            print(f"\n  {Fore.CYAN}Ruta en la app:{Style.RESET_ALL}")
            print(f"    {tmpl['path']}")
            print(f"\n  {Fore.CYAN}Consejos para esta plataforma:{Style.RESET_ALL}")
            for c in tmpl['consejos']:
                print(f"    {Fore.GREEN}>{Style.RESET_ALL} {c}")
        except (ValueError, IndexError):
            pass

    # -----------------------------------------------------------------------
    # DOCUMENTO LEGAL — ESCUDO
    # -----------------------------------------------------------------------
    def generate_legal_shield(self, target_username='', risk=None):
        """
        Genera el documento 'Escudo Legal' en formato .docx.
        Contiene: resumen del caso, inventario de evidencias,
        marco legal aplicable, instrucciones de denuncia y
        recomendaciones de bloqueo por plataforma.
        """
        try:
            from docx import Document
            from docx.shared import Pt, RGBColor, Inches
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            print(f"{Fore.RED}  Instala python-docx: pip install python-docx{Style.RESET_ALL}")
            return None

        doc = Document()
        now = datetime.now().strftime('%d/%m/%Y %H:%M')

        # --- Estilos base ---
        style = doc.styles['Normal']
        style.font.name = 'Calibri'
        style.font.size = Pt(11)

        def heading(text, level=1, color=None):
            p = doc.add_heading(text, level=level)
            if color:
                for run in p.runs:
                    run.font.color.rgb = RGBColor(*color)
            return p

        def para(text, bold=False, color=None):
            p = doc.add_paragraph()
            run = p.add_run(text)
            run.bold = bold
            if color:
                run.font.color.rgb = RGBColor(*color)
            return p

        def bullet(items, style_name='List Bullet'):
            for item in items:
                p = doc.add_paragraph(item, style=style_name)
            return p

        # ---- PORTADA ----
        doc.add_paragraph()
        t = doc.add_paragraph()
        t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = t.add_run('DOCUMENTO DE ESCUDO LEGAL')
        run.bold = True
        run.font.size = Pt(20)
        run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)

        doc.add_paragraph()
        sub = doc.add_paragraph()
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub.add_run('Herramienta LINCE — Investigacion Forense Digital Etica').bold = True

        doc.add_paragraph()
        info = doc.add_paragraph()
        info.alignment = WD_ALIGN_PARAGRAPH.CENTER
        info.add_run(
            f'Caso ID: {self.case_id}\n'
            f'Objetivo: @{target_username or "no definido"}\n'
            f'Generado: {now}'
        )
        doc.add_page_break()

        # ---- SECCION 1: NIVEL DE RIESGO ----
        heading('1. Evaluacion de Riesgo del Caso', 1, color=(0xC0, 0x00, 0x00))
        if risk:
            rlabel = {'ALTO': 'ALTO — URGENTE', 'MEDIO': 'MEDIO — PRIORITARIO', 'BAJO': 'BAJO — PLANIFICADO'}
            doc.add_paragraph(
                f"Nivel de riesgo: {rlabel.get(risk['level'], risk['level'])}"
            ).runs[0].bold = True
            doc.add_paragraph(f"Puntuacion: {risk['score']}/100")
            doc.add_paragraph(risk['descripcion'])
            if risk.get('factors'):
                heading('Factores detectados:', 2)
                bullet(risk['factors'])
            if risk.get('threats'):
                heading('Lenguaje amenazante detectado:', 2)
                para(
                    'ATENCION: Se han detectado los siguientes terminos amenazantes en las evidencias:',
                    bold=True, color=(0xC0, 0x00, 0x00)
                )
                bullet(risk['threats'])

        # ---- SECCION 2: INVENTARIO DE EVIDENCIAS ----
        doc.add_page_break()
        heading('2. Inventario de Evidencias', 1)

        evidences = []
        try:
            evidences = self.evidence.get_all_evidence() if hasattr(self.evidence, 'get_all_evidence') else []
        except Exception:
            pass

        doc.add_paragraph(f'Total de evidencias recopiladas: {len(evidences)}')

        if evidences:
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Table Grid'
            hdr = table.rows[0].cells
            for i, h in enumerate(['#', 'Tipo', 'Fecha', 'Descripcion/URL']):
                hdr[i].text = h
                hdr[i].paragraphs[0].runs[0].bold = True

            for idx, ev in enumerate(evidences[:50], 1):
                row = table.add_row().cells
                row[0].text = str(idx)
                row[1].text = ev.get('type', '-')
                row[2].text = ev.get('timestamp', '-')[:16]
                url = ev.get('url', ev.get('source', ev.get('text_preview', '')))
                row[3].text = str(url)[:80]
        else:
            doc.add_paragraph('No se han recopilado evidencias todavia.')

        # ---- SECCION 3: PLATAFORMAS CON PRESENCIA ----
        doc.add_page_break()
        heading('3. Presencia en Plataformas Digitales', 1)

        from modules.investigator import CACHE_FILE
        username_results = {}
        try:
            if os.path.exists(CACHE_FILE) and target_username:
                import json as _j
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = _j.load(f)
                udata = cache.get(target_username, {})
                username_results = {p: d['url'] for p, d in udata.items() if d.get('status') == 'found'}
        except Exception:
            pass

        if username_results:
            doc.add_paragraph(f'Se han localizado {len(username_results)} perfiles activos:')
            table2 = doc.add_table(rows=1, cols=2)
            table2.style = 'Table Grid'
            h2 = table2.rows[0].cells
            h2[0].text = 'Plataforma'
            h2[1].text = 'URL del perfil'
            for h in h2:
                h.paragraphs[0].runs[0].bold = True
            for plat, url in username_results.items():
                r = table2.add_row().cells
                r[0].text = plat
                r[1].text = url
        else:
            doc.add_paragraph('No se han localizado perfiles confirmados todavia.')

        # ---- SECCION 4: MARCO LEGAL ----
        doc.add_page_break()
        heading('4. Marco Legal Aplicable (Espana)', 1)

        for seccion, items in MARCO_LEGAL.items():
            heading(seccion, 2)
            for codigo, desc in items:
                p = doc.add_paragraph()
                p.add_run(f'{codigo}: ').bold = True
                p.add_run(desc)

        # ---- SECCION 5: INSTRUCCIONES DE DENUNCIA ----
        doc.add_page_break()
        heading('5. Como Denunciar — Pasos Inmediatos', 1)

        steps = [
            ('1. Policia Nacional — Denuncia Telematica',
             'www.policia.es/denuncia_web → Delitos informaticos',
             'Adjunta: capturas de pantalla, URLs, fechas, hashes SHA-256 de las evidencias.'),
            ('2. AEPD — Si hay violacion de privacidad',
             'www.aepd.es → Sede electronica → Reclamaciones',
             'Para casos de doxxing, publicacion de datos personales sin consentimiento.'),
            ('3. Fiscalia de Violencia Digital',
             'www.fiscal.es',
             'Para casos graves con amenazas fisicas o acoso reiterado.'),
            ('4. Plataformas directamente',
             'Ver guia de denuncia por plataforma en seccion siguiente',
             'Denuncia simultaneamente a las plataformas digitales donde se produce el acoso.'),
        ]

        for title, url, desc in steps:
            heading(title, 2)
            para(url, bold=True)
            para(desc)

        # ---- SECCION 6: INSTRUCCIONES DE BLOQUEO ----
        doc.add_page_break()
        heading('6. Instrucciones de Bloqueo por Plataforma', 1)

        for plat, tmpl in REPORT_TEMPLATES.items():
            heading(plat, 2)
            p = doc.add_paragraph()
            p.add_run('URL de denuncia: ').bold = True
            p.add_run(tmpl['url'])
            p = doc.add_paragraph()
            p.add_run('Ruta en app: ').bold = True
            p.add_run(tmpl['path'])
            para('Consejos:', bold=True)
            bullet(tmpl['consejos'])

        # ---- SECCION 7: RECOMENDACIONES DE PRIVACIDAD ----
        doc.add_page_break()
        heading('7. Recomendaciones de Privacidad y Seguridad', 1)

        for categoria, tips in PRIVACY_TIPS:
            heading(categoria, 2)
            bullet(tips)

        # ---- PIE ----
        doc.add_page_break()
        footer_para = doc.add_paragraph()
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer_para.add_run(
            f'Documento generado por LINCE — Herramienta Forense Digital Etica\n'
            f'Uso exclusivo para documentacion legal. {now}\n'
            f'Caso: {self.case_id}'
        ).font.size = Pt(9)

        # ---- GUARDAR ----
        report_dir = os.path.join('reports', self.case_id)
        os.makedirs(report_dir, exist_ok=True)
        fname = f"escudo_legal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        fpath = os.path.join(report_dir, fname)
        doc.save(fpath)

        log_action(f"Escudo legal generado: {fpath}", "INFO")
        print(f"{Fore.GREEN}  Escudo legal guardado: {fpath}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  Para convertir a PDF: abre el .docx en Word → Guardar como → PDF{Style.RESET_ALL}")
        return fpath
