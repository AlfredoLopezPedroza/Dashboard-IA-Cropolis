# Sala de Control · Dashboard IA-Crópolis

Panel estático de solo lectura del ecosistema. Se genera bajo demanda; no es un servicio corriendo ni guarda nada entre corridas.

## Qué muestra
1. **Organigrama actual** (Constitución IA-Crópolis v7.7, sección VII).
2. **Salud y estado:** solo conteos y fechas verificables (índices de Frentes, bitácoras de agentes, notas del laboratorio, último commit, último respaldo).
3. **Frentes:** nombre y descripción corta. Métricas: N/D hasta que exista el dashboard financiero.

Los activos de los Frentes no se publican ni se leen. Si un dato no se puede verificar, dice N/D.

## Archivos
- `index.html` · versión visual.
- `estado.md` · versión en texto plano, pensada para leerse desde cualquier nodo del Concilio.
- `generar_dashboard.py` · regenera ambos: `python generar_dashboard.py`

Filosofía: Kaizen. Se mejora agregando al script, nunca editando el HTML a mano.
