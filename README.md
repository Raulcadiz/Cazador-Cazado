# 🛡️ LINCE — Anti-Acoso Digital Toolkit

> Herramienta forense de línea de comandos para la **documentación legal de acoso digital**. Diseñada para víctimas, abogados y profesionales que necesitan recopilar, organizar y presentar evidencias digitales ante autoridades.

**Lee [LEGAL.md](LEGAL.md) antes de usar esta herramienta.**

---

## ⚠️ ADVERTENCIA LEGAL

```
USO EXCLUSIVAMENTE ÉTICO Y LEGAL.

PERMITIDO:  Documentar acoso recibido · Preparar denuncias · Generar
            informes para abogados · Investigación con fines de protección.

PROHIBIDO:  Acosar o intimidar · Violar privacidad sin consentimiento ·
            Venganza personal · Vigilancia no autorizada · Cualquier
            actividad ilegal.

El usuario es el único responsable del uso que haga de esta herramienta.
```

→ Guía completa: [LEGAL.md](LEGAL.md)

---

## ✨ Qué hace

| Modo | Descripción |
|------|-------------|
| 🔍 **Investigar** | Rastrea la huella digital del acosador en 40+ plataformas vía OSINT |
| 🛡️ **Proteger** | Monitoriza menciones de la víctima en Twitter y detecta nuevas amenazas |
| 📄 **Documentar** | Genera expedientes legales Word (.docx) con cadena de custodia forense |
| 📦 **Archivar** | Preserva evidencias en Wayback Machine (URL permanente e inalterable) |

---

## 📦 Instalación

```bash
# 1. Clonar
git clone https://github.com/Raulcadiz/Cazador-Cazado.git
cd Cazador-Cazado

# 2. Entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS

# 3. Dependencias
pip install -r requirements.txt

# 4. Browser stealth (para bypass Cloudflare en Nitter)
scrapling install

# 5. Ejecutar
python main.py
```

> **Python 3.11 o superior requerido.**

---

## 🚀 Menú principal

```
[1]  Definir objetivo (acosador)
[2]  Búsqueda de huella digital   — 40+ plataformas
[3]  Análisis de redes sociales
[4]  Captura de evidencias        — HTML real + hash SHA-256
[5]  Análisis de patrones
[6]  Búsqueda inversa de imágenes
[7]  Análisis de metadatos EXIF
[8]  Generar informes legales     — Word .docx para policía/abogado
[9]  Dashboard de estadísticas
[10] Configuración y ética
[11] Vigilancia automática del acosador
[12] Baliza de alerta
[13] Escudo de protección ←── NUEVO
[0]  Salir
```

---

## 🛡️ Menú 13 — Escudo de Protección (nuevo)

Modo defensivo centrado en la **víctima**, no en el acosador:

```
[1]  Dashboard en vivo           — riesgo, evidencias, plataformas
[2]  Guía de privacidad          — pasos urgentes + configuración por red social
[3]  Plantillas de denuncia      — cómo reportar en Twitter, Instagram, TikTok...
[4]  Escudo legal (.docx)        — documento completo para el abogado

── MODO PROTECCIÓN DE VÍCTIMA ──
[5]  Definir víctima a proteger  — usuario diferente al acosador investigado
[6]  Escanear menciones AHORA    — detección inmediata de amenazas
[7]  Monitor automático          — escaneo periódico en background
[8]  Ver alertas guardadas       — historial de amenazas detectadas
[9]  Exportar alertas a .docx    — informe para abogado
[t]  Configurar twscrape         — scraping directo Twitter (máxima fiabilidad)
```

### Cómo funciona el monitor de víctima

```
Twitter menciones
  │
  ├─ twscrape (si configurado)       ← PRIORIDAD 1: scraping directo, más fiable
  ├─ Scrapling StealthyFetcher       ← PRIORIDAD 2: Camoufox, bypasa Cloudflare
  ├─ Scrapling Fetcher               ← PRIORIDAD 3: TLS fingerprint spoof
  └─ DuckDuckGo Search               ← SIEMPRE activo como complemento

Resultado → Clasificador de amenazas (Art. 169 / Art. 173 CP)
         → Wayback Machine auto-archive (evidencia permanente)
         → Alerta Telegram / email
         → JSON forense en data/{caso}/shield/
         → .docx exportable para abogado
```

### Monitor en segundo plano (sin tener el toolkit abierto)

```bash
python setup_monitor.py install 4   # cada 4 horas via Task Scheduler
python setup_monitor.py status
python setup_monitor.py run         # ciclo inmediato
python setup_monitor.py remove
```

---

## 🌐 Stack de scraping

