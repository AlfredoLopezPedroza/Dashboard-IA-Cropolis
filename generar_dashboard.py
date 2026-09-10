#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador del Dashboard General de IA-Crópolis (Sala de Control).

No es un proceso que corre solo — se ejecuta bajo demanda (Alfred o Claude
Code lo piden explícitamente). Escanea el disco real cada vez que corre, no
memoriza nada entre corridas. Si un dato no existe en disco (ej. un Frente
sin INDICE.md), el dashboard lo dice honestamente en vez de inventarlo.

Uso:
    python generar_dashboard.py

Genera: index.html en esta misma carpeta.
"""

import os
import re
import html
from pathlib import Path
from datetime import datetime, timezone

RAIZ = Path(__file__).resolve().parents[3]  # .../IA-CROPOLIS
ACTIVOS = RAIZ / "activos-negocios"
AGENTES = RAIZ / "AGENTES-IA" / "AGENTES ACTIVOS"
VAULT = RAIZ / "conocimiento" / "obsidian"
SALIDA = Path(__file__).resolve().parent / "index.html"

# Frentes conocidos, en el orden en que deben aparecer. El nombre de carpeta
# real se busca por coincidencia de prefijo (F01, F02, ...) para no tronar
# si Capa 0 vuelve a renombrar una carpeta.
FRENTES_ORDEN = ["F01", "F02", "F03", "F04", "F05", "F06"]


def buscar_carpeta_frente(prefijo):
    if not ACTIVOS.exists():
        return None
    for item in ACTIVOS.iterdir():
        if item.is_dir() and item.name.upper().startswith(prefijo):
            return item
    return None


def contar_archivos(carpeta, extension=None):
    if not carpeta or not carpeta.exists():
        return 0
    total = 0
    for _, _, archivos in os.walk(carpeta):
        for a in archivos:
            if extension is None or a.lower().endswith(extension):
                total += 1
    return total


def fecha_modificacion_mas_reciente(carpeta):
    if not carpeta or not carpeta.exists():
        return None
    mas_reciente = None
    for raiz, _, archivos in os.walk(carpeta):
        for a in archivos:
            ruta = Path(raiz) / a
            try:
                m = datetime.fromtimestamp(ruta.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            if mas_reciente is None or m > mas_reciente:
                mas_reciente = m
    return mas_reciente


def leer_indice(carpeta):
    """Busca INDICE.md o README.md en el nivel superior del Frente.
    Si no existe, regresa None honestamente — no se inventa descripción."""
    if not carpeta:
        return None
    for nombre in ("INDICE.md", "README.md"):
        candidato = carpeta / nombre
        if candidato.exists():
            try:
                texto = candidato.read_text(encoding="utf-8", errors="ignore")
                return nombre, texto
            except OSError:
                return None
    return None


def extraer_lineas_clave(texto, maximo=6):
    """Toma las primeras líneas no vacías y no-encabezado-de-markdown puro
    para dar un resumen corto, sin inventar nada que no esté ya escrito."""
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    resumen = []
    for l in lineas:
        limpio = re.sub(r"^#+\s*", "", l)
        limpio = re.sub(r"[*_`]", "", limpio)
        if limpio:
            resumen.append(limpio)
        if len(resumen) >= maximo:
            break
    return resumen


def datos_frente(prefijo):
    carpeta = buscar_carpeta_frente(prefijo)
    if not carpeta:
        return {
            "prefijo": prefijo,
            "existe": False,
        }
    indice = leer_indice(carpeta)
    archivos_md = contar_archivos(carpeta, ".md")
    ultima_mod = fecha_modificacion_mas_reciente(carpeta)
    return {
        "prefijo": prefijo,
        "existe": True,
        "nombre_carpeta": carpeta.name,
        "tiene_indice": indice is not None,
        "fuente_indice": indice[0] if indice else None,
        "resumen": extraer_lineas_clave(indice[1]) if indice else [],
        "archivos_md": archivos_md,
        "ultima_modificacion": ultima_mod,
    }


def datos_agente(carpeta):
    bitacora = carpeta / "BITACORA.md"
    tiene_bitacora = bitacora.exists()
    ultima_mod = None
    lineas_bitacora = 0
    if tiene_bitacora:
        try:
            contenido = bitacora.read_text(encoding="utf-8", errors="ignore")
            lineas_bitacora = len(contenido.splitlines())
            ultima_mod = datetime.fromtimestamp(bitacora.stat().st_mtime, tz=timezone.utc)
        except OSError:
            pass
    tiene_manual = (carpeta / "MANUAL-COGNITIVO.md").exists()
    tiene_skills = (carpeta / "SKILLS.md").exists()
    return {
        "nombre": carpeta.name,
        "tiene_bitacora": tiene_bitacora,
        "lineas_bitacora": lineas_bitacora,
        "ultima_modificacion": ultima_mod,
        "tiene_manual_cognitivo": tiene_manual,
        "tiene_skills": tiene_skills,
    }


ZONAS_VAULT = [
    "00_CORE", "01_FUENTES", "02_IDEAS_ATOMICAS", "03_MOLECULAS_COGNITIVAS",
    "04_OPORTUNIDADES", "05_EXPERIMENTOS", "06_APRENDIZAJES",
    "07_CONOCIMIENTO_VALIDADO", "08_COMPETENCIAS", "09_FRENTES_Y_ACTIVOS",
    "99_ARCHIVO",
]


def datos_vault():
    zonas = []
    for z in ZONAS_VAULT:
        carpeta = VAULT / z
        zonas.append({
            "zona": z,
            "existe": carpeta.exists(),
            "archivos_md": contar_archivos(carpeta, ".md") if carpeta.exists() else 0,
        })
    return zonas


def fmt_fecha(dt):
    if dt is None:
        return "sin archivos"
    return dt.strftime("%Y-%m-%d")


def esc(s):
    return html.escape(str(s), quote=True)


def construir_html(frentes, agentes, vault_zonas, generado_en):
    frentes_ok = sum(1 for f in frentes if f["existe"])
    frentes_con_indice = sum(1 for f in frentes if f["existe"] and f["tiene_indice"])
    agentes_con_bitacora = sum(1 for a in agentes if a["tiene_bitacora"])
    vault_total_notas = sum(z["archivos_md"] for z in vault_zonas)

    tarjetas_frentes = []
    for f in frentes:
        if not f["existe"]:
            tarjetas_frentes.append(f"""
            <article class="tarjeta tarjeta-ausente">
              <div class="tarjeta-head"><span class="numero">{esc(f['prefijo'])}</span><span class="chip chip-ausente"><i class="chip-dot"></i>No encontrado en disco</span></div>
              <p class="nota">No hay ninguna carpeta que empiece con "{esc(f['prefijo'])}" en <code>activos-negocios/</code> ahora mismo.</p>
            </article>""")
            continue

        chip = ("chip-ok" if f["tiene_indice"] else "chip-alerta")
        chip_txt = f"Con {esc(f['fuente_indice'])}" if f["tiene_indice"] else "Sin INDICE.md/README.md — revisar manualmente"
        resumen_html = ""
        if f["resumen"]:
            items = "".join(f"<li>{esc(l)}</li>" for l in f["resumen"])
            resumen_html = f"<ul class='resumen'>{items}</ul>"
        else:
            resumen_html = "<p class='nota'>Sin descripción legible en disco — no se inventó ninguna.</p>"

        tarjetas_frentes.append(f"""
        <article class="tarjeta">
          <div class="tarjeta-head"><span class="numero">{esc(f['prefijo'])}</span><span class="chip {chip}"><i class="chip-dot"></i>{chip_txt}</span></div>
          <h3>{esc(f['nombre_carpeta'])}</h3>
          {resumen_html}
          <div class="tarjeta-footer">
            <span class="meta">📄 {f['archivos_md']} archivos .md</span>
            <span class="meta">🕒 Última actividad: {esc(fmt_fecha(f['ultima_modificacion']))}</span>
          </div>
        </article>""")

    filas_agentes = []
    for a in agentes:
        estado_memoria = []
        if a["tiene_manual_cognitivo"]:
            estado_memoria.append("Manual Cognitivo")
        if a["tiene_skills"]:
            estado_memoria.append("Skills")
        if a["tiene_bitacora"]:
            estado_memoria.append(f"Bitácora ({a['lineas_bitacora']} líneas)")
        estado_txt = " · ".join(estado_memoria) if estado_memoria else "Sin documentos de identidad detectados"
        dot = "dot-on" if a["tiene_bitacora"] else "dot-off"
        filas_agentes.append(f"""
        <tr>
          <td class="fila-label"><i class="row-dot {dot}"></i>{esc(a['nombre'])}</td>
          <td>{esc(estado_txt)}</td>
          <td>{esc(fmt_fecha(a['ultima_modificacion']))}</td>
        </tr>""")

    filas_vault = []
    for z in vault_zonas:
        estado = f"{z['archivos_md']} notas" if z["existe"] else "No existe"
        clase = "" if z["existe"] else "fila-ausente"
        dot = "dot-on" if z["existe"] else "dot-off"
        filas_vault.append(f"<tr class='{clase}'><td class='fila-label'><i class='row-dot {dot}'></i>{esc(z['zona'])}</td><td>{esc(estado)}</td></tr>")

    return f"""<!DOCTYPE html>
