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
    tarjetas_frentes = []
    for f in frentes:
        if not f["existe"]:
            tarjetas_frentes.append(f"""
            <article class="tarjeta tarjeta-ausente">
              <div class="tarjeta-head"><span class="numero">{esc(f['prefijo'])}</span><span class="chip chip-ausente">No encontrado en disco</span></div>
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
          <div class="tarjeta-head"><span class="numero">{esc(f['prefijo'])}</span><span class="chip {chip}">{chip_txt}</span></div>
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
        filas_agentes.append(f"""
        <tr>
          <td class="fila-label">{esc(a['nombre'])}</td>
          <td>{esc(estado_txt)}</td>
          <td>{esc(fmt_fecha(a['ultima_modificacion']))}</td>
        </tr>""")

    filas_vault = []
    for z in vault_zonas:
        estado = f"{z['archivos_md']} notas" if z["existe"] else "No existe"
        clase = "" if z["existe"] else "fila-ausente"
        filas_vault.append(f"<tr class='{clase}'><td class='fila-label'>{esc(z['zona'])}</td><td>{esc(estado)}</td></tr>")

    return f"""<!DOCTYPE html>
<html lang="es-MX">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sala de Control · IA-Crópolis</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
  --verde: #0F6B4C; --verde-oscuro: #0A4A34; --verde-suave: #E7F3EE;
  --gris-950: #1B1F1D; --gris-700: #4A524D; --gris-500: #7C857F;
  --gris-200: #E4E7E5; --gris-100: #F3F5F4; --blanco: #FFFFFF;
  --amarillo: #B7791F; --amarillo-bg: #FBF2E3;
  --rojo: #9C3B2E; --rojo-bg: #F8EBE9;
  --font: 'Inter', -apple-system, sans-serif; --font-d: 'Manrope', var(--font);
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family: var(--font); color: var(--gris-950); background: var(--blanco); line-height: 1.5; }}
.wrap {{ max-width: 1100px; margin: 0 auto; padding: 0 20px; }}
h1,h2,h3 {{ font-family: var(--font-d); font-weight: 800; margin: 0 0 10px; }}
.header {{ background: linear-gradient(180deg, var(--verde-suave), var(--blanco)); padding: 40px 0 28px; border-bottom: 1px solid var(--gris-200); }}
.header h1 {{ font-size: clamp(24px,5vw,34px); }}
.header p {{ color: var(--gris-700); font-size: 13.5px; margin: 4px 0; }}
.seccion {{ padding: 36px 0; }}
.seccion.alt {{ background: var(--gris-100); }}
.eyebrow {{ font-size: 11.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; color: var(--verde); margin-bottom: 6px; }}
.tarjetas {{ display: grid; grid-template-columns: 1fr; gap: 16px; margin-top: 20px; }}
@media (min-width: 720px) {{ .tarjetas {{ grid-template-columns: repeat(3,1fr); }} }}
.tarjeta {{ background: var(--blanco); border: 1px solid var(--gris-200); border-radius: 14px; padding: 20px; box-shadow: 0 4px 16px rgba(27,31,29,.06); }}
.tarjeta-ausente {{ opacity: .7; border-style: dashed; }}
.tarjeta-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
.numero {{ font-size:13px; font-weight:800; color:var(--verde); background:var(--verde-suave); padding:3px 10px; border-radius:999px; }}
.chip {{ font-size:11px; font-weight:700; padding:3px 9px; border-radius:999px; }}
.chip-ok {{ background: var(--verde-suave); color: var(--verde-oscuro); }}
.chip-alerta {{ background: var(--amarillo-bg); color: var(--amarillo); }}
.chip-ausente {{ background: var(--rojo-bg); color: var(--rojo); }}
.tarjeta h3 {{ font-size: 16px; margin-bottom: 10px; }}
.resumen {{ margin: 0 0 12px; padding-left: 18px; font-size: 13px; color: var(--gris-700); }}
.resumen li {{ margin-bottom: 4px; }}
.nota {{ font-size: 12.5px; color: var(--gris-500); font-style: italic; }}
.tarjeta-footer {{ display:flex; flex-wrap:wrap; gap:8px; padding-top:10px; border-top:1px solid var(--gris-200); margin-top: 8px;}}
.meta {{ font-size: 11.5px; font-weight:600; color: var(--gris-700); background: var(--gris-100); padding:4px 8px; border-radius:6px; }}
table {{ width:100%; border-collapse: collapse; margin-top: 16px; font-size: 13.5px; background: var(--blanco); border-radius: 12px; overflow: hidden; border: 1px solid var(--gris-200); }}
th {{ background: var(--verde-oscuro); color: #fff; text-align:left; padding: 10px 12px; font-size: 12px; text-transform: uppercase; letter-spacing: .03em; }}
td {{ padding: 10px 12px; border-bottom: 1px solid var(--gris-200); color: var(--gris-700); }}
tr:last-child td {{ border-bottom: none; }}
tr:nth-child(even) td {{ background: var(--gris-100); }}
.fila-label {{ font-weight: 700; color: var(--gris-950); }}
.fila-ausente td {{ color: var(--gris-500); font-style: italic; }}
.footer {{ text-align:center; padding: 24px 0; color: var(--gris-500); font-size: 12px; border-top: 1px solid var(--gris-200); }}
</style>
</head>
<body>

<header class="header">
  <div class="wrap">
    <p class="eyebrow">🐝 Sala de Control · IA-Crópolis</p>
    <h1>Dashboard General del Ecosistema</h1>
    <p>Generado bajo demanda — no es un proceso en vivo. Refleja el disco real al momento en que se corrió el generador. Sujeto a Kaizen-Ouroboros: se regenera cuando se pide, no memoriza entre corridas.</p>
    <p><strong>Última generación:</strong> {esc(generado_en)}</p>
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
  <div class="wrap">Generado automáticamente por <code>generar_dashboard.py</code> · IA-Crópolis</div>
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
