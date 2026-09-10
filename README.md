# Sala de Control · Dashboard General IA-Crópolis

Dashboard estático de solo lectura del estado real del ecosistema. Generado bajo demanda a partir del disco — no es un servicio corriendo 24/7, no memoriza nada entre corridas.

## Cómo actualizarlo

```
python generar_dashboard.py
```

Escanea `activos-negocios/`, `AGENTES-IA/AGENTES ACTIVOS/` y `conocimiento/obsidian/` en el momento en que se corre, y regenera `index.html` desde cero. Vuelve a correrlo cada vez que quieras una foto actualizada — no hay caché ni base de datos.

## Qué muestra

- **Frentes financieros (F01-F06):** carpeta real, si tiene `INDICE.md`/`README.md` (y su contenido si sí), conteo de archivos `.md`, última fecha de modificación. Si un Frente no tiene índice, lo dice honestamente — nunca inventa una descripción.
- **Agentes de Capa 2:** qué documentos de identidad tiene cada uno (Manual Cognitivo, Skills, Bitácora) y cuántas líneas lleva su Bitácora.
- **Laboratorio Cognitivo:** cuántas notas hay en cada una de las 9 zonas del Vault de Obsidian.

## Despliegue

Local → GitHub → Hostinger, igual que el resto de los artefactos del ecosistema. Alfred sube manualmente a Hostinger tras cada push.

## Filosofía

Sujeto a Kaizen-Ouroboros como cualquier otro artefacto del ecosistema — se mejora con el tiempo, nunca se congela. Si algún día se necesita más detalle por Frente, se agrega al script, no se inventa a mano en el HTML.