<html lang="es-MX">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sala de Control · IA-Crópolis</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;700;900&family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
:root {{
  --bg-deep:#060a14; --bg-mid:#0a1225; --bg-card:rgba(8,16,36,0.7);
  --border:rgba(0,180,255,0.14); --border-hi:rgba(0,220,255,0.4);
  --cyan:#00e0ff; --cyan2:#0af; --gold:#ffd866;
  --green:#00ff88; --red:#ff4455; --orange:#ffaa00;
  --text:#c8d6e5; --text-dim:#5a6d80; --text-bright:#eef4fa;
  --font-ui:'Rajdhani',sans-serif; --font-brand:'Orbitron',sans-serif; --font-mono:'Share Tech Mono',monospace;
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family: var(--font-ui); font-size:16px; color: var(--text); background: var(--bg-deep); line-height: 1.6;
  background-image:
    linear-gradient(rgba(0,140,220,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,140,220,0.05) 1px, transparent 1px);
  background-size: 42px 42px;
}}
.wrap {{ max-width: 1100px; margin: 0 auto; padding: 0 20px; }}
h1,h2,h3 {{ font-family: var(--font-brand); font-weight: 700; margin: 0 0 10px; color: var(--text-bright); }}
code {{ font-family: var(--font-mono); }}
.header {{ background: linear-gradient(180deg, rgba(0,140,220,.08), transparent); padding: 44px 0 30px; border-bottom: 1px solid var(--border); position:relative; overflow:hidden; }}
.header::after {{ content:''; position:absolute; bottom:-1px; left:0; width:100%; height:1px; background:linear-gradient(90deg,transparent,var(--cyan),var(--gold),var(--cyan),transparent); }}
.header h1 {{ font-size: clamp(22px,4.5vw,32px); letter-spacing: 1px; background:linear-gradient(135deg,var(--gold),var(--cyan)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
.header p {{ color: var(--text-dim); font-size: 13.5px; margin: 4px 0; max-width: 760px; }}
.header p strong {{ color: var(--text); }}
.eyebrow {{ font-family: var(--font-mono); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .18em; color: var(--cyan); margin-bottom: 8px; }}
.resumen-global {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:18px; }}
.pill {{ font-family: var(--font-mono); font-size:11.5px; padding:6px 12px; border:1px solid var(--border); border-radius:999px; background:var(--bg-card); color:var(--text); }}
.pill b {{ color: var(--cyan); }}
.seccion {{ padding: 40px 0; }}
.seccion.alt {{ background: linear-gradient(180deg, rgba(0,60,110,.05), transparent); border-top:1px solid var(--border); border-bottom:1px solid var(--border); }}
.tarjetas {{ display: grid; grid-template-columns: 1fr; gap: 16px; margin-top: 20px; }}
@media (min-width: 720px) {{ .tarjetas {{ grid-template-columns: repeat(3,1fr); }} }}
.tarjeta {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; backdrop-filter: blur(6px); position:relative; overflow:hidden; transition: border-color .25s, transform .25s; }}
.tarjeta::before {{ content:''; position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,var(--cyan2),transparent); opacity:.6; }}
.tarjeta:hover {{ border-color: var(--border-hi); transform: translateY(-2px); }}
.tarjeta-ausente {{ opacity: .55; border-style: dashed; }}
.tarjeta-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; gap:8px; flex-wrap:wrap; }}
.numero {{ font-family: var(--font-brand); font-size:12px; font-weight:700; letter-spacing:1px; color:var(--bg-deep); background:var(--cyan); padding:3px 10px; border-radius:6px; }}
.chip {{ display:inline-flex; align-items:center; gap:6px; font-family:var(--font-mono); font-size:10.5px; font-weight:600; padding:3px 10px; border-radius:999px; border:1px solid var(--border); }}
.chip-dot {{ width:6px; height:6px; border-radius:50%; display:inline-block; }}
.chip-ok {{ color: var(--green); }} .chip-ok .chip-dot {{ background:var(--green); box-shadow:0 0 6px var(--green); }}
.chip-alerta {{ color: var(--orange); }} .chip-alerta .chip-dot {{ background:var(--orange); box-shadow:0 0 6px var(--orange); }}
.chip-ausente {{ color: var(--red); }} .chip-ausente .chip-dot {{ background:var(--red); box-shadow:0 0 6px var(--red); }}
.tarjeta h3 {{ font-family: var(--font-ui); font-size: 17px; font-weight:700; margin-bottom: 10px; color: var(--text-bright); }}
.resumen {{ margin: 0 0 12px; padding-left: 18px; font-size: 13.5px; color: var(--text-dim); }}
.resumen li {{ margin-bottom: 4px; }}
.nota {{ font-size: 12.5px; color: var(--text-dim); font-style: italic; }}
.tarjeta-footer {{ display:flex; flex-wrap:wrap; gap:8px; padding-top:12px; border-top:1px solid var(--border); margin-top: 10px; }}
.meta {{ font-family: var(--font-mono); font-size: 11px; font-weight:600; color: var(--text-dim); background: rgba(255,255,255,.03); padding:4px 8px; border-radius:6px; }}
table {{ width:100%; border-collapse: collapse; margin-top: 18px; font-size: 13.5px; background: var(--bg-card); border-radius: 12px; overflow: hidden; border: 1px solid var(--border); }}
th {{ background: rgba(0,180,255,.08); color: var(--cyan); text-align:left; padding: 11px 14px; font-family: var(--font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: .06em; border-bottom:1px solid var(--border); }}
td {{ padding: 11px 14px; border-bottom: 1px solid rgba(255,255,255,.04); color: var(--text-dim); }}
tr:last-child td {{ border-bottom: none; }}
tr:hover td {{ background: rgba(0,180,255,.04); color: var(--text); }}
.fila-label {{ font-weight: 700; color: var(--text-bright); display:flex; align-items:center; gap:8px; }}
.row-dot {{ width:7px; height:7px; border-radius:50%; display:inline-block; flex-shrink:0; }}
.dot-on {{ background: var(--green); box-shadow:0 0 5px var(--green); }}
.dot-off {{ background: var(--text-dim); }}
.fila-ausente td {{ color: var(--text-dim); font-style: italic; opacity:.6; }}
.footer {{ text-align:center; padding: 26px 0; color: var(--text-dim); font-family: var(--font-mono); font-size: 11px; border-top: 1px solid var(--border); }}
</style>
</head>
<body>

<header class="header">
  <div class="wrap">
    <p class="eyebrow">◈ Sala de Control · IA-Crópolis</p>
    <h1>Dashboard General del Ecosistema</h1>
    <p>Generado bajo demanda a partir del disco real — no es un proceso en vivo ni memoriza nada entre corridas. Sujeto a Kaizen-Ouroboros: se regenera cuando se pide.</p>
    <p><strong>Última generación:</strong> {esc(generado_en)}</p>
    <div class="resumen-global">
      <span class="pill">Frentes en disco: <b>{frentes_ok}/{len(frentes)}</b></span>
      <span class="pill">Con índice real: <b>{frentes_con_indice}/{frentes_ok}</b></span>
      <span class="pill">Agentes con bitácora: <b>{agentes_con_bitacora}/{len(agentes)}</b></span>
      <span class="pill">Notas en el Vault: <b>{vault_total_notas}</b></span>
    </div>
  </div>
</header>

<main>
  <section class="seccion">
    <div class="wrap">
      <p class="eyebrow">Frentes financieros</p>
      <h2>Los 6 Frentes de activos-negocios/</h2>
      <div class="tarjetas">
        {"".join(tarjetas_frentes)}
      </div>
    </div>
  </section>

  <section class="seccion alt">
    <div class="wrap">
      <p class="eyebrow">Capa 2</p>
      <h2>Agentes ejecutores — estado de memoria</h2>
      <table>
        <thead><tr><th>Agente</th><th>Documentos de identidad detectados</th><th>Última actividad</th></tr></thead>
        <tbody>{"".join(filas_agentes)}</tbody>
      </table>
    </div>
  </section>

  <section class="seccion">
    <div class="wrap">
      <p class="eyebrow">Laboratorio Cognitivo</p>
      <h2>Vault de Obsidian — notas por zona</h2>
      <table>
        <thead><tr><th>Zona</th><th>Estado</th></tr></thead>
        <tbody>{"".join(filas_vault)}</tbody>
      </table>
    </div>
  </section>
</main>

<footer class="footer">
  <div class="wrap">GENERADO POR generar_dashboard.py · IA-CRÓPOLIS · DATOS REALES, SIN INVENCIÓN</div>
</footer>

</body>
</html>
"""


def main():
    frentes = [datos_frente(p) for p in FRENTES_ORDEN]
    agentes = []
    if AGENTES.exists():
        for carpeta in sorted(AGENTES.iterdir()):
            if carpeta.is_dir():
                agentes.append(datos_agente(carpeta))
    vault_zonas = datos_vault()
    generado_en = datetime.now().strftime("%Y-%m-%d %H:%M")

    salida_html = construir_html(frentes, agentes, vault_zonas, generado_en)
    SALIDA.write_text(salida_html, encoding="utf-8")
    print(f"Dashboard generado en: {SALIDA}")
    print(f"Frentes detectados: {sum(1 for f in frentes if f['existe'])} / {len(FRENTES_ORDEN)}")
    print(f"Agentes detectados: {len(agentes)}")


if __name__ == "__main__":
    main()
