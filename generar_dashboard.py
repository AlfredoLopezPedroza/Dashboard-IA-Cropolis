#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sala de Control · Dashboard general IA-Crópolis (v3, 25-sep-2026).

Versión PÚBLICA-SEGURA: no lee el contenido de los Frentes. Muestra solo:
  1) Organigrama actual (leído EN VIVO de la Constitución, sección VII —
     ya no es una lista escrita a mano; Fase 1 de la Reconstrucción del
     Ecosistema, mismo principio que documentacion/core/generar_mapa.py)
  2) Salud / estado actual (solo conteos y fechas verificables)
  3) Frentes (nombre y descripción de FRENTES-REFERENCIA.md; métricas N/D)

Regla de No Invención: si un dato no se puede verificar, dice N/D.
Uso:  python generar_dashboard.py   -> regenera index.html y estado.md
"""
import html
import re
import subprocess
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]  # .../IA-CROPOLIS
ACTIVOS = RAIZ / "activos-negocios"
AGENTES = RAIZ / "AGENTES-IA" / "AGENTES ACTIVOS"
VAULT = RAIZ / "conocimiento" / "obsidian"
CONSTITUCION = RAIZ / "documentacion" / "core" / "CONSTITUCIÓN_IA-CRÓPOLIS_v7.7.md"
REFERENCIA = RAIZ / "documentacion" / "core" / "FRENTES-REFERENCIA.md"
RESPALDO_MARCA = Path("D:/RESPALDOS-IA-CROPOLIS/IA-CROPOLIS-ACTUAL/ULTIMO-RESPALDO.txt")
SALIDA_HTML = AQUI / "index.html"
SALIDA_MD = AQUI / "estado.md"

# Encabezados reales de la seccion VII de la Constitucion, en orden.
# Si algun dia cambia el texto de un encabezado en la Constitucion, este
# parser deja de encontrar esa capa -- se nota de inmediato (lista vacia
# en el dashboard), nunca falla en silencio con datos viejos.
_CAPAS = [
    ("Capa 1 · Concilio", "### 🏛️ CAPA 1"),
    ("Capa 1.5 · Fuerza de Asalto Táctico", "### 🪓 CAPA 1.5"),
    ("Capa 2 · Brazos Ejecutores (activos)", "### ⚙️ CAPA 2"),
    ("Capa 3 · Reserva Estratégica", "### 🔘 CAPA 3"),
]
_FILA = re.compile(r"^\|\s*\*\*(.+?)\*\*[^|]*\|(.+)\|(.+)\|\s*$")


def _valido(col: str) -> bool:
    col = col.strip()
    return bool(col) and col not in ("—", "-", "–") and not col.startswith("---")


def leer_organigrama():
    """Lee la seccion VII de la Constitucion en vivo -- Capa 0 se deja
    fija (nunca esta en una tabla), las demas capas se extraen tal cual
    esten hoy. Ningun nombre/rol se escribe aqui a mano."""
    if not CONSTITUCION.exists():
        return [("Capa 0 · Autoridad", [("Alfred", "Autoridad final")])]
    texto = CONSTITUCION.read_text(encoding="utf-8")
    marcadores = [m for _, m in _CAPAS] + ["## VII-B."]
    organigrama = [("Capa 0 · Autoridad", [("Alfred", "Autoridad final")])]
    for i, (etiqueta, marcador) in enumerate(_CAPAS):
        ini = texto.find(marcador)
        if ini == -1:
            organigrama.append((etiqueta, []))
            continue
        fin = len(texto)
        for m2 in marcadores[i + 1:]:
            pos = texto.find(m2, ini + 1)
            if pos != -1:
                fin = min(fin, pos)
        bloque = texto[ini:fin]
        nodos = []
        if etiqueta.startswith("Capa 3"):
            # Capa 3 es una lista plana "A · B · C", no una tabla.
            for linea in bloque.splitlines():
                linea = linea.strip()
                if linea.startswith("###") or not linea or linea.startswith(("**", ">", "#")):
                    continue
                nodos = [(n.strip(), "") for n in linea.split("·") if n.strip()]
                break
        else:
            # La tabla de Capa 2 tiene otra forma de columnas: Agente |
            # Modelo/Plataforma | Especialidad -- la col2 es el modelo,
            # no un rol. Las demas tablas van Nodo | Rol | Plataforma,
            # donde la col2 SI es el rol. Cada tabla se lee segun su
            # propia forma real, no se le impone una ajena.
            es_capa2 = etiqueta.startswith("Capa 2")
            for linea in bloque.splitlines():
                m3 = _FILA.match(linea.strip())
                if not m3:
                    continue
                nombre, col2, col3 = m3.group(1).strip(), m3.group(2).strip(), m3.group(3).strip()
                if nombre.lower() in ("nodo", "agente"):
                    continue
                rol = col3 if es_capa2 else " · ".join(p for p in (col2, col3) if _valido(p))
                nodos.append((nombre, rol))
        organigrama.append((etiqueta, nodos))
    return organigrama


def esc(s):
    return html.escape(str(s), quote=True)


def leer_frentes():
    """Filas F0X de FRENTES-REFERENCIA.md: (codigo, nombre, descripcion)."""
    frentes = []
    if not REFERENCIA.exists():
        return frentes
    for linea in REFERENCIA.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(F0\d)\s+([^|]+?)\s*\|\s*([^|]+?)\s*\|", linea)
        if m:
            frentes.append((m.group(1), m.group(2), m.group(3)))
    return frentes


def contar_frentes_con_indice():
    total = con = 0
    if ACTIVOS.exists():
        for d in sorted(ACTIVOS.iterdir()):
            if d.is_dir() and re.match(r"F0\d", d.name):
                total += 1
                if (d / "INDICE.md").exists():
                    con += 1
    return con, total


def contar_agentes_con_bitacora():
    total = con = 0
    if AGENTES.exists():
        for d in sorted(AGENTES.iterdir()):
            if d.is_dir():
                total += 1
                if (d / "BITACORA.md").exists():
                    con += 1
    return con, total


def contar_notas_vault():
    if not VAULT.exists():
        return None
    return sum(1 for p in VAULT.rglob("*.md") if ".obsidian" not in p.parts)


def ultimo_commit_cerebro():
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%cs"], cwd=RAIZ,
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return "N/D"


def ultimo_respaldo():
    try:
        if RESPALDO_MARCA.exists():
            return RESPALDO_MARCA.read_text(encoding="utf-8-sig").strip().splitlines()[0]
    except Exception:
        pass
    return "N/D"


def salud():
    i_con, i_tot = contar_frentes_con_indice()
    a_con, a_tot = contar_agentes_con_bitacora()
    notas = contar_notas_vault()
    commit, respaldo = ultimo_commit_cerebro(), ultimo_respaldo().split(" (")[0]
    return [
        ("Frentes con índice documentado", f"{i_con} / {i_tot}", i_tot > 0 and i_con == i_tot),
        ("Agentes activos con bitácora", f"{a_con} / {a_tot}", a_tot > 0 and a_con == a_tot),
        ("Notas en el Laboratorio Cognitivo", "N/D" if notas is None else str(notas), notas is not None),
        ("Último commit del cerebro", commit, commit != "N/D"),
        ("Último respaldo verificado", respaldo, respaldo != "N/D"),
    ]


def _titulo_corto(rol: str) -> str:
    """La tarjeta es un chip compacto, no un párrafo -- solo el título
    corto. El detalle completo (fechas, contexto, notas) vive en
    estado.md, que sí tiene espacio para leerse como texto."""
    corto = rol.split(" (")[0].split(" · ")[0]
    return corto.replace("**", "").strip()


def construir_html(organigrama, frentes, checks, generado):
    org = ""
    for capa, nodos in organigrama:
        chips = "".join(
            f'<div class="nodo"><b>{esc(n)}</b>'
            + (f"<span>{esc(_titulo_corto(r))}</span>" if r else "") + "</div>"
            for n, r in nodos)
        org += f'<div class="capa"><h3>{esc(capa)}</h3><div class="nodos">{chips}</div></div>'
    sal = "".join(
        f'<div class="card {"ok" if ok else "nd"}"><span class="k">{esc(k)}</span>'
        f'<span class="v">{esc(v)}</span></div>' for k, v, ok in checks)
    fr = "".join(
        f'<div class="card frente"><span class="cod">{esc(c)}</span><b>{esc(n)}</b>'
        f'<p>{esc(d)}</p><span class="met">Métricas: N/D · pendiente del dashboard financiero</span></div>'
        for c, n, d in frentes)
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sala de Control · IA-Crópolis</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Rajdhani:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#070b14;--panel:#0e1626;--linea:#1c2b47;--txt:#dbe7ff;--mut:#8aa0c8;--cy:#38d4ff;--ok:#3ddc97;--nd:#f0b429}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--txt);font:17px/1.5 Rajdhani,system-ui,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}
h1{{font:700 26px Orbitron,sans-serif;color:var(--cy);margin:0 0 4px;letter-spacing:.04em}}
h2{{font:500 18px Orbitron,sans-serif;color:var(--cy);margin:34px 0 12px;letter-spacing:.05em}}
h3{{margin:0 0 8px;font-size:15px;color:var(--mut);font-weight:600;text-transform:uppercase;letter-spacing:.08em}}
.sub{{color:var(--mut);margin:0}}
.capa{{background:var(--panel);border:1px solid var(--linea);border-radius:12px;padding:14px;margin-bottom:10px}}
.nodos{{display:flex;flex-wrap:wrap;gap:8px}}
.nodo{{border:1px solid var(--linea);border-radius:8px;padding:6px 10px;display:flex;flex-direction:column;min-width:130px}}
.nodo b{{font-weight:600}}.nodo span{{color:var(--mut);font-size:14px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px}}
.card{{background:var(--panel);border:1px solid var(--linea);border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:4px}}
.card.ok{{border-left:4px solid var(--ok)}}.card.nd{{border-left:4px solid var(--nd)}}
.k{{color:var(--mut);font-size:14px}}.v{{font:700 22px Orbitron,sans-serif}}
.frente .cod{{color:var(--cy);font:700 13px Orbitron,sans-serif}}.frente p{{margin:2px 0 6px;color:var(--txt)}}
.met{{color:var(--nd);font-size:14px}}
footer{{margin-top:36px;color:var(--mut);font-size:14px;border-top:1px solid var(--linea);padding-top:12px}}
</style></head><body><main>
<h1>SALA DE CONTROL · IA-CRÓPOLIS</h1>
<p class="sub">Foto generada: {esc(generado)} · solo lectura</p>
<h2>1 · ORGANIGRAMA ACTUAL</h2>{org}
<h2>2 · SALUD Y ESTADO</h2><div class="grid">{sal}</div>
<h2>3 · FRENTES</h2><div class="grid">{fr}</div>
<footer>Fuente del organigrama: Constitución IA-Crópolis v7.7 (sección VII). Los activos de los Frentes no se publican; aquí solo aparece su existencia. N/D = dato no disponible o aún sin fuente verificable.</footer>
</main></body></html>"""


