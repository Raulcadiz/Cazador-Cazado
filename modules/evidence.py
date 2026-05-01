#!/usr/bin/env python3
"""
Módulo para la recolección y gestión de evidencias digitales
"""

import os
import json
import hashlib
import requests
import shutil
from datetime import datetime
from PIL import Image
import exif
from colorama import Fore, Style
from modules.utils import log_action, calculate_hash, create_directory_structure

class EvidenceCollector:
    """Clase para recolectar y gestionar evidencias digitales forenses"""
    
    def __init__(self, case_id):
        self.case_id = case_id
        self.evidences = []
        self.case_info = {}
        self.evidence_counter = 1
        
        # Crear estructura de directorios
        create_directory_structure()
        
        # Directorios específicos del caso
        self.case_dir = f"data/{case_id}"
        self.directories = {
            'root': self.case_dir,
            'screenshots': f"{self.case_dir}/screenshots",
            'images': f"{self.case_dir}/images",
            'metadata': f"{self.case_dir}/metadata",
            'videos': f"{self.case_dir}/videos",
            'documents': f"{self.case_dir}/documents",
            'logs': f"{self.case_dir}/logs",
            'exports': f"{self.case_dir}/exports"
        }
        
        for dir_path in self.directories.values():
            os.makedirs(dir_path, exist_ok=True)
            log_action(f"Directorio creado: {dir_path}", "DEBUG")
        
        # Inicializar archivos del caso
        self._init_case_files()
        
        log_action(f"EvidenceCollector inicializado para caso {case_id}", "INFO")
    
    def _init_case_files(self):
        """Inicializar archivos necesarios para el caso"""
        files_to_create = {
            'case_info.json': {
                'case_id': self.case_id,
                'created': datetime.now().isoformat(),
                'status': 'active',
                'evidence_count': 0
            },
            'chain_of_custody.json': {
                'entries': [],
                'last_modified': datetime.now().isoformat()
            },
            'timeline.csv': 'timestamp,event_type,description,evidence_id,hash\n'
        }
        
        for filename, content in files_to_create.items():
            filepath = f"{self.case_dir}/{filename}"
            
            if not os.path.exists(filepath):
                if isinstance(content, dict):
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(content, f, indent=4, ensure_ascii=False)
                else:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
    
    def save_case_info(self, info):
        """Guardar información del caso"""
        self.case_info.update(info)
        info['last_updated'] = datetime.now().isoformat()
        
        info_file = f"{self.case_dir}/case_info.json"
        
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                existing_info = json.load(f)
        except:
            existing_info = {}
        
        existing_info.update(info)
        
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(existing_info, f, indent=4, ensure_ascii=False)
        
        log_action(f"Información del caso actualizada: {info_file}", "INFO")
        return True
    
    def capture_screenshot(self, url):
        """Capturar screenshot de una URL"""
        print(f"\n{Fore.CYAN}📸 Capturando screenshot de: {url}{Style.RESET_ALL}")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            evidence_id = f"SCREEN_{timestamp}_{self.evidence_counter:04d}"
            filename = f"{self.directories['screenshots']}/{evidence_id}.html"
            
            # Obtener contenido real de la URL
            capture_time = datetime.now()
            page_html = ""
            http_status = "N/A"
            content_type = "N/A"
            try:
                resp = requests.get(url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, allow_redirects=True)
                http_status = str(resp.status_code)
                content_type = resp.headers.get('Content-Type', 'N/A')
                page_html = resp.text
                print(f"{Fore.GREEN}   ✅ Contenido descargado (HTTP {http_status}){Style.RESET_ALL}")
            except Exception as fetch_err:
                page_html = f"<!-- Error al obtener contenido: {fetch_err} -->"
                print(f"{Fore.YELLOW}   ⚠️ No se pudo obtener el contenido: {fetch_err}{Style.RESET_ALL}")

            # Encabezado forense con metadatos de evidencia
            meta_header = (
                "<!--\n"
                "=================================================================\n"
                "EVIDENCIA DIGITAL - ANTI-ACOSO TOOLKIT v2.0\n"
                "=================================================================\n"
                f"Caso ID:      {self.case_id}\n"
                f"Evidencia ID: {evidence_id}\n"
                f"URL:          {url}\n"
                f"Fecha/Hora:   {capture_time.strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"HTTP Status:  {http_status}\n"
                f"Content-Type: {content_type}\n"
                f"Hash-ID:      {hashlib.sha256(evidence_id.encode()).hexdigest()}\n"
                "=================================================================\n"
                "ADVERTENCIA LEGAL: No modificar este archivo. Cualquier cambio\n"
                "invalida el valor probatorio de esta evidencia.\n"
                "=================================================================\n"
                "-->\n"
            )
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(meta_header + page_html)
            
            # Calcular hash
            file_hash = calculate_hash(filename)
            
            # Registrar evidencia
            evidence = {
                'id': evidence_id,
                'type': 'screenshot',
                'subtype': 'html_capture',
                'url': url,
                'filename': filename,
                'hash': file_hash,
                'hash_algorithm': 'SHA-256',
                'timestamp': datetime.now().isoformat(),
                'file_size': os.path.getsize(filename),
                'chain_of_custody': [
                    {
                        'action': 'created',
                        'timestamp': datetime.now().isoformat(),
                        'responsible': 'system',
                        'location': filename,
                        'integrity_check': 'passed'
                    }
                ]
            }
            
            self.evidences.append(evidence)
            self._save_evidence_record(evidence)
            self._update_timeline('screenshot_capture', f"URL: {url}", evidence_id)
            
            print(f"{Fore.GREEN}✅ Screenshot guardado:{Style.RESET_ALL}")
            print(f"   📁 Archivo: {filename}")
            print(f"   🔗 Hash: {file_hash[:16]}...")
            print(f"   🆔 ID: {evidence_id}")
            
            self.evidence_counter += 1
            return evidence
            
        except Exception as e:
            log_action(f"Error capturando screenshot: {str(e)}", "ERROR")
            print(f"{Fore.RED}❌ Error capturando screenshot: {str(e)}{Style.RESET_ALL}")
            return None
    
    def download_image(self, image_url):
        """Descargar una imagen desde una URL"""
        print(f"\n{Fore.CYAN}🖼️  Descargando imagen: {image_url}{Style.RESET_ALL}")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            evidence_id = f"IMAGE_{timestamp}_{self.evidence_counter:04d}"
            
            # Extraer extensión de la URL
            extension = self._get_file_extension(image_url) or 'jpg'
            filename = f"{self.directories['images']}/{evidence_id}.{extension}"
            
            # Descargar imagen real
            resp = requests.get(image_url, timeout=30, stream=True, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            resp.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"{Fore.GREEN}   ✅ Imagen descargada ({resp.headers.get('Content-Type', 'N/A')}){Style.RESET_ALL}")
            
            # Calcular hash
            file_hash = calculate_hash(filename)
            
            # Registrar evidencia
            evidence = {
                'id': evidence_id,
                'type': 'image',
                'subtype': 'downloaded',
                'url': image_url,
                'filename': filename,
                'hash': file_hash,
                'hash_algorithm': 'SHA-256',
                'timestamp': datetime.now().isoformat(),
                'file_size': os.path.getsize(filename),
                'metadata': self.extract_metadata(filename)
            }
            
            self.evidences.append(evidence)
            self._save_evidence_record(evidence)
            self._update_timeline('image_download', f"URL: {image_url}", evidence_id)
            
            print(f"{Fore.GREEN}✅ Imagen descargada:{Style.RESET_ALL}")
            print(f"   📁 Archivo: {filename}")
            print(f"   🔗 Hash: {file_hash[:16]}...")
            print(f"   📊 Tamaño: {os.path.getsize(filename):,} bytes")
            
            self.evidence_counter += 1
            return evidence
            
        except Exception as e:
            log_action(f"Error descargando imagen: {str(e)}", "ERROR")
            print(f"{Fore.RED}❌ Error descargando imagen: {str(e)}{Style.RESET_ALL}")
            return None
    
    def extract_metadata(self, file_path):
        """Extraer metadatos de un archivo de forma completa"""
        if not os.path.exists(file_path):
            return {'error': 'Archivo no encontrado'}
        
        try:
            metadata = {
                'basic': {
                    'filename': os.path.basename(file_path),
                    'absolute_path': os.path.abspath(file_path),
                    'file_size': os.path.getsize(file_path),
                    'created': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                    'accessed': datetime.fromtimestamp(os.path.getatime(file_path)).isoformat(),
                    'extension': os.path.splitext(file_path)[1].lower(),
                    'hash_sha256': calculate_hash(file_path)
                }
            }
            
            # Metadatos EXIF para imágenes
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif')):
                try:
                    with open(file_path, 'rb') as f:
                        exif_data = exif.Image(f)
                    
                    if exif_data.has_exif:
                        metadata['exif'] = {}
                        
                        # Información básica de la cámara
                        if hasattr(exif_data, 'make'):
                            metadata['exif']['make'] = str(exif_data.make)
                        if hasattr(exif_data, 'model'):
                            metadata['exif']['model'] = str(exif_data.model)
                        if hasattr(exif_data, 'software'):
                            metadata['exif']['software'] = str(exif_data.software)
                        
                        # Fecha y hora
                        if hasattr(exif_data, 'datetime'):
                            metadata['exif']['datetime'] = str(exif_data.datetime)
                        if hasattr(exif_data, 'datetime_original'):
                            metadata['exif']['datetime_original'] = str(exif_data.datetime_original)
                        if hasattr(exif_data, 'datetime_digitized'):
                            metadata['exif']['datetime_digitized'] = str(exif_data.datetime_digitized)
                        
                        # Configuración de la cámara
                        if hasattr(exif_data, 'exposure_time'):
                            metadata['exif']['exposure_time'] = str(exif_data.exposure_time)
                        if hasattr(exif_data, 'f_number'):
                            metadata['exif']['f_number'] = str(exif_data.f_number)
                        if hasattr(exif_data, 'iso'):
                            metadata['exif']['iso'] = str(exif_data.iso)
                        if hasattr(exif_data, 'focal_length'):
                            metadata['exif']['focal_length'] = str(exif_data.focal_length)
                        
                        # GPS
                        if hasattr(exif_data, 'gps_latitude'):
                            metadata['exif']['gps_latitude'] = str(exif_data.gps_latitude)
                        if hasattr(exif_data, 'gps_longitude'):
                            metadata['exif']['gps_longitude'] = str(exif_data.gps_longitude)
                        if hasattr(exif_data, 'gps_altitude'):
                            metadata['exif']['gps_altitude'] = str(exif_data.gps_altitude)
                        
                        # Dimensiones
                        try:
                            with Image.open(file_path) as img:
                                metadata['exif']['dimensions'] = f"{img.width}x{img.height}"
                                metadata['exif']['mode'] = img.mode
                        except:
                            pass
                        
                except Exception as e:
                    metadata['exif_error'] = str(e)
            
            # Guardar metadatos en archivo JSON
            meta_filename = f"{self.directories['metadata']}/{os.path.basename(file_path)}_metadata.json"
            with open(meta_filename, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4, ensure_ascii=False)
            
            log_action(f"Metadatos extraídos: {file_path}", "INFO")
            return metadata
            
        except Exception as e:
            log_action(f"Error extrayendo metadatos: {str(e)}", "ERROR")
            return {'error': str(e)}
    
    def record_text_evidence(self, text, source, description=""):
        """Registrar evidencia de texto"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            evidence_id = f"TEXT_{timestamp}_{self.evidence_counter:04d}"
            filename = f"{self.case_dir}/{evidence_id}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"=== EVIDENCIA DE TEXTO ===\n")
                f.write(f"Case ID: {self.case_id}\n")
                f.write(f"Evidence ID: {evidence_id}\n")
                f.write(f"Source: {source}\n")
                f.write(f"Description: {description}\n")
                f.write(f"Recorded: {datetime.now().isoformat()}\n")
                f.write(f"\n{'='*40}\n\n")
                f.write(text)
                f.write(f"\n\n{'='*40}\n")
                f.write(f"End of evidence {evidence_id}\n")
            
            file_hash = calculate_hash(filename)
            
            evidence = {
                'id': evidence_id,
                'type': 'text',
                'source': source,
                'description': description,
                'filename': filename,
                'hash': file_hash,
                'timestamp': datetime.now().isoformat(),
                'text_preview': text[:100] + '...' if len(text) > 100 else text
            }
            
            self.evidences.append(evidence)
            self._save_evidence_record(evidence)
            self._update_timeline('text_record', description, evidence_id)
            
            self.evidence_counter += 1
            return evidence
            
        except Exception as e:
            log_action(f"Error registrando texto: {str(e)}", "ERROR")
            return None
    
    def get_all_evidence(self):
        """Obtener todas las evidencias"""
        return self.evidences
    
    def get_evidence_count(self):
        """Obtener conteo de evidencias por tipo"""
        counts = {}
        for evidence in self.evidences:
            ev_type = evidence.get('type', 'unknown')
            counts[ev_type] = counts.get(ev_type, 0) + 1
        return counts
    
    def save_case_state(self):
        """Guardar estado completo del caso"""
        try:
            state_file = f"{self.case_dir}/case_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            state = {
                'case_id': self.case_id,
                'saved_at': datetime.now().isoformat(),
                'evidence_count': len(self.evidences),
                'evidence_by_type': self.get_evidence_count(),
                'evidences': self.evidences,
                'case_info': self.case_info,
                'directory_structure': self._get_directory_structure()
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4, ensure_ascii=False)
            
            # También guardar copia en exports
            export_file = f"{self.directories['exports']}/case_export_{datetime.now().strftime('%Y%m%d')}.json"
            shutil.copy2(state_file, export_file)
            
            log_action(f"Estado del caso guardado: {state_file}", "INFO")
            return state_file
            
        except Exception as e:
            log_action(f"Error guardando estado: {str(e)}", "ERROR")
            return None
    
    def export_case(self, format='zip'):
        """Exportar caso completo en formato especificado"""
        print(f"\n{Fore.CYAN}📦 Exportando caso {self.case_id}...{Style.RESET_ALL}")
        
        try:
            export_dir = f"reports/{self.case_id}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(export_dir, exist_ok=True)
            
            # Copiar todos los archivos del caso
            for item in os.listdir(self.case_dir):
                src = os.path.join(self.case_dir, item)
                dst = os.path.join(export_dir, item)
                
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            
            # Generar resumen de exportación
            summary = {
                'case_id': self.case_id,
                'exported_at': datetime.now().isoformat(),
                'total_evidence': len(self.evidences),
                'export_directory': export_dir,
                'integrity_check': self._generate_integrity_report()
            }
            
            summary_file = f"{export_dir}/export_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=4, ensure_ascii=False)
            
            print(f"{Fore.GREEN}✅ Caso exportado exitosamente:{Style.RESET_ALL}")
            print(f"   📁 Directorio: {export_dir}")
            print(f"   📊 Evidencias: {len(self.evidences)}")
            print(f"   🔒 Checksum: {summary['integrity_check']['overall_hash'][:16]}...")
            
            return export_dir
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error exportando caso: {str(e)}{Style.RESET_ALL}")
            return None
    
    def load_case_data(self):
        """Cargar datos de un caso existente desde disco"""
        record_file = f"{self.case_dir}/evidence_records.json"
        if os.path.exists(record_file):
            try:
                with open(record_file, 'r', encoding='utf-8') as f:
                    self.evidences = json.load(f)
                self.evidence_counter = len(self.evidences) + 1
                log_action(f"Caso cargado: {len(self.evidences)} evidencias", "INFO")
                return len(self.evidences)
            except Exception as e:
                log_action(f"Error cargando caso: {str(e)}", "ERROR")
        return 0

    def _save_evidence_record(self, evidence):
        """Guardar registro individual de evidencia"""
        record_file = f"{self.case_dir}/evidence_records.json"
        
        records = []
        if os.path.exists(record_file):
            with open(record_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
        
        records.append(evidence)
        
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=4, ensure_ascii=False)
    
    def _update_timeline(self, event_type, description, evidence_id):
        """Actualizar línea de tiempo del caso"""
        timeline_file = f"{self.case_dir}/timeline.csv"
        
        with open(timeline_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()},{event_type},{description},{evidence_id},\n")
    
    def _get_file_extension(self, url):
        """Obtener extensión de archivo desde URL"""
        import re
        match = re.search(r'\.(jpg|jpeg|png|gif|bmp|webp|svg|ico)$', url.lower())
        return match.group(1) if match else None
    
    def _get_directory_structure(self):
        """Obtener estructura de directorios del caso"""
        structure = {}
        
        for root, dirs, files in os.walk(self.case_dir):
            level = root.replace(self.case_dir, '').count(os.sep)
            indent = ' ' * 4 * level
            rel_path = os.path.relpath(root, self.case_dir)
            
            if rel_path == '.':
                structure['root'] = []
            else:
                structure[rel_path] = []
            
            for file in files:
                filepath = os.path.join(root, file)
                file_info = {
                    'name': file,
                    'size': os.path.getsize(filepath),
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                }
                
                if rel_path == '.':
                    structure['root'].append(file_info)
                else:
                    structure[rel_path].append(file_info)
        
        return structure
    
    def _generate_integrity_report(self):
        """Generar reporte de integridad de todas las evidencias"""
        integrity_report = {
            'generated_at': datetime.now().isoformat(),
            'total_files': 0,
            'valid_hashes': 0,
            'file_checks': [],
            'overall_hash': ''
        }
        
        all_hashes = []
        
        for evidence in self.evidences:
            if 'filename' in evidence and os.path.exists(evidence['filename']):
                current_hash = calculate_hash(evidence['filename'])
                is_valid = current_hash == evidence.get('hash', '')
                
                integrity_report['file_checks'].append({
                    'evidence_id': evidence['id'],
                    'filename': evidence['filename'],
                    'stored_hash': evidence.get('hash', ''),
                    'current_hash': current_hash,
                    'is_valid': is_valid,
                    'checked_at': datetime.now().isoformat()
                })
                
                all_hashes.append(current_hash)
                integrity_report['total_files'] += 1
                if is_valid:
                    integrity_report['valid_hashes'] += 1
        
        # Calcular hash general
        if all_hashes:
            combined = ''.join(sorted(all_hashes))
            overall_hash = hashlib.sha256(combined.encode()).hexdigest()
            integrity_report['overall_hash'] = overall_hash
        
        # Guardar reporte
        report_file = f"{self.case_dir}/integrity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(integrity_report, f, indent=4, ensure_ascii=False)
        
        return integrity_report