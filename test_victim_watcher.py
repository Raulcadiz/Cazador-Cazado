#!/usr/bin/env python3
"""
Test rapido de VictimWatcher con Scrapling.
Ejecutar desde el directorio raiz del proyecto:
  python test_victim_watcher.py
"""
import sys, os
# Forzar UTF-8 en terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from colorama import init, Fore, Style
init(autoreset=True)

print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
print(f"{Fore.YELLOW}  TEST VictimWatcher + Scrapling{Style.RESET_ALL}")
print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

# ── 1. Verificar dependencias ────────────────────────────────────────────────
print(f"{Fore.YELLOW}[1] Dependencias:{Style.RESET_ALL}")

try:
    from scrapling.fetchers import Fetcher
    print(f"  {Fore.GREEN}OK{Style.RESET_ALL} scrapling.Fetcher          (TLS spoof)")
except ImportError:
    print(f"  {Fore.RED}--{Style.RESET_ALL} scrapling NO instalado  →  pip install \"scrapling[fetchers]\"")

try:
    from scrapling.fetchers import StealthyFetcher
    print(f"  {Fore.GREEN}OK{Style.RESET_ALL} scrapling.StealthyFetcher  (Cloudflare bypass)")
    stealth_ok = True
except ImportError:
    print(f"  {Fore.YELLOW}~~{Style.RESET_ALL} StealthyFetcher no disponible  →  scrapling install")
    stealth_ok = False

try:
    from bs4 import BeautifulSoup
    print(f"  {Fore.GREEN}OK{Style.RESET_ALL} BeautifulSoup4")
except ImportError:
    print(f"  {Fore.RED}--{Style.RESET_ALL} beautifulsoup4 NO instalado")

try:
    from ddgs import DDGS
    print(f"  {Fore.GREEN}OK{Style.RESET_ALL} ddgs (DuckDuckGo Search)")
except ImportError:
    print(f"  {Fore.YELLOW}~~{Style.RESET_ALL} ddgs no instalado  (fuente secundaria desactivada)")

from modules.victim_watcher import (
    SCRAPLING_OK, SCRAPLING_STEALTH, TWSCRAPE_OK,
    _smart_get, _parse_nitter_html,
    _fetch_nitter, _fetch_ddg, _clasificar,
    _nitter_is_alive, _best_nitter, _wayback_archive,
    NITTER_INSTANCES,
)

print(f"\n  Fetcher activo: ", end="")
if TWSCRAPE_OK:
    print(f"{Fore.GREEN}twscrape{Style.RESET_ALL}")
elif SCRAPLING_STEALTH:
    print(f"{Fore.GREEN}Scrapling + StealthyFetcher{Style.RESET_ALL}")
elif SCRAPLING_OK:
    print(f"{Fore.YELLOW}Scrapling Fetcher (sin stealth){Style.RESET_ALL}")
else:
    print(f"{Fore.RED}requests (basico){Style.RESET_ALL}")

# ── 2. Test _clasificar ──────────────────────────────────────────────────────
print(f"\n{Fore.YELLOW}[2] Clasificador de amenazas:{Style.RESET_ALL}")
casos = [
    ("Cuando beses cuneta dejaras de insultar. Putilla comunista",
     "AMENAZA"),
    ("te voy a matar si no te callas",                            "AMENAZA"),
    ("eres una imbecil y una ignorante",                          "VIGILANCIA"),
    ("muy buen contenido sigue adelante",                         None),
    ("hola bb estas sola?",                                       None),
]
ok = True
for texto, esperado in casos:
    resultado = _clasificar(texto)
    igual = resultado == esperado
    if not igual:
        ok = False
    mark = f"{Fore.GREEN}OK{Style.RESET_ALL}" if igual else f"{Fore.RED}--{Style.RESET_ALL}"
    print(f"  {mark} [{resultado or 'OK':10}] {texto[:55]}")
print(f"  {'Clasificador: ' + (Fore.GREEN+'PASS'+Style.RESET_ALL if ok else Fore.RED+'FAIL'+Style.RESET_ALL)}")

