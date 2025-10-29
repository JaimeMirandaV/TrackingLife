# Tracker Personal (Finanzas · Deporte · Salud)

Proyecto mínimo para llevar seguimiento diario y medir progreso vs. objetivos **corto / mediano / largo plazo**.

## Requisitos
- Python 3.10+
- (opcional) entorno virtual

```bash
pip install -r requirements.txt
```

## Ejecutar
```bash
streamlit run streamlit_app.py
```
La app crea una base SQLite `tracker.db` en la carpeta `data/` y aplica el esquema de `schema.sql`.

## Qué puedes registrar
- **Finanzas**: ingresos/gastos (monto positivo = ingreso, negativo = gasto), categoría, método, tags.
- **Deporte**: actividad, minutos, km, calorías, RPE (esfuerzo 1–10).
- **Salud**: peso, horas de sueño, pasos, FC reposo, agua, kcal in/out, notas.

## Objetivos
Edita `config.yaml` o usa la pestaña **Objetivos** en la app. Tipos:
- `acumulativo`: suma (p.ej. km/mes, ahorro).
- `promedio`: media (p.ej. peso medio).
- `habito`: proporción de días con condición (p.ej. "dormir ≥ 7 h").

## Exportar datos
Desde **Dashboard** puedes exportar CSV con tus tablas y métricas.

> Sugerencia de rutina diaria (2–5 min):
> 1) Anota peso/horas de sueño/agua.
> 2) Registra entreno (o descanso).
> 3) Ingresa gastos/ingresos.
> 4) Revisa progreso vs objetivos.