| Capa | Herramienta | Cuándo actúa |
|------|-------------|--------------|
| **Nivel 1** | [twscrape](https://github.com/vladkens/twscrape) | Con cuenta Twitter configurada |
| **Nivel 2** | [Scrapling](https://github.com/D4Vinci/Scrapling) StealthyFetcher | Instancias Nitter con Cloudflare |
| **Nivel 3** | Scrapling Fetcher (TLS spoof) | Instancias Nitter sin Cloudflare |
| **Nivel 4** | DuckDuckGo Search (ddgs) | Siempre activo como complemento |
| **Fallback** | requests | Sin Scrapling instalado |

> Las instancias Nitter se comprueban con **healthcheck automático** antes de usar.  
> Si una instancia cae, pasa automáticamente a la siguiente.

---

## 📄 Tipos de informes generados

| Informe | Destinatario | Contenido |
|---------|-------------|-----------|
| Denuncia policial | Policía / GC | Evidencias + hashes SHA-256 + Art. CP aplicables |
| Informe legal | Abogado/a | Catalogación jurídica completa |
| Escudo legal | Abogado/víctima | 7 secciones: riesgo, evidencias, plataformas, ley, denuncia... |
| Alertas de monitor | Abogado | Registro cronológico de amenazas con URLs Wayback |
| Reporte de plataformas | Instagram/Twitter... | Solicitud de eliminación de contenido |

---

## 🔒 Cadena de custodia forense

Cada evidencia capturada incluye:
- **Hash SHA-256** calculado en el momento de la captura
- **Timestamp ISO 8601** con fecha y hora exacta
- **Archivo permanente en Wayback Machine** (no puede ser borrado por el acosador)
- **`chain_of_custody.json`** con cada acceso al archivo

---

## 📁 Estructura del proyecto

```
Cazador-Cazado/
├── main.py                    # CLI principal — AntiAcosoToolkit
├── setup_monitor.py           # Configura Task Scheduler para monitor en background
├── config.yaml                # Configuración: plataformas, alertas, límites
├── requirements.txt
├── LEGAL.md                   # Guía legal completa
│
├── modules/
│   ├── investigator.py        # OSINT: 40+ plataformas + Twitter/Nitter
│   ├── evidence.py            # Capturas HTML reales + Wayback Machine
│   ├── analyzer.py            # Análisis de patrones, nivel de riesgo
│   ├── reporter.py            # Informes Word (.docx)
│   ├── shield.py              # Dashboard, guía privacidad, escudo legal
│   ├── victim_watcher.py      # Monitor de víctima: Scrapling + twscrape + DDG
│   ├── watcher.py             # Vigilancia del acosador
│   ├── alerts.py              # Sistema de alertas (Telegram / email)
│   └── utils.py               # Utilidades: hash, log, banner
│
├── data/                      # [.gitignore] Datos de casos (CONFIDENCIAL)
│   └── CASE-YYYYMMDD/
│       ├── case_info.json
│       ├── evidence_records.json
│       ├── chain_of_custody.json
│       └── shield/            # Alertas del monitor de víctima
│
└── reports/                   # [.gitignore] Informes generados
```

---

## ⚙️ Configuración (`config.yaml`)

```yaml
# Alertas automáticas (monitor de víctima)
telegram:
  bot_token: "TU_TOKEN"
  chat_id:   "TU_CHAT_ID"

email:
  enabled:   false
  smtp_host: "smtp.gmail.com"
  smtp_port: 465
  username:  "tu@gmail.com"
  password:  "app_password"
  from:      "tu@gmail.com"
  to:        "destino@gmail.com"

# Intervalo del monitor de víctima (horas)
shield_interval_hours: 4
```

---

## ⚖️ Marco legal de referencia (España)

| Artículo | Delito | Pena |
|----------|--------|------|
| Art. 169-171 CP | Amenazas graves | 1–5 años |
| Art. 172 ter CP | Stalking digital | hasta 5 años |
| Art. 173 CP | Trato degradante reiterado | hasta 2 años |
| Art. 510 CP | Discurso de odio | hasta 4 años |
| **Art. 588 LECr** | **Solicitud judicial de datos a plataformas** | Twitter/X obligada a entregar IP + email + nombre real |

> **Prescripción**: 5 años. Documenta cuanto antes.

---

## 📞 Recursos de ayuda (España)

| Recurso | Contacto |
|---------|----------|
| Violencia de género | **016** — gratuito, 24h |
| Emergencia física | **112** |
| Ciberacoso — INCIBE | **017** — [osi.es](https://osi.es) |
| GDT — Policía Nacional | [policia.es/denuncia_web](https://www.policia.es/denuncia_web) |
| AEPD — Protección de datos | [aepd.es](https://www.aepd.es) |
| Fiscalía digital | [fiscal.es](https://www.fiscal.es) |

---

## 🤝 Contribuir

Las contribuciones son bienvenidas si mantienen el propósito ético.

```bash
git checkout -b feature/mi-mejora
# ... cambios ...
git push origin feature/mi-mejora
# → Abre Pull Request
```

**No se aceptan PRs que** eliminen advertencias legales, añadan evasión de autenticación o conviertan la herramienta en instrumento de vigilancia masiva.

---

<p align="center">
  <strong>LINCE — Herramienta Forense Digital Ética</strong><br>
  v2.1.0 · Mayo 2026 · Uso exclusivo para documentación legal
</p>
