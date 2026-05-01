#!/usr/bin/env python3
"""
Módulo para análisis de patrones de comportamiento digital
"""

import json
import statistics
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from colorama import Fore, Style
import pandas as pd

class PatternAnalyzer:
    """Clase para analizar patrones de comportamiento en evidencias digitales"""

    # -----------------------------------------------------------------------
    # Palabras clave de amenaza (ES + EN) ordenadas por gravedad
    # -----------------------------------------------------------------------
    THREAT_KEYWORDS = {
        'alta': [
            'matar', 'matarte', 'te voy a matar', 'te mato',
            'violar', 'violarte', 'voy a violar',
            'muerte', 'muerto', 'muerta',
            'kill', 'murder', 'rape', 'dead',
            'bomba', 'bomb', 'disparo', 'arma', 'gun',
            'degollar', 'acuchillar', 'apunalar',
        ],
        'media': [
            'danar', 'hacerte dano', 'hacerte sufrir',
            'destruirte', 'arruinarte', 'acabar contigo',
            'te arrepentiras', 'pagaras', 'te lo juro',
            'hurt', 'destroy', 'ruin', 'suffer',
            'amenaza', 'threat', 'stalk', 'acecho',
            'donde vives', 'se donde estas', 'te encuentro',
        ],
        'baja': [
            'asco', 'odio', 'te odio', 'maldito', 'maldita',
            'suicida', 'muerate', 'desgraciado',
            'hate', 'disgusting', 'worthless', 'loser',
            'basura', 'inutil', 'idiota', 'imbecil',
        ],
    }

    def __init__(self):
        self.patterns = []
        self.time_format = "%Y-%m-%dT%H:%M:%S"

    # -----------------------------------------------------------------------
    # SISTEMA DE SEMAFORO
    # -----------------------------------------------------------------------
    def calculate_risk_level(self, evidences, username_results=None):
        """
        Calcula el nivel de riesgo del caso (BAJO / MEDIO / ALTO).
        Retorna dict completo con score, nivel, factores y descripcion.
        username_results: dict de plataformas encontradas {platform: url}
        """
        score = 0
        factors = []
        threat_words_found = []

        n_ev   = len(evidences) if evidences else 0
        n_plat = len(username_results) if username_results else 0

        # --- Factor 1: Evidencias recopiladas ---
        if n_ev >= 20:
            score += 35
            factors.append(f"Volumen critico de evidencias ({n_ev})")
        elif n_ev >= 10:
            score += 25
            factors.append(f"Volumen significativo de evidencias ({n_ev})")
        elif n_ev >= 5:
            score += 15
            factors.append(f"Evidencias recopiladas ({n_ev})")
        elif n_ev > 0:
            score += 5
            factors.append(f"Evidencias iniciales ({n_ev})")

        # --- Factor 2: Presencia en plataformas ---
        if n_plat >= 6:
            score += 40
            factors.append(f"Presencia masiva en redes sociales ({n_plat} plataformas)")
        elif n_plat >= 3:
            score += 25
            factors.append(f"Presencia multiple en redes ({n_plat} plataformas)")
        elif n_plat >= 1:
            score += 10
            factors.append(f"Presencia detectada ({n_plat} plataforma/s)")

        # --- Factor 3: Patrones temporales (sin output) ---
        if evidences and n_ev >= 3:
            dates = []
            for ev in evidences:
                if 'timestamp' in ev:
                    try:
                        dt = datetime.fromisoformat(
                            ev['timestamp'].replace('Z', '+00:00')
                        )
                        dates.append(dt)
                    except Exception:
                        pass

            if len(dates) >= 4:
                dates.sort()
                # Escalada: segunda mitad mas frecuente que primera
                mid = len(dates) // 2
                f1 = dates[:mid]
                f2 = dates[mid:]
                dur1 = max((f1[-1] - f1[0]).days, 1) if len(f1) > 1 else 1
                dur2 = max((f2[-1] - f2[0]).days, 1) if len(f2) > 1 else 1
                freq1 = len(f1) / dur1
                freq2 = len(f2) / dur2
                if freq2 > freq1 * 1.5:
                    score += 20
                    factors.append("Patron de escalada detectado (frecuencia creciente)")

                # Duracion total del caso
                total_days = (dates[-1] - dates[0]).days
                if total_days >= 30:
                    score += 10
                    factors.append(f"Acoso prolongado ({total_days} dias)")

        # --- Factor 4: Palabras amenazantes ---
        all_text = ""
        for ev in (evidences or []):
            all_text += " " + ev.get('text_preview', '')
            all_text += " " + ev.get('description', '')
        all_text_lower = all_text.lower()

        for kw in self.THREAT_KEYWORDS['alta']:
            if kw in all_text_lower:
                threat_words_found.append(kw)

        for kw in self.THREAT_KEYWORDS['media']:
            if kw in all_text_lower:
                threat_words_found.append(kw)

        if threat_words_found:
            pts = min(len(threat_words_found) * 15, 35)
            score += pts
            factors.append(
                f"Lenguaje amenazante detectado: {', '.join(threat_words_found[:5])}"
            )

        # --- Determinar nivel ---
        if score >= 65:
            level, urgencia = 'ALTO', 'URGENTE'
            color = Fore.RED
            descripcion = (
                "Caso de alto riesgo. Presenta indicadores de amenazas graves "
                "o acoso sistematico. Denuncia policial inmediata recomendada."
            )
        elif score >= 30:
            level, urgencia = 'MEDIO', 'PRIORITARIO'
            color = Fore.YELLOW
            descripcion = (
                "Patron de acoso identificado con evidencias. "
                "Documenta y presenta denuncia formal cuanto antes."
            )
        else:
            level, urgencia = 'BAJO', 'PLANIFICADO'
            color = Fore.GREEN
            descripcion = (
                "Evidencias preliminares. Continua documentando "
                "antes de presentar denuncia formal."
            )

        return {
            'level':       level,
            'score':       score,
            'color':       color,
            'urgencia':    urgencia,
            'descripcion': descripcion,
            'factors':     factors,
            'threats':     threat_words_found,
            'n_evidences': n_ev,
            'n_platforms': n_plat,
        }

    def display_risk_semaphore(self, risk, compact=False):
        """
        Muestra el semaforo de riesgo en consola.
        compact=True: version corta para el menu principal.
        compact=False: version completa con factores.
        """
        level  = risk['level']
        color  = risk['color']
        score  = risk['score']

        # Indicadores del semaforo
        dot_alto   = (Fore.RED    + " ALTO  " + Style.RESET_ALL
                      if level == 'ALTO'  else " ALTO  ")
        dot_medio  = (Fore.YELLOW + " MEDIO " + Style.RESET_ALL
                      if level == 'MEDIO' else " MEDIO ")
        dot_bajo   = (Fore.GREEN  + " BAJO  " + Style.RESET_ALL
                      if level == 'BAJO'  else " BAJO  ")

        filled  = "#" if level == 'ALTO'  else "."
        filled2 = "#" if level != 'BAJO'  else "."
        filled3 = "#"

        if compact:
            # Una sola linea para el menu
            ind = f"[{'!!!' if level=='ALTO' else '!!' if level=='MEDIO' else ' ok'}]"
            print(
                f"{color}  {ind} RIESGO {level} (score {score}/100)"
                f"  {risk['urgencia']}{Style.RESET_ALL}"
            )
            return

        # Version completa
        w = 60
        print(f"\n{color}{'='*w}{Style.RESET_ALL}")
        print(f"{color}  SEMAFORO DE RIESGO  |  {level}  |  {score}/100  |  {risk['urgencia']}{Style.RESET_ALL}")
        print(f"{color}{'='*w}{Style.RESET_ALL}\n")

        # Semaforo visual en ASCII
        s_alto  = Fore.RED    + "[#]" + Style.RESET_ALL if level == 'ALTO'  else Fore.WHITE + "[ ]" + Style.RESET_ALL
        s_med   = Fore.YELLOW + "[#]" + Style.RESET_ALL if level == 'MEDIO' else Fore.WHITE + "[ ]" + Style.RESET_ALL
        s_bajo  = Fore.GREEN  + "[#]" + Style.RESET_ALL if level == 'BAJO'  else Fore.WHITE + "[ ]" + Style.RESET_ALL

        print(f"    +-------+")
        print(f"    | {s_alto}  |   {Fore.RED}ALTO{Style.RESET_ALL}   - Amenazas / acoso severo")
        print(f"    |       |")
        print(f"    | {s_med}  |   {Fore.YELLOW}MEDIO{Style.RESET_ALL}  - Patron de acoso identificado")
        print(f"    |       |")
        print(f"    | {s_bajo}  |   {Fore.GREEN}BAJO{Style.RESET_ALL}   - Evidencias preliminares")
        print(f"    +-------+\n")

        print(f"  {color}{risk['descripcion']}{Style.RESET_ALL}\n")

        if risk['factors']:
            print(f"  {Fore.CYAN}Factores detectados:{Style.RESET_ALL}")
            for f in risk['factors']:
                print(f"    {color}>{Style.RESET_ALL} {f}")

        if risk['threats']:
            print(f"\n  {Fore.RED}Lenguaje amenazante: {', '.join(risk['threats'])}{Style.RESET_ALL}")

        print()

    def get_statistics(self, evidences):
        """Obtener estadísticas detalladas de las evidencias"""
        print(f"\n{Fore.CYAN}📊 Generando estadísticas de {len(evidences)} evidencias...{Style.RESET_ALL}")
        
        if not evidences:
            return {
                'total_evidencias': 0,
                'error': 'No hay evidencias para analizar'
            }
        
        stats = {
            'total_evidencias': len(evidences),
            'por_tipo': {},
            'por_fuente': {},
            'linea_temporal': [],
            'frecuencia_diaria': {},
            'horas_pico': {},
            'dias_activos': {},
            'duracion_caso': None,
            'evidencias_por_dia': None,
            'patrones_temporales': {}
        }
        
        # Extraer todas las fechas
        dates = []
        for ev in evidences:
            if 'timestamp' in ev:
                try:
                    dt = datetime.fromisoformat(ev['timestamp'].replace('Z', '+00:00'))
                    dates.append(dt)
                    
                    # Agrupar por tipo
                    ev_type = ev.get('type', 'desconocido')
                    stats['por_tipo'][ev_type] = stats['por_tipo'].get(ev_type, 0) + 1
                    
                    # Agrupar por fuente
                    source = ev.get('source', ev.get('url', 'desconocida'))
                    if source:
                        source_key = source[:50] + ('...' if len(source) > 50 else '')
                        stats['por_fuente'][source_key] = stats['por_fuente'].get(source_key, 0) + 1
                    
                    # Línea temporal
                    stats['linea_temporal'].append({
                        'fecha': dt.strftime('%Y-%m-%d'),
                        'hora': dt.strftime('%H:%M:%S'),
                        'timestamp': dt.isoformat(),
                        'tipo': ev_type,
                        'id': ev.get('id', ''),
                        'descripcion': self._get_evidence_description(ev)
                    })
                    
                    # Horas pico
                    hour = dt.hour
                    stats['horas_pico'][hour] = stats['horas_pico'].get(hour, 0) + 1
                    
                    # Días activos
                    weekday = dt.strftime('%A')
                    stats['dias_activos'][weekday] = stats['dias_activos'].get(weekday, 0) + 1
                    
                except Exception as e:
                    continue
        
        if dates:
            # Duración del caso
            dates.sort()
            stats['duracion_caso'] = {
                'inicio': dates[0].strftime('%Y-%m-%d %H:%M:%S'),
                'fin': dates[-1].strftime('%Y-%m-%d %H:%M:%S'),
                'dias_totales': (dates[-1] - dates[0]).days + 1,
                'dias_activos': len(set([d.strftime('%Y-%m-%d') for d in dates]))
            }
            
            # Frecuencia diaria
            for date in dates:
                date_str = date.strftime('%Y-%m-%d')
                stats['frecuencia_diaria'][date_str] = stats['frecuencia_diaria'].get(date_str, 0) + 1
            
            # Evidencias por día promedio
            days_active = stats['duracion_caso']['dias_activos']
            if days_active > 0:
                stats['evidencias_por_dia'] = len(evidences) / days_active
            
            # Análisis de patrones temporales
            stats['patrones_temporales'] = self._analyze_time_patterns(dates)
        
        print(f"{Fore.GREEN}✅ Estadísticas generadas exitosamente{Style.RESET_ALL}")
        return stats
    
    def _get_evidence_description(self, evidence):
        """Obtener descripción legible de una evidencia"""
        ev_type = evidence.get('type', 'desconocido')
        
        descriptions = {
            'screenshot': f"Captura de {evidence.get('url', 'URL desconocida')}",
            'image': f"Imagen de {evidence.get('url', 'fuente desconocida')}",
            'text': f"Texto: {evidence.get('text_preview', 'sin vista previa')}",
            'video': f"Video de {evidence.get('source', 'fuente desconocida')}",
            'audio': f"Audio de {evidence.get('source', 'fuente desconocida')}"
        }
        
        return descriptions.get(ev_type, f"Evidencia tipo {ev_type}")
    
    def _analyze_time_patterns(self, dates):
        """Analizar patrones temporales en las fechas"""
        if len(dates) < 2:
            return {'error': 'Datos insuficientes para análisis temporal'}
        
        dates.sort()
        patterns = {
            'intervalos': [],
            'frecuencia_promedio': None,
            'horas_activas': [],
            'dias_mas_activos': [],
            'escalada': False,
            'periodicidad': None
        }
        
        # Calcular intervalos entre eventos
        intervals = []
        for i in range(1, len(dates)):
            interval = (dates[i] - dates[i-1]).total_seconds() / 3600  # Horas
            intervals.append(interval)
        
        if intervals:
            patterns['intervalos'] = {
                'min': min(intervals),
                'max': max(intervals),
                'promedio': statistics.mean(intervals),
                'mediana': statistics.median(intervals)
            }
            
            patterns['frecuencia_promedio'] = 24 / patterns['intervalos']['promedio'] if patterns['intervalos']['promedio'] > 0 else 0
        
        # Horas más activas
        hour_counts = Counter([d.hour for d in dates])
        if hour_counts:
            top_hours = hour_counts.most_common(3)
            patterns['horas_activas'] = [{'hora': h, 'count': c} for h, c in top_hours]
        
        # Días más activos
        day_counts = Counter([d.strftime('%A') for d in dates])
        if day_counts:
            top_days = day_counts.most_common(3)
            patterns['dias_mas_activos'] = [{'dia': d, 'count': c} for d, c in top_days]
        
        # Detectar escalada
        if len(dates) >= 4:
            split_point = len(dates) // 2
            first_half = dates[:split_point]
            second_half = dates[split_point:]
            
            freq_first = len(first_half) / ((first_half[-1] - first_half[0]).days + 1) if len(first_half) > 1 else 0
            freq_second = len(second_half) / ((second_half[-1] - second_half[0]).days + 1) if len(second_half) > 1 else 0
            
            patterns['escalada'] = freq_second > freq_first * 1.5  # 50% más frecuente
        
        # Detectar periodicidad (días específicos de la semana)
        weekdays = [d.weekday() for d in dates]  # 0 = lunes, 6 = domingo
        weekday_counts = Counter(weekdays)
        if len(set(weekdays)) <= 3 and len(dates) >= 5:  # Si se concentra en 3 días o menos
            patterns['periodicidad'] = 'concentrado_en_dias_especificos'
        
        return patterns
    
    def get_recommendations(self, stats):
        """Obtener recomendaciones basadas en estadísticas"""
        recommendations = []
        
        total = stats.get('total_evidencias', 0)
        
        if total == 0:
            recommendations.append("📝 **Recopila más evidencias** antes de proceder con análisis")
            recommendations.append("🎯 **Enfócate en diferentes tipos** de evidencias (screenshots, textos, imágenes)")
            return recommendations
        
        # Recomendaciones basadas en cantidad
        if total < 5:
            recommendations.append("📈 **Aumenta la recopilación** - Con menos de 5 evidencias el caso es débil")
        elif total >= 5 and total < 10:
            recommendations.append("✅ **Caso viable** - Tienes suficientes evidencias para una denuncia preliminar")
            recommendations.append("📋 **Organiza por fecha** - Crea una línea de tiempo clara")
        else:
            recommendations.append("💪 **Caso sólido** - Tienes un volumen significativo de evidencias")
            recommendations.append("⚖️ **Procede con denuncia formal** - El caso está bien documentado")
        
        # Recomendaciones basadas en tipos
        evidence_types = stats.get('por_tipo', {})
        
        if 'screenshot' in evidence_types:
            recommendations.append("🖼️ **Los screenshots son excelentes** - Asegúrate de que muestren URL y fecha completa")
        
        if 'text' in evidence_types:
            recommendations.append("📝 **Textos documentados** - Incluye contexto y fuente de cada mensaje")
        
        if 'image' in evidence_types:
            recommendations.append("🔍 **Analiza metadatos** de imágenes - Pueden contener información valiosa")
        
        # Recomendaciones basadas en temporalidad
        if stats.get('patrones_temporales', {}).get('escalada', False):
            recommendations.append("⚠️ **PATRÓN DETECTADO: Escalada** - La frecuencia ha aumentado, indica urgencia")
        
        if stats.get('patrones_temporales', {}).get('horas_activas'):
            top_hour = stats['patrones_temporales']['horas_activas'][0]['hora']
            recommendations.append(f"🕐 **Patrón horario**: Mayor actividad alrededor de las {top_hour}:00")
        
        # Recomendaciones legales
        recommendations.append("👨‍⚖️ **Consulta con un abogado** especializado en delitos digitales")
        recommendations.append("📞 **Contacta a las autoridades**: Policía Nacional - Grupo de Delitos Telemáticos")
        recommendations.append("🏛️ **Prepara documentación** para Fiscalía de Violencia Digital")
        
        # Recomendaciones técnicas
        recommendations.append("🔒 **Mantén copias de seguridad** en diferentes ubicaciones")
        recommendations.append("📊 **Genera informes periódicos** del progreso del caso")
        recommendations.append("🔄 **Actualiza evidencias** regularmente si el acoso continúa")
        
        return recommendations
    
    def generate_visual_report(self, stats, output_dir):
        """Generar reporte visual con gráficos"""
        try:
            print(f"\n{Fore.CYAN}📈 Generando reporte visual...{Style.RESET_ALL}")
            
            # Configurar estilo
            plt.style.use('seaborn-v0_8-darkgrid')
            sns.set_palette("husl")
            
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'Análisis Forense Digital - Caso {stats.get("case_id", "Desconocido")}', 
                        fontsize=16, fontweight='bold')
            
            # 1. Gráfico de tipos de evidencia
            if stats.get('por_tipo'):
                ax1 = axes[0, 0]
                types = list(stats['por_tipo'].keys())
                counts = list(stats['por_tipo'].values())
                
                bars = ax1.bar(types, counts, color=sns.color_palette("husl", len(types)))
                ax1.set_title('Tipos de Evidencia Recopilada', fontweight='bold')
                ax1.set_xlabel('Tipo de Evidencia')
                ax1.set_ylabel('Cantidad')
                ax1.tick_params(axis='x', rotation=45)
                
                # Añadir etiquetas
                for bar, count in zip(bars, counts):
                    height = bar.get_height()
                    ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            f'{count}', ha='center', va='bottom')
            
            # 2. Gráfico de frecuencia diaria
            if stats.get('frecuencia_diaria'):
                ax2 = axes[0, 1]
                dates = list(stats['frecuencia_diaria'].keys())
                frequencies = list(stats['frecuencia_diaria'].values())
                
                # Ordenar por fecha
                sorted_data = sorted(zip(dates, frequencies), key=lambda x: x[0])
                dates, frequencies = zip(*sorted_data) if sorted_data else ([], [])
                
                ax2.plot(dates, frequencies, marker='o', linewidth=2, markersize=6)
                ax2.set_title('Frecuencia de Actividad Diaria', fontweight='bold')
                ax2.set_xlabel('Fecha')
                ax2.set_ylabel('Evidencias por día')
                ax2.tick_params(axis='x', rotation=45)
                ax2.grid(True, alpha=0.3)
            
            # 3. Gráfico de horas pico
            if stats.get('horas_pico'):
                ax3 = axes[1, 0]
                hours = list(range(24))
                counts = [stats['horas_pico'].get(h, 0) for h in hours]
                
                bars = ax3.bar(hours, counts, color='skyblue', edgecolor='black')
                ax3.set_title('Distribución por Hora del Día', fontweight='bold')
                ax3.set_xlabel('Hora')
                ax3.set_ylabel('Número de Evidencias')
                ax3.set_xticks(range(0, 24, 2))
                ax3.set_xlim(-0.5, 23.5)
            
            # 4. Gráfico de días activos
            if stats.get('dias_activos'):
                ax4 = axes[1, 1]
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                days = [day for day in days_order if day in stats['dias_activos']]
                counts = [stats['dias_activos'].get(day, 0) for day in days]
                
                bars = ax4.bar(days, counts, color='lightcoral', edgecolor='black')
                ax4.set_title('Actividad por Día de la Semana', fontweight='bold')
                ax4.set_xlabel('Día')
                ax4.set_ylabel('Número de Evidencias')
                ax4.tick_params(axis='x', rotation=45)
                
                # Añadir etiquetas
                for bar, count in zip(bars, counts):
                    height = bar.get_height()
                    ax4.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            f'{count}', ha='center', va='bottom')
            
            # Ajustar layout
            plt.tight_layout()
            
            # Guardar gráfico
            output_path = f"{output_dir}/analisis_visual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"{Fore.GREEN}✅ Reporte visual guardado: {output_path}{Style.RESET_ALL}")
            return output_path
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error generando reporte visual: {str(e)}{Style.RESET_ALL}")
            return None
    
    def analyze_communication_patterns(self, text_evidences):
        """Analizar patrones en comunicaciones de texto"""
        if not text_evidences:
            return {'error': 'No hay evidencias de texto para analizar'}
        
        analysis = {
            'total_mensajes': len(text_evidences),
            'vocabulario_analisis': {},
            'sentimiento_basico': {},
            'patrones_linguisticos': [],
            'terminos_amenazantes': []
        }
        
        all_text = ""
        for ev in text_evidences:
            if 'text_preview' in ev:
                all_text += ev['text_preview'] + " "
        
        # Análisis básico de vocabulario
        words = all_text.lower().split()
        word_counts = Counter(words)
        
        # Filtrar palabras comunes
        common_words = {'el', 'la', 'los', 'las', 'de', 'en', 'y', 'a', 'que', 'por', 'con', 'para', 'me', 'te', 'se'}
        filtered_words = {word: count for word, count in word_counts.items() 
                         if word not in common_words and len(word) > 2}
        
        analysis['vocabulario_analisis'] = {
            'total_palabras': len(words),
            'palabras_unicas': len(set(words)),
            'palabras_mas_usadas': dict(sorted(filtered_words.items(), 
                                              key=lambda x: x[1], 
                                              reverse=True)[:10])
        }
        
        # Detectar términos amenazantes
        threat_keywords = [
            'matar', 'muerte', 'daño', 'herir', 'violar', 'acabar', 'terminar',
            'amenaza', 'peligro', 'miedo', 'sufrir', 'dolor', 'castigar'
        ]
        
        found_threats = []
        for keyword in threat_keywords:
            if keyword in all_text.lower():
                found_threats.append(keyword)
        
        analysis['terminos_amenazantes'] = found_threats
        
        # Patrones lingüísticos básicos
        patterns = []
        
        # Exclamaciones e interrogaciones
        exclamation_count = all_text.count('!') + all_text.count('¡')
        question_count = all_text.count('?') + all_text.count('¿')
        
        if exclamation_count > len(text_evidences) * 2:  # Más de 2 por mensaje en promedio
            patterns.append("Uso excesivo de exclamaciones (tono agresivo/emocional)")
        
        if question_count > len(text_evidences):
            patterns.append("Muchas preguntas (posible acoso interrogativo)")
        
        # Longitud promedio
        avg_length = sum(len(ev.get('text_preview', '')) for ev in text_evidences) / len(text_evidences)
        if avg_length > 500:
            patterns.append("Mensajes largos (posible acoso por sobrecarga)")
        elif avg_length < 50:
            patterns.append("Mensajes cortos y repetitivos (posible acoso persistente)")
        
        analysis['patrones_linguisticos'] = patterns
        
        return analysis
    
    def generate_summary_report(self, stats, output_dir):
        """Generar reporte de resumen ejecutivo"""
        try:
            summary = {
                'generated_at': datetime.now().isoformat(),
                'case_overview': {
                    'total_evidence': stats.get('total_evidencias', 0),
                    'duration_days': stats.get('duracion_caso', {}).get('dias_totales', 0),
                    'active_days': stats.get('duracion_caso', {}).get('dias_activos', 0),
                    'evidence_per_day': stats.get('evidencias_por_dia', 0)
                },
                'key_findings': [],
                'risk_assessment': {},
                'recommended_actions': []
            }
            
            # Hallazgos clave
            if stats.get('total_evidencias', 0) > 0:
                summary['key_findings'].append(f"Total de evidencias recopiladas: {stats['total_evidencias']}")
            
            if stats.get('patrones_temporales', {}).get('escalada', False):
                summary['key_findings'].append("🔴 ESCALADA DETECTADA: La frecuencia del acoso ha aumentado significativamente")
            
            if stats.get('patrones_temporales', {}).get('horas_activas'):
                top_hour = stats['patrones_temporales']['horas_activas'][0]
                summary['key_findings'].append(f"Hora pico de actividad: {top_hour['hora']}:00 ({top_hour['count']} eventos)")
            
            # Evaluación de riesgo
            risk_level = 'BAJO'
            if stats.get('total_evidencias', 0) >= 10:
                risk_level = 'MEDIO'
            if stats.get('total_evidencias', 0) >= 20 or stats.get('patrones_temporales', {}).get('escalada', False):
                risk_level = 'ALTO'
            
            summary['risk_assessment'] = {
                'level': risk_level,
                'factors': [],
                'recommended_response': 'Urgente' if risk_level == 'ALTO' else 'Prioritario' if risk_level == 'MEDIO' else 'Planificado'
            }
            
            # Guardar reporte
            report_file = f"{output_dir}/resumen_ejecutivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=4, ensure_ascii=False)
            
            print(f"{Fore.GREEN}✅ Reporte ejecutivo guardado: {report_file}{Style.RESET_ALL}")
            return report_file
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error generando reporte ejecutivo: {str(e)}{Style.RESET_ALL}")
            return None