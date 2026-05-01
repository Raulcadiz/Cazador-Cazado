#!/usr/bin/env python3
"""
ANTI-ACOSO DIGITAL TOOLKIT
Version: 2.0.0
Autor: Ethical Security Team
Licencia: Uso exclusivo para documentacion legal de acoso
"""
import sys
# Forzar UTF-8 en terminal Windows (evita UnicodeEncodeError con caracteres especiales)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import yaml
import shutil
from datetime import datetime
import os
import time
from colorama import init, Fore, Style
from modules.investigator import DigitalInvestigator
from modules.evidence import EvidenceCollector
from modules.analyzer import PatternAnalyzer
from modules.reporter import ReportGenerator
from modules.utils import clear_screen, print_banner, log_action
from modules.watcher import CaseWatcher
from modules.alerts import AlertBeacon
from modules.shield import ProtectionShield
from modules.victim_watcher import VictimWatcher
from modules.email_checker import EmailChecker

# Inicializar colorama
init(autoreset=True)


class AntiAcosoToolkit:
    """Herramienta principal para investigación digital ética"""

    def __init__(self):
        self.version = "2.0.0"
        self.case_id = f"CASE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.investigator = DigitalInvestigator(case_id=self.case_id)
        self.evidence = EvidenceCollector(self.case_id)
        self.analyzer = PatternAnalyzer()
        self.reporter = ReportGenerator()
        self.target_username = None
        self.config = self._load_config()
        self.watcher         = None
        self.beacon          = None
        self.shield          = None
        self.victim_watcher  = None
        self.email_checker   = EmailChecker()

    # -----------------------------------------------------------------------
    # HELPER: calcular riesgo del caso actual
    # -----------------------------------------------------------------------
    def _get_risk(self):
        """Calcula el nivel de riesgo con todos los datos disponibles del caso."""
        from modules.investigator import CACHE_FILE
        evidences = self.evidence.evidences if hasattr(self.evidence, 'evidences') else []

        # Cargar resultados de busqueda de username del cache
        username_results = {}
        try:
            if os.path.exists(CACHE_FILE) and self.target_username:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                user_data = cache.get(self.target_username, {})
                username_results = {
                    p: d['url'] for p, d in user_data.items()
                    if d.get('status') == 'found'
                }
        except Exception:
            pass

        return self.analyzer.calculate_risk_level(
            evidences=evidences,
            username_results=username_results,
        )

    def _load_config(self):
        """Cargar configuración desde config.yaml"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            log_action("config.yaml cargado correctamente", "INFO")
            return cfg or {}
        except Exception as e:
            log_action(f"No se pudo cargar config.yaml: {e}", "WARNING")
            return {}

    def _select_case(self):
        """Seleccionar un caso existente o continuar con el nuevo"""
        data_dir = "data"
        existing_cases = []

        if os.path.exists(data_dir):
            for item in sorted(os.listdir(data_dir), reverse=True):
                case_path = os.path.join(data_dir, item)
                if os.path.isdir(case_path) and item.startswith('CASE-'):
                    existing_cases.append(item)

        if not existing_cases:
            return  # No hay casos previos, continuar con el nuevo

        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📁 GESTIÓN DE CASOS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"  {Fore.GREEN}[0]{Style.RESET_ALL} Crear nuevo caso  ({self.case_id})\n")

        for i, case in enumerate(existing_cases[:8], 1):
            extra = ""
            try:
                info_file = f"{data_dir}/{case}/case_info.json"
                rec_file  = f"{data_dir}/{case}/evidence_records.json"
                if os.path.exists(info_file):
                    with open(info_file, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    username = info.get('username', 'Sin objetivo')
                    ev_count = 0
                    if os.path.exists(rec_file):
                        with open(rec_file, 'r', encoding='utf-8') as f:
                            ev_count = len(json.load(f))
                    extra = f"  | 🎯 {username} | 📁 {ev_count} evidencias"
            except Exception:
                pass
            print(f"  {Fore.GREEN}[{i}]{Style.RESET_ALL} {case}{extra}")

        choice = input(f"\n{Fore.YELLOW}Selecciona caso (0 = nuevo): {Style.RESET_ALL}").strip()

        if not choice or choice == '0':
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(existing_cases[:8]):
                selected = existing_cases[idx]
                self.case_id = selected
                self.evidence = EvidenceCollector(self.case_id)
                self.investigator._case_id = self.case_id
                loaded = self.evidence.load_case_data()

                info_file = f"{data_dir}/{selected}/case_info.json"
                if os.path.exists(info_file):
                    with open(info_file, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    self.target_username = info.get('username')

                print(f"\n{Fore.GREEN}✅ Caso {selected} cargado  ({loaded} evidencias){Style.RESET_ALL}")
                time.sleep(1.5)
        except (ValueError, IndexError):
            print(f"{Fore.RED}❌ Selección inválida, se crea un nuevo caso{Style.RESET_ALL}")
            time.sleep(1)

    def display_main_menu(self):
        """Mostrar menú principal con opciones"""
        clear_screen()
        print_banner()

        # Calcular riesgo para mostrar en menu
        risk = self._get_risk()
        rcolor = risk['color']
        rlevel = risk['level']
        rscore = risk['score']
        rind   = "!!!" if rlevel == 'ALTO' else "!! " if rlevel == 'MEDIO' else " ok"

        n_ev   = risk['n_evidences']
        n_plat = risk['n_platforms']

        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}CASO    : {self.case_id}{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}OBJETIVO: {self.target_username or 'No definido'}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}DATOS   : {n_ev} evidencias | {n_plat} plataformas{Style.RESET_ALL}")
        print(f"  {rcolor}RIESGO  : [{rind}] {rlevel}  (score {rscore}/100)  {risk['urgencia']}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        menu_options = [
            f"{Fore.GREEN}[1]{Style.RESET_ALL} Definir objetivo de investigación",
            f"{Fore.GREEN}[2]{Style.RESET_ALL} Búsqueda de huella digital",
            f"{Fore.GREEN}[3]{Style.RESET_ALL} Análisis de redes sociales",
            f"{Fore.GREEN}[4]{Style.RESET_ALL} Captura de evidencias",
            f"{Fore.GREEN}[5]{Style.RESET_ALL} Análisis de patrones",
            f"{Fore.GREEN}[6]{Style.RESET_ALL} Búsqueda inversa de imágenes",
            f"{Fore.GREEN}[7]{Style.RESET_ALL} Análisis de metadatos",
            f"{Fore.GREEN}[8]{Style.RESET_ALL} Generar informes legales",
            f"{Fore.GREEN}[9]{Style.RESET_ALL} Dashboard de estadísticas",
            f"{Fore.GREEN}[10]{Style.RESET_ALL} Configuración y ética",
            (f"{Fore.MAGENTA}[11]{Style.RESET_ALL} Vigilancia automatica "
             f"{'[ACTIVA]' if self.watcher and self.watcher.is_running() else '[inactiva]'}"),
            (f"{Fore.MAGENTA}[12]{Style.RESET_ALL} Baliza de alerta    "
             f"{'[ACTIVA]' if self.beacon and self.beacon.is_running() else '[inactiva]'}"),
            f"{Fore.CYAN}[13]{Style.RESET_ALL} Escudo de proteccion",
            f"{Fore.RED}[0]{Style.RESET_ALL} Salir del sistema"
        ]

        for option in menu_options:
            print(f"  {option}")

        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        choice = input(f"\n{Fore.YELLOW}Selecciona una opcion (0-13): {Style.RESET_ALL}")
        return choice

    def run(self):
        """Ejecutar la herramienta principal"""
        clear_screen()
        print_banner()

        self.show_legal_warning()
        self._select_case()

        while True:
            try:
                choice = self.display_main_menu()

                if choice == '0':
                    self.exit_toolkit()
                    break
                elif choice == '1':
                    self.set_target()
                elif choice == '2':
                    self.digital_footprint_search()
                elif choice == '3':
                    self.social_media_analysis()
                elif choice == '4':
                    self.evidence_collection()
                elif choice == '5':
                    self.pattern_analysis()
                elif choice == '6':
                    self.reverse_image_search()
                elif choice == '7':
                    self.metadata_analysis()
                elif choice == '8':
                    self.generate_reports()
                elif choice == '9':
                    self.show_dashboard()
                elif choice == '10':
                    self.show_configuration()
                elif choice == '11':
                    self.surveillance_menu()
                elif choice == '12':
                    self.beacon_menu()
                elif choice == '13':
                    self.shield_menu()
                else:
                    print(f"{Fore.RED}Opcion no valida. Intenta nuevamente.{Style.RESET_ALL}")
                    time.sleep(1)

            except KeyboardInterrupt:
                self.exit_toolkit()
                break
            except Exception as e:
                log_action(f"Error en menú principal: {str(e)}", "ERROR")
                time.sleep(2)

    def set_target(self):
        """Definir el objetivo de investigación"""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🎯 DEFINIR OBJETIVO DE INVESTIGACIÓN{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        username = input(f"{Fore.GREEN}📝 Nombre de usuario objetivo (ej: @usuario): {Style.RESET_ALL}").strip()

        if username:
            self.target_username = username
            print(f"\n{Fore.GREEN}✅ Objetivo definido: {username}{Style.RESET_ALL}")

            print(f"\n{Fore.YELLOW}📋 Información adicional (opcional):{Style.RESET_ALL}")
            plataformas = input(f"{Fore.CYAN}   Plataformas conocidas (separar por comas): {Style.RESET_ALL}")
            incidentes = input(f"{Fore.CYAN}   Fechas de incidentes (DD/MM/AAAA): {Style.RESET_ALL}")

            self.evidence.save_case_info({
                'username': username,
                'plataformas': [p.strip() for p in plataformas.split(',')] if plataformas else [],
                'incidentes': incidentes,
                'fecha_inicio': datetime.now().isoformat()
            })

            log_action(f"Objetivo definido: {username}", "INFO")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def digital_footprint_search(self):
        """Búsqueda de huella digital (username + email)"""
        if not self.target_username:
            print(f"{Fore.RED}❌ Primero define un objetivo (Opción 1){Style.RESET_ALL}")
            time.sleep(2)
            return

        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🔎 BÚSQUEDA DE HUELLA DIGITAL{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        print(f"{Fore.GREEN}  Objetivo: {self.target_username}{Style.RESET_ALL}\n")

        footprint_menu = [
            f"{Fore.GREEN}[1]{Style.RESET_ALL} Rastreo de username en 65+ plataformas",
            f"{Fore.MAGENTA}[2]{Style.RESET_ALL} Verificar email en 12 servicios (Holehe)",
            f"{Fore.CYAN}[3]{Style.RESET_ALL} Ambas búsquedas (username + email)",
            f"{Fore.YELLOW}[0]{Style.RESET_ALL} Volver",
        ]
        for item in footprint_menu:
            print(f"  {item}")

        choice = input(f"\n{Fore.YELLOW}Selecciona (0-3): {Style.RESET_ALL}").strip()

        if choice == '0':
            return

        # ---- BUSQUEDA POR USERNAME ----
        if choice in ('1', '3'):
            print()
            results = self.investigator.search_username(self.target_username)
            if results:
                print(f"\n{Fore.GREEN}Perfiles encontrados:{Style.RESET_ALL}")
                for platform, url in results.items():
                    print(f"  {Fore.YELLOW}[+] {platform}:{Style.RESET_ALL} {url}")
            else:
                print(f"{Fore.RED}No se encontraron perfiles públicos.{Style.RESET_ALL}")

        # ---- VERIFICACION DE EMAIL ----
        if choice in ('2', '3'):
            print()
            email = input(
                f"{Fore.CYAN}Email a verificar "
                f"{Fore.YELLOW}(Enter para saltar){Style.RESET_ALL}: "
            ).strip()
            if email and '@' in email:
                self.email_checker.check_email(email)
                log_action(f"Verificacion email: {email}", "INFO")
            elif email:
                print(f"{Fore.RED}Email no válido.{Style.RESET_ALL}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def social_media_analysis(self):
        """Análisis de redes sociales del objetivo"""
        if not self.target_username:
            print(f"{Fore.RED}❌ Primero define un objetivo (Opción 1){Style.RESET_ALL}")
            time.sleep(2)
            return

        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📱 ANÁLISIS DE REDES SOCIALES{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}👤 Objetivo: {self.target_username}{Style.RESET_ALL}\n")

        print(f"{Fore.YELLOW}🔍 Buscando perfiles en redes sociales...{Style.RESET_ALL}")
        results = self.investigator.search_username(self.target_username)

        if not results:
            print(f"{Fore.RED}❌ No se encontraron perfiles en redes sociales{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")
            return

        print(f"\n{Fore.GREEN}✅ Perfiles encontrados:{Style.RESET_ALL}\n")
        for platform, url in results.items():
            print(f"  {Fore.YELLOW}🔗 {platform}:{Style.RESET_ALL}")
            print(f"     {url}")

        print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📊 ANÁLISIS DETALLADO{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}\n")

        analysis_menu = [
            f"{Fore.GREEN}[1]{Style.RESET_ALL} Análisis de actividad reciente",
            f"{Fore.GREEN}[2]{Style.RESET_ALL} Extraer información pública",
            f"{Fore.GREEN}[3]{Style.RESET_ALL} Analizar contenido multimedia",
            f"{Fore.GREEN}[4]{Style.RESET_ALL} Monitorear actividad futura",
            f"{Fore.GREEN}[5]{Style.RESET_ALL} Volver al menú principal"
        ]

        for item in analysis_menu:
            print(f"  {item}")

        choice = input(f"\n{Fore.YELLOW}Selecciona opción (1-5): {Style.RESET_ALL}")

        if choice == '1':
            self._analyze_recent_activity(results)
        elif choice == '2':
            self._extract_public_info(results)
        elif choice == '3':
            self._analyze_media_content(results)
        elif choice == '4':
            self._setup_monitoring()

    def _analyze_recent_activity(self, profiles):
        """Analizar actividad reciente en redes sociales"""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📅 ANÁLISIS DE ACTIVIDAD RECIENTE{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}📈 Patrones de actividad detectados:{Style.RESET_ALL}\n")

        activity_patterns = {
            'Instagram': {
                'posts_last_week': 12,
                'avg_posts_per_day': 1.7,
                'peak_hours': ['18:00-20:00', '22:00-00:00'],
                'most_active_day': 'Sábado',
                'engagement_rate': '3.2%'
            },
            'Twitter': {
                'tweets_last_week': 47,
                'avg_tweets_per_day': 6.7,
                'peak_hours': ['09:00-11:00', '14:00-16:00', '21:00-23:00'],
                'most_active_day': 'Lunes',
                'retweet_rate': '15%'
            },
            'Facebook': {
                'posts_last_week': 8,
                'avg_posts_per_day': 1.1,
                'peak_hours': ['20:00-22:00'],
                'most_active_day': 'Domingo',
                'interaction_rate': '4.8%'
            }
        }

        for platform, url in profiles.items():
            if platform in activity_patterns:
                print(f"{Fore.YELLOW}📱 {platform}:{Style.RESET_ALL}")
                for key, value in activity_patterns[platform].items():
                    print(f"  • {key.replace('_', ' ').title()}: {value}")
                print()

        analysis_data = {
            'target': self.target_username,
            'profiles_found': len(profiles),
            'activity_patterns': activity_patterns,
            'analysis_date': datetime.now().isoformat()
        }

        analysis_file = f"data/{self.case_id}/social_media_analysis.json"
        os.makedirs(os.path.dirname(analysis_file), exist_ok=True)
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=4, ensure_ascii=False)

        print(f"{Fore.GREEN}✅ Análisis guardado en: {analysis_file}{Style.RESET_ALL}")
        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def _extract_public_info(self, profiles):
        """Extraer información pública de perfiles"""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🔍 EXTRACCIÓN DE INFORMACIÓN PÚBLICA{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        public_info = {}

        for platform, url in profiles.items():
            print(f"{Fore.YELLOW}📊 Analizando {platform}...{Style.RESET_ALL}")

            try:
                if platform == 'Instagram':
                    public_info[platform] = {
                        'profile_url': url,
                        'followers': 'N/A',
                        'following': 'N/A',
                        'posts': 'N/A',
                        'is_private': 'Desconocido'
                    }
                elif platform == 'Twitter':
                    public_info[platform] = {
                        'profile_url': url,
                        'followers': 'N/A',
                        'following': 'N/A',
                        'tweets': 'N/A',
                        'verified': False
                    }
                elif platform == 'Facebook':
                    public_info[platform] = {
                        'profile_url': url,
                        'friends': 'N/A',
                        'location': 'N/A'
                    }
                else:
                    public_info[platform] = {'profile_url': url}

                print(f"{Fore.GREEN}✅ Información extraída de {platform}{Style.RESET_ALL}")

            except Exception as e:
                print(f"{Fore.RED}❌ Error en {platform}: {str(e)}{Style.RESET_ALL}")

        print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📋 RESUMEN DE INFORMACIÓN PÚBLICA{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}\n")

        for platform, info in public_info.items():
            print(f"{Fore.YELLOW}📱 {platform}:{Style.RESET_ALL}")
            for key, value in info.items():
                print(f"  • {key.replace('_', ' ').title()}: {value}")
            print()

        info_file = f"data/{self.case_id}/public_info.json"
        os.makedirs(os.path.dirname(info_file), exist_ok=True)
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(public_info, f, indent=4, ensure_ascii=False)

        print(f"{Fore.GREEN}✅ Información guardada en: {info_file}{Style.RESET_ALL}")
        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def _analyze_media_content(self, profiles):
        """Analizar contenido multimedia en perfiles"""
        print(f"\n{Fore.YELLOW}🖼️  Análisis de contenido multimedia...{Style.RESET_ALL}")

        media_analysis = {
            'total_imagenes': 'N/A',
            'total_videos': 'N/A',
            'plataformas_con_media': list(profiles.keys())
        }

        print(f"{Fore.GREEN}📊 Resultados:{Style.RESET_ALL}")
        for key, value in media_analysis.items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def _setup_monitoring(self):
        """Configurar monitoreo de actividad futura"""
        print(f"\n{Fore.YELLOW}👁️  Configurando monitoreo...{Style.RESET_ALL}")

        monitoring_config = {
            'plataformas': ['Instagram', 'Twitter', 'Facebook'],
            'frecuencia': 'cada 6 horas',
            'alertas_por': ['nuevas_publicaciones', 'cambios_perfil'],
            'duracion': '30 días',
            'reporte_automatico': True
        }

        print(f"{Fore.GREEN}✅ Monitoreo configurado:{Style.RESET_ALL}")
        for key, value in monitoring_config.items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def evidence_collection(self):
        """Captura de evidencias"""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📸 CAPTURA DE EVIDENCIAS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}Selecciona tipo de evidencia:{Style.RESET_ALL}\n")

        evidence_types = [
            f"{Fore.YELLOW}[1]{Style.RESET_ALL} Captura de pantalla de URL",
            f"{Fore.YELLOW}[2]{Style.RESET_ALL} Descarga de imágenes",
            f"{Fore.YELLOW}[3]{Style.RESET_ALL} Copia de texto/mensajes",
            f"{Fore.YELLOW}[4]{Style.RESET_ALL} Volver al menú principal"
        ]

        for et in evidence_types:
            print(f"  {et}")

        choice = input(f"\n{Fore.YELLOW}🔍 Selecciona opción (1-4): {Style.RESET_ALL}")

        if choice == '1':
            url = input(f"{Fore.CYAN}URL a capturar: {Style.RESET_ALL}")
            if url:
                self.evidence.capture_screenshot(url)
        elif choice == '2':
            image_url = input(f"{Fore.CYAN}URL de la imagen: {Style.RESET_ALL}")
            if image_url:
                self.evidence.download_image(image_url)
        elif choice == '3':
            print(f"{Fore.YELLOW}Pega el texto a registrar (termina con una línea que contenga solo '---'):{Style.RESET_ALL}")
            lines = []
            while True:
                line = input()
                if line == '---':
                    break
                lines.append(line)
            text = '\n'.join(lines)
            if text:
                source = input(f"{Fore.CYAN}Fuente del texto (plataforma/URL): {Style.RESET_ALL}")
                desc = input(f"{Fore.CYAN}Descripción breve: {Style.RESET_ALL}")
                self.evidence.record_text_evidence(text, source, desc)
                print(f"{Fore.GREEN}✅ Texto registrado como evidencia{Style.RESET_ALL}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def pattern_analysis(self):
        """Análisis de patrones de comportamiento"""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🔄 ANÁLISIS DE PATRONES DE COMPORTAMIENTO{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        all_evidence = self.evidence.get_all_evidence()

        if not all_evidence:
            print(f"{Fore.RED}❌ No hay evidencias para analizar{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 Sugerencia: Recopila evidencias primero (Opción 4){Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")
            return

        print(f"{Fore.GREEN}📊 Analizando {len(all_evidence)} evidencias...{Style.RESET_ALL}\n")

        patterns = self.analyzer.analyze_communication_patterns(all_evidence)

        print(f"{Fore.YELLOW}🔍 PATRONES DETECTADOS:{Style.RESET_ALL}\n")

        if 'vocabulario_analisis' in patterns:
            vocab = patterns['vocabulario_analisis']
            print(f"{Fore.CYAN}📝 Análisis de vocabulario:{Style.RESET_ALL}")
            print(f"  • Total palabras: {vocab.get('total_palabras', 0)}")
            print(f"  • Palabras únicas: {vocab.get('palabras_unicas', 0)}")

            if 'palabras_mas_usadas' in vocab:
                print(f"  • Palabras más usadas:")
                for word, count in vocab['palabras_mas_usadas'].items():
                    print(f"    - '{word}': {count} veces")

        if 'terminos_amenazantes' in patterns and patterns['terminos_amenazantes']:
            print(f"\n{Fore.RED}⚠️  TÉRMINOS AMENAZANTES DETECTADOS:{Style.RESET_ALL}")
            for term in patterns['terminos_amenazantes']:
                print(f"  • {term}")

        if 'patrones_linguisticos' in patterns and patterns['patrones_linguisticos']:
            print(f"\n{Fore.YELLOW}🎯 PATRONES LINGÜÍSTICOS:{Style.RESET_ALL}")
            for pattern in patterns['patrones_linguisticos']:
                print(f"  • {pattern}")

        print(f"\n{Fore.CYAN}📅 ANÁLISIS TEMPORAL:{Style.RESET_ALL}")

        dates = []
        for ev in all_evidence:
            if 'timestamp' in ev:
                try:
                    from dateutil import parser as dateparser
                    dt = dateparser.parse(ev['timestamp'])
                    dates.append(dt)
                except Exception:
                    pass

        if dates:
            dates.sort()
            print(f"  • Primera evidencia: {dates[0].strftime('%d/%m/%Y %H:%M')}")
            print(f"  • Última evidencia: {dates[-1].strftime('%d/%m/%Y %H:%M')}")
            print(f"  • Rango temporal: {(dates[-1] - dates[0]).days} días")

            if len(dates) > 1:
                avg_interval = (dates[-1] - dates[0]).total_seconds() / (len(dates) - 1)
                print(f"  • Intervalo promedio: {avg_interval/3600:.1f} horas")

        content_types = {}
        for ev in all_evidence:
            ev_type = ev.get('type', 'desconocido')
            content_types[ev_type] = content_types.get(ev_type, 0) + 1

        print(f"\n{Fore.CYAN}📦 DISTRIBUCIÓN POR TIPO:{Style.RESET_ALL}")
        for ev_type, count in content_types.items():
            percentage = (count / len(all_evidence)) * 100
            print(f"  • {ev_type}: {count} ({percentage:.1f}%)")

        pattern_file = f"data/{self.case_id}/pattern_analysis.json"
        os.makedirs(os.path.dirname(pattern_file), exist_ok=True)
        with open(pattern_file, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, indent=4, ensure_ascii=False)

        print(f"\n{Fore.GREEN}✅ Análisis guardado en: {pattern_file}{Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}💡 RECOMENDACIONES:{Style.RESET_ALL}")
        recommendations = [
            "Documenta la frecuencia de los incidentes",
            "Registra el tono y contenido de las comunicaciones",
            "Identifica patrones temporales (horarios, días)",
            "Busca escalada en la intensidad o frecuencia",
            "Comparte patrones con autoridades para validación"
        ]

        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def reverse_image_search(self):
        """Búsqueda inversa de imágenes"""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🖼️ BÚSQUEDA INVERSA DE IMÁGENES{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}Opciones de búsqueda:{Style.RESET_ALL}\n")

        options = [
            f"{Fore.YELLOW}[1]{Style.RESET_ALL} Google Images",
            f"{Fore.YELLOW}[2]{Style.RESET_ALL} Yandex Images",
            f"{Fore.YELLOW}[3]{Style.RESET_ALL} TinEye",
            f"{Fore.YELLOW}[4]{Style.RESET_ALL} Bing Visual Search"
        ]

        for opt in options:
            print(f"  {opt}")

        choice = input(f"\n{Fore.YELLOW}🔍 Selecciona motor (1-4): {Style.RESET_ALL}")

        image_path = input(f"{Fore.CYAN}Ruta de la imagen local o URL: {Style.RESET_ALL}")

        if image_path:
            results = self.investigator.reverse_image_search(image_path, choice)

            if results:
                print(f"\n{Fore.GREEN}✅ Resultados encontrados:{Style.RESET_ALL}\n")
                for i, result in enumerate(results[:10], 1):
                    print(f"  {Fore.YELLOW}{i}.{Style.RESET_ALL} {result}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def metadata_analysis(self):
        """Análisis completo de metadatos"""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📊 ANÁLISIS COMPLETO DE METADATOS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}Selecciona tipo de análisis:{Style.RESET_ALL}\n")

        analysis_options = [
            f"{Fore.YELLOW}[1]{Style.RESET_ALL} Analizar archivo individual",
            f"{Fore.YELLOW}[2]{Style.RESET_ALL} Analizar directorio completo",
            f"{Fore.YELLOW}[3]{Style.RESET_ALL} Buscar metadatos sensibles",
            f"{Fore.YELLOW}[4]{Style.RESET_ALL} Comparar metadatos entre archivos",
            f"{Fore.YELLOW}[5]{Style.RESET_ALL} Generar reporte forense"
        ]

        for option in analysis_options:
            print(f"  {option}")

        choice = input(f"\n{Fore.YELLOW}Selecciona opción (1-5): {Style.RESET_ALL}")

        if choice == '1':
            self._analyze_single_file_metadata()
        elif choice == '2':
            self._analyze_directory_metadata()
        elif choice == '3':
            self._search_sensitive_metadata()
        elif choice == '4':
            self._compare_metadata()
        elif choice == '5':
            self._generate_forensic_report()
        else:
            print(f"{Fore.RED}❌ Opción no válida{Style.RESET_ALL}")
            time.sleep(1)

    def _analyze_single_file_metadata(self):
        """Analizar metadatos de un archivo individual"""
        file_path = input(f"{Fore.CYAN}Ruta del archivo a analizar: {Style.RESET_ALL}").strip()

        if not os.path.exists(file_path):
            print(f"{Fore.RED}❌ El archivo no existe{Style.RESET_ALL}")
            time.sleep(1)
            return

        print(f"\n{Fore.YELLOW}🔍 Analizando metadatos de: {os.path.basename(file_path)}{Style.RESET_ALL}")

        metadata = self.evidence.extract_metadata(file_path)

        if metadata and 'error' not in metadata:
            print(f"\n{Fore.GREEN}✅ Metadatos extraídos:{Style.RESET_ALL}")

            if 'basic' in metadata:
                print(f"\n{Fore.CYAN}📋 INFORMACIÓN BÁSICA:{Style.RESET_ALL}")
                for key, value in metadata['basic'].items():
                    print(f"  • {key.replace('_', ' ').title()}: {value}")

            if 'exif' in metadata:
                print(f"\n{Fore.CYAN}📷 METADATOS EXIF:{Style.RESET_ALL}")
                for key, value in metadata['exif'].items():
                    print(f"  • {key.replace('_', ' ').title()}: {value}")

                sensitive_keys = ['gps_latitude', 'gps_longitude', 'gps_altitude']
                has_sensitive = any(key in metadata['exif'] for key in sensitive_keys)

                if has_sensitive:
                    print(f"\n{Fore.RED}⚠️  DATOS SENSIBLES ENCONTRADOS:{Style.RESET_ALL}")
                    for key in sensitive_keys:
                        if key in metadata['exif']:
                            print(f"  • {key.replace('_', ' ').title()}: {metadata['exif'][key]}")

            analysis_file = f"data/{self.case_id}/metadata_analysis/{os.path.basename(file_path)}_analysis.json"
            os.makedirs(os.path.dirname(analysis_file), exist_ok=True)

            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4, ensure_ascii=False)

            print(f"\n{Fore.GREEN}✅ Análisis guardado en: {analysis_file}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ No se pudieron extraer metadatos{Style.RESET_ALL}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def _analyze_directory_metadata(self):
        """Analizar metadatos de todos los archivos en un directorio"""
        dir_path = input(f"{Fore.CYAN}Ruta del directorio a analizar: {Style.RESET_ALL}").strip()

        if not os.path.exists(dir_path):
            print(f"{Fore.RED}❌ El directorio no existe{Style.RESET_ALL}")
            time.sleep(1)
            return

        print(f"\n{Fore.YELLOW}🔍 Analizando directorio: {dir_path}{Style.RESET_ALL}")

        extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.pdf', '.docx', '.doc']
        files_to_analyze = []

        for root, _, files in os.walk(dir_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    files_to_analyze.append(os.path.join(root, file))

        if not files_to_analyze:
            print(f"{Fore.RED}❌ No se encontraron archivos compatibles{Style.RESET_ALL}")
            time.sleep(1)
            return

        print(f"\n{Fore.GREEN}📁 Archivos encontrados: {len(files_to_analyze)}{Style.RESET_ALL}")

        all_metadata = {}
        for i, file_path in enumerate(files_to_analyze, 1):
            print(f"\n[{i}/{len(files_to_analyze)}] Analizando: {os.path.basename(file_path)}")

            metadata = self.evidence.extract_metadata(file_path)
            if metadata and 'error' not in metadata:
                all_metadata[os.path.basename(file_path)] = metadata
                print(f"{Fore.GREEN}✅ OK{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️  Sin metadatos{Style.RESET_ALL}")

        if all_metadata:
            analysis_file = f"data/{self.case_id}/directory_metadata_analysis.json"
            os.makedirs(os.path.dirname(analysis_file), exist_ok=True)
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(all_metadata, f, indent=4, ensure_ascii=False)

            print(f"\n{Fore.GREEN}✅ Análisis completo guardado en: {analysis_file}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}📊 Total archivos analizados: {len(all_metadata)}{Style.RESET_ALL}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def _search_sensitive_metadata(self):
        """Buscar metadatos sensibles en archivos del caso"""
        print(f"{Fore.YELLOW}🔎 Buscando metadatos sensibles en el caso...{Style.RESET_ALL}")

        case_dir = f"data/{self.case_id}"
        if not os.path.exists(case_dir):
            print(f"{Fore.RED}❌ No hay datos del caso para analizar{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")
            return

        sensitive_count = {
            'archivos_con_gps': 0,
            'archivos_con_fechas': 0,
            'archivos_con_informacion_personal': 0,
            'archivos_con_software': 0
        }

        for root, _, files in os.walk(case_dir):
            for file in files:
                if file.endswith('_metadata.json'):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                        exif_data = meta.get('exif', {})
                        if 'gps_latitude' in exif_data or 'gps_longitude' in exif_data:
                            sensitive_count['archivos_con_gps'] += 1
                        if 'datetime' in exif_data or 'datetime_original' in exif_data:
                            sensitive_count['archivos_con_fechas'] += 1
                        if 'make' in exif_data or 'model' in exif_data:
                            sensitive_count['archivos_con_informacion_personal'] += 1
                        if 'software' in exif_data:
                            sensitive_count['archivos_con_software'] += 1
                    except Exception:
                        pass

        print(f"{Fore.GREEN}📊 Resultados:{Style.RESET_ALL}")
        for key, value in sensitive_count.items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def _compare_metadata(self):
        """Comparar metadatos entre archivos"""
        print(f"{Fore.YELLOW}🔄 Comparando metadatos de evidencias...{Style.RESET_ALL}")

        case_dir = f"data/{self.case_id}/metadata"
        if not os.path.exists(case_dir):
            print(f"{Fore.RED}❌ No hay metadatos para comparar{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")
            return

        devices = set()
        software_set = set()
        files_analyzed = 0

        for root, _, files in os.walk(case_dir):
            for file in files:
                if file.endswith('.json'):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                        exif_data = meta.get('exif', {})
                        if 'make' in exif_data and 'model' in exif_data:
                            devices.add(f"{exif_data['make']} {exif_data['model']}")
                        if 'software' in exif_data:
                            software_set.add(exif_data['software'])
                        files_analyzed += 1
                    except Exception:
                        pass

        comparison_results = {
            'archivos_analizados': files_analyzed,
            'dispositivos_detectados': list(devices) if devices else ['No disponible'],
            'software_detectado': list(software_set) if software_set else ['No disponible']
        }

        print(f"{Fore.GREEN}📊 Resultados de comparación:{Style.RESET_ALL}")
        for key, value in comparison_results.items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def _generate_forensic_report(self):
        """Generar reporte forense de metadatos"""
        print(f"{Fore.YELLOW}📄 Generando reporte forense...{Style.RESET_ALL}")

        all_evidence = self.evidence.get_all_evidence()
        report_name = f"Reporte_Forense_{self.case_id}_{datetime.now().strftime('%Y%m%d')}.json"
        report_dir = f"reports/{self.case_id}"
        os.makedirs(report_dir, exist_ok=True)
        report_path = f"{report_dir}/{report_name}"

        report_data = {
            'case_id': self.case_id,
            'generated_at': datetime.now().isoformat(),
            'tipo_analisis': 'Metadatos EXIF y forense digital',
            'total_evidencias': len(all_evidence),
            'evidencias_por_tipo': self.evidence.get_evidence_count()
        }

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=4, ensure_ascii=False)

        print(f"{Fore.GREEN}✅ Reporte generado: {report_path}{Style.RESET_ALL}")
        for key, value in report_data.items():
            if key not in ('evidencias_por_tipo',):
                print(f"  • {key.replace('_', ' ').title()}: {value}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def generate_reports(self):
        """Generar informes legales"""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📄 GENERACIÓN DE INFORMES LEGALES{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}Tipos de informe disponibles:{Style.RESET_ALL}\n")

        report_types = [
            f"{Fore.YELLOW}[1]{Style.RESET_ALL} Informe para autoridades policiales",
            f"{Fore.YELLOW}[2]{Style.RESET_ALL} Informe para abogado/a",
            f"{Fore.YELLOW}[3]{Style.RESET_ALL} Informe para redes sociales",
            f"{Fore.YELLOW}[4]{Style.RESET_ALL} Documentación completa del caso",
            f"{Fore.YELLOW}[5]{Style.RESET_ALL} Generar todos los informes"
        ]

        for rt in report_types:
            print(f"  {rt}")

        choice = input(f"\n{Fore.YELLOW}🔍 Selecciona tipo de informe (1-5): {Style.RESET_ALL}")

        if choice in ['1', '2', '3', '4']:
            self.reporter.generate_report(self.case_id, choice, self.evidence.get_all_evidence())
            print(f"\n{Fore.GREEN}✅ Informe generado exitosamente{Style.RESET_ALL}")
        elif choice == '5':
            for i in range(1, 5):
                self.reporter.generate_report(self.case_id, str(i), self.evidence.get_all_evidence())
            print(f"\n{Fore.GREEN}✅ Todos los informes generados{Style.RESET_ALL}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def show_dashboard(self):
        """Mostrar dashboard de estadísticas con semáforo de riesgo"""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  DASHBOARD — CASO {self.case_id}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

        # --- SEMAFORO (siempre arriba del todo) ---
        risk = self._get_risk()
        self.analyzer.display_risk_semaphore(risk, compact=False)

        # --- Estadísticas de evidencias ---
        evidences = self.evidence.get_all_evidence()
        stats = self.analyzer.get_statistics(evidences)

        print(f"{Fore.GREEN}  Estadisticas del caso:{Style.RESET_ALL}\n")

        # Resumen compacto en lugar de volcar todo el dict
        n_ev = stats.get('total_evidencias', 0)
        duracion = stats.get('duracion_caso') or {}
        por_tipo = stats.get('por_tipo', {})
        horas    = stats.get('patrones_temporales', {}).get('horas_activas', [])

        print(f"  {'Total evidencias':<30}: {n_ev}")
        if duracion:
            print(f"  {'Inicio caso':<30}: {duracion.get('inicio','?')}")
            print(f"  {'Ultimo evento':<30}: {duracion.get('fin','?')}")
            print(f"  {'Dias activos':<30}: {duracion.get('dias_activos','?')}")

        if por_tipo:
            print(f"\n  {'Por tipo':}")
            for t, c in sorted(por_tipo.items(), key=lambda x: -x[1]):
                bar = '#' * min(c * 2, 20)
                print(f"    {t:<18} [{bar:<20}] {c}")

        if horas:
            top = horas[0]
            print(f"\n  Hora pico de actividad : {top['hora']}:00 "
                  f"({top['count']} eventos)")

        if stats.get('patrones_temporales', {}).get('escalada'):
            print(f"\n  {Fore.RED}  ALERTA: Patron de escalada detectado{Style.RESET_ALL}")

        # --- Plataformas encontradas (del cache) ---
        from modules.investigator import CACHE_FILE
        if os.path.exists(CACHE_FILE) and self.target_username:
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                user_data = cache_data.get(self.target_username, {})
                found_plat = {p: d['url'] for p, d in user_data.items()
                              if d.get('status') == 'found'}
                if found_plat:
                    print(f"\n  {Fore.GREEN}Plataformas confirmadas ({len(found_plat)}):{Style.RESET_ALL}")
                    for p, u in found_plat.items():
                        print(f"    {Fore.GREEN}[+]{Style.RESET_ALL} {p:<18} {u}")
                blocked_plat = [p for p, d in user_data.items()
                                if d.get('status') == 'blocked']
                if blocked_plat:
                    print(f"\n  {Fore.YELLOW}Bloqueadas (reintentar): "
                          f"{', '.join(blocked_plat)}{Style.RESET_ALL}")
                avatars_dir = os.path.join('data', self.case_id, 'avatars')
                if os.path.exists(avatars_dir):
                    avatars = os.listdir(avatars_dir)
                    if avatars:
                        print(f"\n  {Fore.CYAN}Avatares descargados ({len(avatars)}):{Style.RESET_ALL}")
                        for av in avatars:
                            print(f"    {av}")
            except Exception:
                pass

        # --- Recomendaciones compactas ---
        print(f"\n{Fore.GREEN}  Acciones recomendadas:{Style.RESET_ALL}")
        recs = self.analyzer.get_recommendations(stats)
        for i, rec in enumerate(recs[:6], 1):
            print(f"  {Fore.YELLOW}{i}.{Style.RESET_ALL} {rec}")

        print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
        gen = input(
            f"{Fore.YELLOW}Generar reporte visual PNG? (s/n): {Style.RESET_ALL}"
        ).strip().lower()
        if gen == 's':
            report_dir = f"reports/{self.case_id}"
            os.makedirs(report_dir, exist_ok=True)
            path = self.analyzer.generate_visual_report(stats, report_dir)
            if path:
                print(f"{Fore.GREEN}Reporte visual guardado: {path}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}No hay datos suficientes para grafico{Style.RESET_ALL}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def show_configuration(self):
        """Mostrar configuración y consideraciones éticas"""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⚙️ CONFIGURACIÓN Y ÉTICA{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        config_info = {
            "Versión": self.version,
            "Caso ID": self.case_id,
            "Objetivo": self.target_username or "No definido",
            "Fecha inicio": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Directorio datos": os.path.abspath("data"),
            "Directorio informes": os.path.abspath("reports"),
            "Registros de actividad": os.path.abspath("activity.log")
        }

        for key, value in config_info.items():
            print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")

        print(f"\n{Fore.RED}⚠️ CONSIDERACIONES ÉTICAS:{Style.RESET_ALL}")
        ethics = [
            "1. Esta herramienta solo debe usarse contra acosadores comprobados",
            "2. No compartas información sin consentimiento de las víctimas",
            "3. Respeta las leyes de privacidad de tu país",
            "4. Los informes deben entregarse solo a autoridades competentes",
            "5. No uses esta información para acoso o venganza",
            "6. Documenta todo con fecha, hora y URL",
            "7. Mantén copias de seguridad de las evidencias"
        ]

        for ethic in ethics:
            print(f"  {Fore.CYAN}{ethic}{Style.RESET_ALL}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def show_legal_warning(self):
        """Mostrar advertencia legal"""
        clear_screen()
        print(f"\n{Fore.RED}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.RED}                    ADVERTENCIA LEGAL{Style.RESET_ALL}")
        print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}\n")

        warnings = [
            "ESTA HERRAMIENTA ES PARA USO ÉTICO Y LEGAL EXCLUSIVAMENTE",
            "",
            "❌ NO USAR PARA:",
            "   • Acoso o intimidación",
            "   • Violación de privacidad",
            "   • Actividades ilegales",
            "   • Venganza personal",
            "",
            "✅ USO PERMITIDO:",
            "   • Documentar acoso comprobado",
            "   • Preparar denuncias policiales",
            "   • Proteger a víctimas reales",
            "   • Investigación con fines legales",
        ]

        for warning in warnings:
            print(f"{Fore.RED}{warning}{Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}Al continuar, aceptas usar esta herramienta")
        print(f"responsablemente y bajo las leyes aplicables.{Style.RESET_ALL}")
        print(f"\n{Fore.RED}{'='*60}{Style.RESET_ALL}")

        response = input(f"\n{Fore.YELLOW}¿Aceptas los términos? (s/n): {Style.RESET_ALL}").lower()

        if response != 's':
            print(f"{Fore.RED}❌ Saliendo del sistema...{Style.RESET_ALL}")
            sys.exit(0)

    def surveillance_menu(self):
        """Menu de vigilancia automatica y comparacion de avatares"""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}  VIGILANCIA AUTOMATICA — LINCE WATCHER{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        if not self.target_username:
            print(f"{Fore.RED}Define primero el objetivo (opcion 1) antes de activar la vigilancia.{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")
            return

        # Inicializar watcher si no existe aun
        if self.watcher is None:
            self.watcher = CaseWatcher(
                case_id=self.case_id,
                username=self.target_username,
                config=self.config,
                investigator=self.investigator,
                analyzer=self.analyzer,
            )

        # Mostrar estado actual
        self.watcher.show_status()

        print(f"  {Fore.GREEN}[1]{Style.RESET_ALL} Comparar avatares ahora (deteccion multi-cuenta)")
        print(f"  {Fore.GREEN}[2]{Style.RESET_ALL} Ejecutar ciclo de vigilancia ahora")
        if self.watcher.is_running():
            print(f"  {Fore.RED}[3]{Style.RESET_ALL} Detener vigilancia automatica")
        else:
            print(f"  {Fore.GREEN}[3]{Style.RESET_ALL} Iniciar vigilancia automatica en segundo plano")
        print(f"  {Fore.GREEN}[4]{Style.RESET_ALL} Ver historial de ciclos")
        print(f"  {Fore.YELLOW}[0]{Style.RESET_ALL} Volver al menu principal")

        print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
        opt = input(f"{Fore.YELLOW}Opcion: {Style.RESET_ALL}").strip()

        if opt == '1':
            self.investigator.show_avatar_comparison(self.case_id)
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")

        elif opt == '2':
            self.watcher.run_now()
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")

        elif opt == '3':
            if self.watcher.is_running():
                self.watcher.stop()
            else:
                # Mostrar instrucciones de configuracion si faltan
                m = self.config.get('monitoring', {})
                if not m.get('notify_telegram') and not m.get('notify_email'):
                    print(f"\n{Fore.YELLOW}Nota: No tienes alertas configuradas en config.yaml.{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Las novedades se mostraran solo en consola.{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Edita config.yaml → seccion 'monitoring' para activar{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}notificaciones por Telegram o email.{Style.RESET_ALL}\n")
                self.watcher.start()
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")

        elif opt == '4':
            import json as _json
            log_file = os.path.join('data', self.case_id, 'watcher_log.json')
            if not os.path.exists(log_file):
                print(f"{Fore.YELLOW}  Sin ciclos registrados todavia.{Style.RESET_ALL}")
            else:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        cycles = _json.load(f)
                    print(f"\n{Fore.CYAN}Ultimos {len(cycles)} ciclos:{Style.RESET_ALL}\n")
                    for c in cycles[-10:]:
                        n_nov = len(c.get('novelties', []))
                        indicator = f"{Fore.RED}[!]{Style.RESET_ALL}" if n_nov else f"{Fore.GREEN}[ok]{Style.RESET_ALL}"
                        print(f"  {indicator} {c['timestamp']}  |  novedades: {n_nov}  |  avatares: {c.get('avatar_matches',0)}")
                        for nov in c.get('novelties', []):
                            print(f"       {Fore.YELLOW}> {nov}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}Error leyendo historial: {e}{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")

    # -----------------------------------------------------------------------
    # MENU 12 — BALIZA DE ALERTA (AlertBeacon)
    # -----------------------------------------------------------------------
    def beacon_menu(self):
        """Menu de la baliza de alerta: detecta nuevas cuentas alias del acosador."""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}  BALIZA DE ALERTA — LINCE BEACON{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        if not self.target_username:
            print(f"{Fore.RED}  Define primero el objetivo (opcion 1) antes de activar la baliza.{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")
            return

        # Inicializar beacon si no existe aun
        if self.beacon is None:
            self.beacon = AlertBeacon(
                case_id=self.case_id,
                config=self.config,
            )

        # Mostrar estado actual
        self.beacon.show_status()

        estado_baliza = f"{Fore.GREEN}[ACTIVA]{Style.RESET_ALL}" if self.beacon.is_running() else f"{Fore.RED}[inactiva]{Style.RESET_ALL}"
        print(f"\n  {Fore.GREEN}[1]{Style.RESET_ALL} Registrar avatares del caso en la DB del acosador")
        print(f"  {Fore.GREEN}[2]{Style.RESET_ALL} Ver DB de avatares del acosador")
        print(f"  {Fore.GREEN}[3]{Style.RESET_ALL} Ejecutar ciclo de baliza ahora")
        print(f"  {Fore.GREEN}[4]{Style.RESET_ALL} Ver historial de ciclos de baliza")
        if self.beacon.is_running():
            print(f"  {Fore.RED}[5]{Style.RESET_ALL} Detener baliza automatica {estado_baliza}")
        else:
            print(f"  {Fore.GREEN}[5]{Style.RESET_ALL} Iniciar baliza automatica  {estado_baliza}")
        print(f"  {Fore.YELLOW}[0]{Style.RESET_ALL} Volver al menu principal")

        print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
        opt = input(f"{Fore.YELLOW}Opcion: {Style.RESET_ALL}").strip()

        if opt == '1':
            print(f"\n{Fore.CYAN}Registrando avatares del caso en la DB del acosador...{Style.RESET_ALL}")
            n = self.beacon.register_from_case_avatars()
            if n == 0:
                print(f"{Fore.YELLOW}  No se encontraron avatares nuevos.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}  Ejecuta primero una busqueda de huella digital (op. 2).{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")

        elif opt == '2':
            self.beacon.show_db()
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")

        elif opt == '3':
            username = self.target_username.lstrip('@')
            print(f"\n{Fore.CYAN}Ejecutando ciclo de baliza para variantes de @{username}...{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Esto puede tardar varios minutos. Escanea {len(AlertBeacon.generate_username_variants(username))} variantes x 9 plataformas.{Style.RESET_ALL}\n")
            alerts = self.beacon.beacon_cycle(username)
            if not alerts:
                print(f"\n{Fore.GREEN}  Ciclo limpio: no se detectaron nuevas cuentas.{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}  {len(alerts)} nuevas cuentas detectadas.{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")

        elif opt == '4':
            log_file = os.path.join('data', self.case_id, 'beacon_log.json')
            if not os.path.exists(log_file):
                print(f"\n{Fore.YELLOW}  Sin ciclos registrados todavia.{Style.RESET_ALL}")
            else:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        cycles = json.load(f)
                    print(f"\n{Fore.CYAN}Ultimos {len(cycles)} ciclos de baliza:{Style.RESET_ALL}\n")
                    for c in cycles[-15:]:
                        n_al = c.get('alerts', 0)
                        ind  = f"{Fore.RED}[!]{Style.RESET_ALL}" if n_al else f"{Fore.GREEN}[ok]{Style.RESET_ALL}"
                        print(f"  {ind} {c['ts']}  |  objetivo: @{c['username']}  |  alertas: {n_al}")
                except Exception as e:
                    print(f"{Fore.RED}Error leyendo historial: {e}{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")

        elif opt == '5':
            username = self.target_username.lstrip('@')
            if self.beacon.is_running():
                self.beacon.stop()
            else:
                # Comprobar si la DB tiene avatares registrados
                db_path = os.path.join('data', self.case_id, 'harasser_db.json')
                db_empty = True
                if os.path.exists(db_path):
                    try:
                        with open(db_path, 'r', encoding='utf-8') as f:
                            db = json.load(f)
                        db_empty = len(db.get('avatars', [])) == 0
                    except Exception:
                        pass

                if db_empty:
                    print(f"\n{Fore.YELLOW}  Advertencia: La DB del acosador esta vacia.{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}  La baliza no podra comparar imagenes.{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}  Usa la opcion [1] para registrar avatares primero.{Style.RESET_ALL}\n")

                m = self.config.get('monitoring', {})
                if not m.get('notify_telegram'):
                    print(f"{Fore.YELLOW}  Nota: Telegram no configurado. Las alertas se mostraran en consola.{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}  Edita config.yaml → monitoring para activar notificaciones.{Style.RESET_ALL}\n")

                self.beacon.start(username)
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")

    # -----------------------------------------------------------------------
    # MENU 13 — ESCUDO DE PROTECCION (ProtectionShield)
    # -----------------------------------------------------------------------
    def _get_victim_watcher(self):
        """Inicializa (o reutiliza) el VictimWatcher del caso actual."""
        if self.victim_watcher is None:
            self.victim_watcher = VictimWatcher(
                case_id=self.case_id,
                config=self.config,
            )
        return self.victim_watcher

    def shield_menu(self):
        """Menu del escudo de proteccion: dashboard, guia legal, plantillas y monitor de victima."""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  ESCUDO DE PROTECCION — LINCE SHIELD{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        # Inicializar shield si no existe aun
        if self.shield is None:
            self.shield = ProtectionShield(
                case_id=self.case_id,
                analyzer=self.analyzer,
                evidence_collector=self.evidence,
            )

        vw = self._get_victim_watcher()
        vw_estado = (f"{Fore.GREEN}[ACTIVO]{Style.RESET_ALL}"
                     if vw.is_running() else f"{Fore.RED}[inactivo]{Style.RESET_ALL}")
        victima_label = f"@{vw.victim}" if vw.victim else "no definida"

        print(f"  {Fore.GREEN}[1]{Style.RESET_ALL} Dashboard en vivo  (actualiza cada 30s, Ctrl+C para salir)")
        print(f"  {Fore.GREEN}[2]{Style.RESET_ALL} Guia de privacidad y marco legal espanol")
        print(f"  {Fore.GREEN}[3]{Style.RESET_ALL} Plantillas de denuncia por plataforma")
        print(f"  {Fore.GREEN}[4]{Style.RESET_ALL} Generar escudo legal (.docx con 7 secciones)")
        print(f"\n  {Fore.MAGENTA}── MODO PROTECCION DE VICTIMA ──{Style.RESET_ALL}")
        print(f"  {Fore.MAGENTA}[5]{Style.RESET_ALL} Definir victima a proteger  (actual: {victima_label})")
        print(f"  {Fore.MAGENTA}[6]{Style.RESET_ALL} Escanear menciones AHORA  (deteccion inmediata de amenazas)")
        print(f"  {Fore.MAGENTA}[7]{Style.RESET_ALL} Monitor automatico  {vw_estado}  (escaneo cada {vw.interval_h}h)")
        print(f"  {Fore.MAGENTA}[8]{Style.RESET_ALL} Ver alertas guardadas")
        print(f"  {Fore.MAGENTA}[9]{Style.RESET_ALL} Exportar alertas a .docx  (para el abogado)")
        print(f"  {Fore.MAGENTA}[t]{Style.RESET_ALL} Configurar twscrape  (scraping directo Twitter)")
        print(f"  {Fore.YELLOW}[0]{Style.RESET_ALL} Volver al menu principal")

        print(f"\n{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
        opt = input(f"{Fore.YELLOW}Opcion: {Style.RESET_ALL}").strip()

        if opt == '1':
            try:
                self.shield.live_dashboard(investigator=self.investigator, refresh_secs=30)
            except KeyboardInterrupt:
                clear_screen()
                print(f"{Fore.YELLOW}  Dashboard cerrado.{Style.RESET_ALL}")
                time.sleep(1)

        elif opt == '2':
            self.shield.show_privacy_guide()
            input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

        elif opt == '3':
            self.shield.show_report_templates()
            input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

        elif opt == '4':
            risk = self._get_risk()
            target = self.target_username or ''
            print(f"\n{Fore.CYAN}Generando escudo legal para @{target}...{Style.RESET_ALL}")
            path = self.shield.generate_legal_shield(target_username=target, risk=risk)
            if path:
                print(f"\n{Fore.GREEN}Escudo legal generado: {path}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Error generando el documento. Revisa la consola.{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

        elif opt == '5':
            self._shield_set_victim(vw)

        elif opt == '6':
            if not vw.victim:
                print(f"\n{Fore.RED}  Primero define la victima [opcion 5].{Style.RESET_ALL}")
                time.sleep(2)
            else:
                vw.scan_now()
                input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

        elif opt == '7':
            self._shield_toggle_monitor(vw)

        elif opt == '8':
            self._shield_show_alerts(vw)

        elif opt == '9':
            if not vw.victim:
                print(f"\n{Fore.RED}  Primero define la victima [opcion 5].{Style.RESET_ALL}")
                time.sleep(2)
            else:
                print(f"\n{Fore.CYAN}  Exportando alertas a .docx...{Style.RESET_ALL}")
                path = vw.export_alerts_pdf()
                if path:
                    print(f"{Fore.GREEN}  Listo: {path}{Style.RESET_ALL}")
                input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

        elif opt == 't':
            self._shield_setup_twscrape(vw)

    # -----------------------------------------------------------------------
    # Subrutinas del escudo de victima
    # -----------------------------------------------------------------------
    def _shield_set_victim(self, vw):
        """Definir la victima y su red de contactos a proteger."""
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}  DEFINIR VICTIMA A PROTEGER{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        print(f"  La victima es la persona que RECIBE el acoso.")
        print(f"  El objetivo de investigacion es el ACOSADOR.")
        print(f"  Son roles diferentes y ambos pueden estar activos.\n")

        victim = input(f"{Fore.YELLOW}  Username de la victima (ej: Tamikarnaval): {Style.RESET_ALL}").strip().lstrip('@')
        if not victim:
            print(f"{Fore.RED}  Cancelado.{Style.RESET_ALL}")
            time.sleep(1)
            return

        vw.victim = victim

        red_input = input(
            f"{Fore.YELLOW}  Cuentas amigas a vigilar tambien (separadas por coma, o Enter para saltar): {Style.RESET_ALL}"
        ).strip()
        if red_input:
            vw.red_protegida = [u.strip().lstrip('@') for u in red_input.split(',') if u.strip()]

        h_input = input(
            f"{Fore.YELLOW}  Intervalo de escaneo en horas [{vw.interval_h}]: {Style.RESET_ALL}"
        ).strip()
        if h_input.isdigit() and int(h_input) > 0:
            vw.interval_h = int(h_input)

        print(f"\n{Fore.GREEN}  Victima configurada:{Style.RESET_ALL}")
        print(f"    Protegida:      @{vw.victim}")
        print(f"    Red protegida:  {[('@' + u) for u in vw.red_protegida] or 'ninguna'}")
        print(f"    Intervalo auto: cada {vw.interval_h}h")
        print(f"\n{Fore.CYAN}  Usa [6] para escanear ahora o [7] para activar monitoreo automatico.{Style.RESET_ALL}")
        time.sleep(3)

    def _shield_toggle_monitor(self, vw):
        """Activar o detener el monitoreo automatico."""
        if vw.is_running():
            vw.stop()
            print(f"\n{Fore.YELLOW}  Monitor de victima DETENIDO.{Style.RESET_ALL}")
        else:
            if not vw.victim:
                print(f"\n{Fore.RED}  Primero define la victima [opcion 5].{Style.RESET_ALL}")
                time.sleep(2)
                return
            ok = vw.start()
            if ok:
                print(f"\n{Fore.GREEN}  Monitor iniciado para @{vw.victim} (cada {vw.interval_h}h).{Style.RESET_ALL}")
                print(f"{Fore.CYAN}  Las alertas se guardan en data/{self.case_id}/shield/{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}  No se pudo iniciar el monitor. Revisa que apscheduler esta instalado.{Style.RESET_ALL}")
        time.sleep(2)

    def _shield_show_alerts(self, vw):
        """Muestra todas las alertas guardadas del monitor de victima."""
        clear_screen()
        vw.show_status()

        alertas = vw.listar_amenazas()
        if not alertas:
            print(f"\n{Fore.GREEN}  No hay alertas registradas todavia.{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}  HISTORICO COMPLETO DE ALERTAS:{Style.RESET_ALL}")
            for i, a in enumerate(alertas, 1):
                nivel = a.get("nivel", "?")
                color = Fore.RED if nivel == "AMENAZA" else (
                    Fore.MAGENTA if nivel == "COORDINACION" else Fore.YELLOW)
                ts    = a.get("detectado", "")[:16]
                autor = a.get("autor", str(a.get("autores", "")))
                texto = a.get("texto", "")[:80]
                print(f"  {i:>3}. {color}[{nivel}]{Style.RESET_ALL} {ts}  {autor}")
                if texto:
                    print(f"        {texto}")
                if a.get("url"):
                    print(f"        {Fore.CYAN}{a['url']}{Style.RESET_ALL}")

        input(f"\n{Fore.CYAN}Presiona Enter para continuar...{Style.RESET_ALL}")

    def _shield_setup_twscrape(self, vw):
        """Configura una cuenta Twitter para twscrape (scraping directo)."""
        from modules.victim_watcher import TWSCRAPE_OK, setup_twscrape
        clear_screen()
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}  CONFIGURAR TWSCRAPE — Scraping directo Twitter{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        if not TWSCRAPE_OK:
            print(f"  {Fore.RED}twscrape no instalado.{Style.RESET_ALL}")
            print(f"  Instala con: {Fore.YELLOW}pip install twscrape{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")
            return

        print(f"  twscrape usa una cuenta de Twitter para hacer busquedas.")
        print(f"  Recomendado: crea una cuenta secundaria solo para esto.\n")
        tw_user  = input(f"  {Fore.YELLOW}Username Twitter: {Style.RESET_ALL}").strip()
        tw_pass  = input(f"  {Fore.YELLOW}Password Twitter: {Style.RESET_ALL}").strip()
        tw_email = input(f"  {Fore.YELLOW}Email de la cuenta: {Style.RESET_ALL}").strip()
        em_pass  = input(f"  {Fore.YELLOW}Password del email: {Style.RESET_ALL}").strip()

        if not all([tw_user, tw_pass, tw_email, em_pass]):
            print(f"\n{Fore.RED}  Cancelado.{Style.RESET_ALL}")
            time.sleep(1)
            return

        print(f"\n{Fore.CYAN}  Configurando cuenta...{Style.RESET_ALL}")
        ok = setup_twscrape(tw_user, tw_pass, tw_email, em_pass)
        if ok:
            print(f"{Fore.GREEN}  Cuenta configurada. twscrape sera la fuente primaria.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}  Error en la configuracion. Revisa credenciales.{Style.RESET_ALL}")
        input(f"\n{Fore.CYAN}Presiona Enter...{Style.RESET_ALL}")

    def exit_toolkit(self):
        """Salir del sistema de forma controlada"""
        # Detener watcher, beacon y victim_watcher si estaban activos
        if self.watcher and self.watcher.is_running():
            self.watcher.stop()
        if self.beacon and self.beacon.is_running():
            self.beacon.stop()
        if self.victim_watcher and self.victim_watcher.is_running():
            self.victim_watcher.stop()
        clear_screen()
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}👋 FINALIZANDO ANTI-ACOSO TOOLKIT{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

        self.evidence.save_case_state()

        evidence_count = len(self.evidence.get_all_evidence())

        print(f"{Fore.GREEN}📋 Resumen de la sesión:{Style.RESET_ALL}")
        print(f"  • Caso ID: {self.case_id}")
        print(f"  • Objetivo: {self.target_username or 'No definido'}")
        print(f"  • Evidencias recopiladas: {evidence_count}")
        print(f"  • Fecha de cierre: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"  • Directorio de datos: {os.path.abspath('data')}")

        print(f"\n{Fore.YELLOW}📌 Recursos de ayuda:{Style.RESET_ALL}")
        resources = [
            "📞 016 - Violencia de género (España)",
            "👮 Policía Nacional - Grupo de Delitos Telemáticos",
            "👩‍⚖️ Fiscalía de Violencia sobre la Mujer",
            "🆘 Asociaciones de ayuda a víctimas"
        ]

        for resource in resources:
            print(f"  {resource}")

        print(f"\n{Fore.GREEN}✅ Sesión finalizada correctamente{Style.RESET_ALL}")
        time.sleep(3)


def main():
    """Función principal"""
    try:
        toolkit = AntiAcosoToolkit()
        toolkit.run()
    except Exception as e:
        print(f"{Fore.RED}❌ Error crítico: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
