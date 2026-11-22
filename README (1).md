# Simulación de cajas – Banco de Colombia

Simulación de eventos discretos de un día de operación (8 horas = 480 min) de un banco con cajas M/M/1 independientes.
Compara cinco configuraciones (3 cajas exclusivas 1+2 y 2+1, 3 cajas mixtas, 4 cajas mixtas y 2+2) en 10 réplicas.

## Requisitos
Python 3.9+ y: `pip install -r requirements.txt`

## Ejecución
```bash
python simulacion_cajas.py
```
Las semillas son fijas, así que los resultados son reproducibles.

## Archivos generados
| Archivo | Contenido |
|---|---|
| `conteo_usuarios.csv` | Usuarios por tipo en cada réplica y promedio |
| `resultados_replicas.csv` | Espera, tiempo en el sistema y espera máxima por configuración y réplica |
| `resumen_configuraciones.csv` | Medias, desviación, IC 95 % y réplicas necesarias |
| `grafica_espera.png`, `grafica_utilizacion.png` | Gráficas de resultados |

## Supuestos
- 70 % retiros / 30 % pagos; las probabilidades de la Tabla 2 se aplican dentro de cada acción.
- Tiempos entre llegadas y de servicio exponenciales según la Tabla 1, por tipo de usuario.
- Cola FIFO por caja; con varias cajas habilitadas, el usuario elige una al azar.
- Desplazamiento despreciable; se deja de recibir usuarios a los 480 min y se atiende a quienes ya llegaron.

## Parámetros editables
`N_REPLICAS`, `DURACION`, `P_RETIRO`, `TIPOS` y `CONFIGS` al inicio de `simulacion_cajas.py`.

## Informe
- Informe: `Informe_simulacion_cajas.docx`
