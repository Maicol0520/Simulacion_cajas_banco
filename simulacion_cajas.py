"""
Simulación de cajas - Banco de Colombia
Modelo de eventos discretos: cada caja es una cola M/M/1 independiente (FIFO).
Un día = 480 minutos. Se ejecutan N_REPLICAS réplicas independientes.

Uso:  python simulacion_cajas.py
Salidas: resultados_replicas.csv, resumen_configuraciones.csv, conteo_usuarios.csv,
         grafica_espera.png, grafica_utilizacion.png
"""
import numpy as np, pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------- Parámetros (Tablas 1 y 2 del enunciado) ----------------
DURACION = 480.0          # minutos de operación (8 horas)
N_REPLICAS = 10           # mínimo exigido
P_RETIRO = 0.70           # 70 % retiros, 30 % pagos
# (acción, tipo, prob. dentro de la acción, media servicio, media entre llegadas)
TIPOS = [
    ("Retiro", "Rápido",    0.23, 1, 1), ("Retiro", "Normal",   0.40, 2, 2),
    ("Retiro", "Lento",     0.17, 3, 3), ("Retiro", "Muy lento", 0.20, 4, 3),
    ("Pago",   "Rápido",    0.10, 3, 1), ("Pago",   "Normal",   0.20, 3, 2),
    ("Pago",   "Lento",     0.30, 5, 3), ("Pago",   "Muy lento", 0.40, 7, 4),
]
# Probabilidad conjunta = P(acción) * P(tipo | acción)
PROB = np.array([(P_RETIRO if t[0] == "Retiro" else 1 - P_RETIRO) * t[2] for t in TIPOS])
SERV = np.array([t[3] for t in TIPOS], float)
LLEG = np.array([t[4] for t in TIPOS], float)
NOMBRES = [f"{t[0]} {t[1]}" for t in TIPOS]

# Configuraciones: lista de cajas, cada una con el conjunto de acciones que atiende
CONFIGS = {
    "A: 1 retiros + 2 pagos": [{"Retiro"}, {"Pago"}, {"Pago"}],
    "B: 2 retiros + 1 pagos": [{"Retiro"}, {"Retiro"}, {"Pago"}],
    "C: 3 mixtas":            [{"Retiro", "Pago"}] * 3,
    "D: 4 mixtas":            [{"Retiro", "Pago"}] * 4,
    "E: 2 retiros + 2 pagos": [{"Retiro"}, {"Retiro"}, {"Pago"}, {"Pago"}],
}

def generar_dia(rng):
    """Genera las llegadas de un día: (instante, tipo, duración del servicio)."""
    t, llegadas = 0.0, []
    while True:
        k = rng.choice(8, p=PROB)            # tipo de usuario
        t += rng.exponential(LLEG[k])        # tiempo entre llegadas (exponencial)
        if t > DURACION:                     # el banco deja de recibir usuarios
            return llegadas
        llegadas.append((t, k, rng.exponential(SERV[k])))

def simular(llegadas, config, rng):
    """Asigna cada usuario a una caja habilitada al azar (cajas independientes)
    y calcula su espera con la recursión de Lindley: inicio = max(llegada, libre)."""
    libre = [0.0] * len(config)
    reg = [[] for _ in config]
    for t, k, s in llegadas:
        accion = "Retiro" if k < 4 else "Pago"
        opciones = [i for i, c in enumerate(config) if accion in c]
        i = opciones[rng.integers(len(opciones))]
        inicio = max(t, libre[i])
        libre[i] = inicio + s
        reg[i].append((k, inicio - t, s, inicio + s - t))   # tipo, espera, servicio, total
    return reg