def construir_md(organigrama, frentes, checks, generado):
    L = ["# ESTADO COMPARTIDO · IA-Crópolis", "", f"Generado: {generado}",
         "Fuente: Constitución v7.7 (organigrama, leído en vivo) y conteos verificables del disco local.", "",
         "## 1. ORGANIGRAMA ACTUAL", ""]
    for capa, nodos in organigrama:
        L.append(f"**{capa}**")
        for n, r in nodos:
            L.append(f"- {n}" + (f": {r}" if r else ""))
        L.append("")
    L += ["## 2. SALUD Y ESTADO", ""]
    for k, v, ok in checks:
        L.append(f"- {k}: {v}")
    L += ["", "## 3. FRENTES", "", "Métricas reales: N/D (pendiente del dashboard financiero).", ""]
    for c, n, d in frentes:
        L.append(f"- {c} {n}: {d}")
    L.append("")
    return "\n".join(L)


def main():
    generado = datetime.now().strftime("%Y-%m-%d %H:%M")
    organigrama = leer_organigrama()
    frentes, checks = leer_frentes(), salud()
    SALIDA_HTML.write_text(construir_html(organigrama, frentes, checks, generado), encoding="utf-8")
    SALIDA_MD.write_text(construir_md(organigrama, frentes, checks, generado), encoding="utf-8")
    print(f"index.html y estado.md generados ({len(frentes)} frentes, {len(checks)} indicadores, "
          f"{sum(len(n) for _, n in organigrama)} nodos en el organigrama)")


if __name__ == "__main__":
    main()