# ── 3. Test _smart_fetch contra xcancel.com ──────────────────────────────────
print(f"\n{Fore.YELLOW}[3] Healthcheck de instancias Nitter:{Style.RESET_ALL}")
for inst in NITTER_INSTANCES[:4]:
    alive = _nitter_is_alive(inst, timeout=6)
    mark  = f"{Fore.GREEN}OK VIVA {Style.RESET_ALL}" if alive else f"{Fore.RED}-- DOWN {Style.RESET_ALL}"
    print(f"  {mark} {inst}")

best = _best_nitter()
print(f"\n  Mejor instancia: {Fore.GREEN if best else Fore.RED}{best or 'ninguna'}{Style.RESET_ALL}")

status, html = 0, ""
if best:
    print(f"\n{Fore.YELLOW}[3b] Fetch menciones en '{best}':{Style.RESET_ALL}")
    status, html = _smart_get(f"{best}/search?q=%40Tamikarnaval&f=tweets",
                               nitter_base=best, timeout=20)
    print(f"  HTTP {status}, {len(html):,} bytes")
    if status == 200 and len(html) > 1000:
        tweets = _parse_nitter_html(html)
        print(f"  Tweets parseados: {len(tweets)}")
        for tw in tweets[:3]:
            print(f"    [{tw['author']}] {tw['text'][:70]}")
    else:
        print(f"  {Fore.RED}-- Sin contenido util{Style.RESET_ALL}")

# ── 4. Test búsqueda menciones via DDG ───────────────────────────────────────
print(f"\n{Fore.YELLOW}[4] Menciones via DuckDuckGo:{Style.RESET_ALL}")
ddg_results = _fetch_ddg("Tamikarnaval", max_results=6)
print(f"  Resultados: {len(ddg_results)}")
for r in ddg_results[:3]:
    nivel = _clasificar(r["text"])
    mark = f"{Fore.RED}[{nivel}]{Style.RESET_ALL}" if nivel else ""
    print(f"  {mark} {r['author']} | {r['text'][:60]}")
    print(f"      {r['url'][:80]}")

# ── 4b. Test Wayback archive ─────────────────────────────────────────────────
print(f"\n{Fore.YELLOW}[4b] Test Wayback Machine (archiva una URL de prueba):{Style.RESET_ALL}")
test_wb_url = "https://twitter.com/DonYuano"
print(f"  Archivando: {test_wb_url}")
archived = _wayback_archive(test_wb_url, timeout=20)
if archived:
    print(f"  {Fore.GREEN}OK Archivado: {archived}{Style.RESET_ALL}")
else:
    print(f"  {Fore.YELLOW}-- No archivado (Wayback puede estar lento){Style.RESET_ALL}")

# ── 5. Test scan_now completo ────────────────────────────────────────────────
print(f"\n{Fore.YELLOW}[5] VictimWatcher.scan_now() — ciclo completo:{Style.RESET_ALL}")
from modules.victim_watcher import VictimWatcher
vw = VictimWatcher("TEST-SCRAPING")
vw.victim = "Tamikarnaval"

alertas = vw.scan_now()
print(f"\n  Alertas nuevas en este ciclo: {len(alertas)}")
for a in alertas:
    print(f"  [{a['nivel']}] {a['autor']}: {a['texto'][:70]}")

# ── Resumen ──────────────────────────────────────────────────────────────────
print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
print(f"{Fore.YELLOW}  RESUMEN{Style.RESET_ALL}")
print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
print(f"  twscrape             : {'OK' if TWSCRAPE_OK else '-- (pip install twscrape)'}")
print(f"  Scrapling Fetcher    : {'OK' if SCRAPLING_OK else '--'}")
print(f"  StealthyFetcher      : {'OK' if SCRAPLING_STEALTH else '--  (scrapling install)'}")
print(f"  Clasificador         : {'PASS' if ok else 'FAIL'}")
print(f"  Nitter mejor inst.   : {best or 'ninguna (xcancel down hoy)'}")
print(f"  DDG menciones        : {len(ddg_results)} resultados")
print(f"  Wayback archive      : {'OK' if archived else 'no disponible'}")
print(f"  Alertas detectadas   : {len(alertas)}")
print(f"\n{Fore.GREEN}  Test completado.{Style.RESET_ALL}\n")