def main():
    dias = [generar_dia(np.random.default_rng(1000 + r)) for r in range(N_REPLICAS)]

    # --- Conteo de usuarios por tipo y réplica (puntos 2 y 3) ---
    conteo = pd.DataFrame(0, index=range(1, N_REPLICAS + 1), columns=NOMBRES)
    for r, d in enumerate(dias, 1):
        for _, k, _ in d:
            conteo.loc[r, NOMBRES[k]] += 1
    conteo["Total"] = conteo.sum(axis=1)
    conteo.loc["Promedio"] = conteo.mean()
    conteo.round(1).to_csv("conteo_usuarios.csv")
    print(conteo.round(1))

    # --- Simulación de cada configuración ---
    filas, cajas = [], []
    for nombre, cfg in CONFIGS.items():
        for r, d in enumerate(dias, 1):
            reg = simular(d, cfg, np.random.default_rng(5000 + r))
            todos = np.array([x for c in reg for x in c])
            esp_ret = todos[todos[:, 0] < 4, 1].mean()
            esp_pag = todos[todos[:, 0] >= 4, 1].mean()
            filas.append(dict(config=nombre, replica=r, espera=todos[:, 1].mean(),
                              sistema=todos[:, 3].mean(), espera_max=todos[:, 1].max(),
                              espera_retiros=esp_ret, espera_pagos=esp_pag))
            for i, c in enumerate(reg):
                a = np.array(c)
                cajas.append(dict(config=nombre, replica=r, caja=i + 1, usuarios=len(a),
                                  servicio=a[:, 2].mean(), espera=a[:, 1].mean(),
                                  sistema=a[:, 3].mean(), utilizacion=a[:, 2].sum() / DURACION))
    df, dc = pd.DataFrame(filas), pd.DataFrame(cajas)
    df.to_csv("resultados_replicas.csv", index=False)

    # --- Resumen con IC 95 % y réplicas necesarias ---
    res = []
    for nombre, g in df.groupby("config"):
        m, s = g.espera.mean(), g.espera.std(ddof=1)
        t = stats.t.ppf(0.975, N_REPLICAS - 1)
        hw = t * s / np.sqrt(N_REPLICAS)
        n_req = int(np.ceil((1.96 * s / 0.25) ** 2))   # error absoluto de 0,25 min
        res.append(dict(config=nombre, espera=m, desv=s, ic95_mitad=hw,
                        sistema=g.sistema.mean(), espera_retiros=g.espera_retiros.mean(),
                        espera_pagos=g.espera_pagos.mean(), espera_max=g.espera_max.mean(),
                        replicas_para_error_0_25min=n_req))
    resumen = pd.DataFrame(res).round(2)
    resumen.to_csv("resumen_configuraciones.csv", index=False)
    print(resumen.to_string(index=False))

    # --- Cajas (configuración C): menor y mayor tiempo promedio de atención ---
    c3 = dc[dc.config == "C: 3 mixtas"].groupby("caja")[["usuarios", "servicio", "espera",
                                                         "sistema", "utilizacion"]].mean().round(2)
    print(c3)

    # --- Gráficas ---
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(resumen.config, resumen.espera, yerr=resumen.ic95_mitad, capsize=4, color="#2a9d8f")
    ax.set_ylabel("Espera promedio en cola (min)"); ax.set_title("Espera promedio por configuración (IC 95 %)")
    plt.xticks(rotation=20, ha="right"); plt.tight_layout(); plt.savefig("grafica_espera.png", dpi=150)

    # Utilización por caja: barras agrupadas por configuración
    fig, ax = plt.subplots(figsize=(8, 4.5))
    u = dc.groupby(["config", "caja"]).utilizacion.mean().reset_index()
    cfgs = list(CONFIGS)
    for j, nombre in enumerate(cfgs):
        g = u[u.config == nombre]
        x = np.arange(len(g)) * 0.0 + j + (g.caja.values - (len(g) + 1) / 2) * 0.17
        ax.bar(x, g.utilizacion * 100, width=0.16, color="#2a9d8f", edgecolor="white")
        for xi, v in zip(x, g.utilizacion * 100):
            ax.text(xi, v + 1, f"{v:.0f}", ha="center", fontsize=8)
    ax.set_xticks(range(len(cfgs))); ax.set_xticklabels(cfgs, rotation=20, ha="right")
    ax.set_ylabel("Utilización por caja (%)"); ax.set_ylim(0, 80)
    ax.set_title("Utilización promedio de cada caja (una barra por caja)")
    plt.tight_layout(); plt.savefig("grafica_utilizacion.png", dpi=150)

if __name__ == "__main__":
    main()
