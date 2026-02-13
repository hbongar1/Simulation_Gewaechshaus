import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math

# ============================================================
# Gewächshaus-Parameter
# ============================================================
A_grund = 10000                 # Grundfläche in m²
hoehe = 4.5                     # Höhe in m
V = A_grund * hoehe             # Luftvolumen in m³ (= 4500 m³)

# Hüllfläche berechnen (Dach + 4 Wände, quadratisch angenommen)
seite = math.sqrt(A_grund)      # Seitenlänge ≈ 31.6 m
A_wand = 4 * seite * hoehe      # Wandfläche
A_dach = A_grund                # Dachfläche ≈ Grundfläche
A_huell = A_wand + A_dach       # Gesamte Hüllfläche ≈ 1569 m²

print(f"Grundfläche: {A_grund} m²")
print(f"Volumen: {V} m³")
print(f"Hüllfläche: {A_huell:.0f} m² (Dach: {A_dach:.0f} + Wände: {A_wand:.0f})")

# Thermische Parameter
U = 4.0                         # U-Wert in W/(m²·K) - typisch Gewächshaus
T_i = 20                        # Solltemperatur Gewächshaus in °C
n = 0.5                         # Luftwechselrate in 1/h
cp_luft = 0.33333               # Spez. Wärmekapazität Luft in Wh/(K·m³)
eta_solar = 0.8                 # Solarer Transmissionsgrad (0.75-0.9)

# ============================================================
# Temperaturdaten Köln einlesen – nur 2019
# ============================================================
df_temp = pd.read_csv('Temperatur Köln.csv', sep=';')
df_temp['MESS_DATUM'] = df_temp['MESS_DATUM'].astype(str)
df_temp = df_temp[df_temp['MESS_DATUM'].str.startswith('2019')]
df_temp = df_temp.reset_index(drop=True)

T_a = df_temp['TT_TU'].values   # Außentemperatur in °C

print(f"Temperaturdaten 2019: {len(T_a)} Stunden")

# ============================================================
# Solardaten Bochum einlesen – nur 2019
# FG_LBERG = Globalstrahlung in J/(h·cm²)
# Umrechnung: × 10000/3600 = W/m²
# ============================================================
df_solar = pd.read_csv('Solareinstrahlung_Bochum.csv', sep=';')
df_solar.columns = df_solar.columns.str.strip()
df_solar['MESS_DATUM'] = df_solar['MESS_DATUM'].astype(str)
df_solar = df_solar[df_solar['MESS_DATUM'].str.startswith('2019')]
df_solar = df_solar.reset_index(drop=True)

# Globalstrahlung umrechnen in W/m²
G_solar = df_solar['FG_LBERG'].values.astype(float)
G_solar[G_solar < 0] = 0        # Fehlwerte (-999) auf 0 setzen
G_solar = G_solar * 10000 / 3600  # Umrechnung in W/m²

print(f"Solardaten 2019: {len(G_solar)} Stunden")

# Sicherstellen, dass beide Zeitreihen gleich lang sind
n_hours = min(len(T_a), len(G_solar))
T_a = T_a[:n_hours]
G_solar = G_solar[:n_hours]

# ============================================================
# Stündliche Heizlastberechnung
# ============================================================
Q_dot = []

for t in range(n_hours):
    # Transmissionswärmeverlust: Q = U × A × ΔT
    Q_trans = U * A_huell * (T_i - T_a[t])    # in W

    # Lüftungswärmeverlust: Q = V × n × cp × ΔT
    Q_luft = V * n * cp_luft * (T_i - T_a[t])  # in W

    # Solare Gewinne durch Dachfläche
    Q_solar = G_solar[t] * A_dach * eta_solar   # in W

    # Netto-Heizlast in kW
    Q = (Q_trans + Q_luft - Q_solar) / 1000
    Q_dot.append(max(Q, 0))  # keine negativen Werte (= keine Kühlung)

Q_dot = np.array(Q_dot)

# ============================================================
# Ergebnisse ausgeben
# ============================================================
print(f"\n--- Ergebnisse Heizlast 2019 ---")
print(f"Maximale Heizlast: {Q_dot.max():.1f} kW")
print(f"Mittlere Heizlast: {Q_dot.mean():.1f} kW")
print(f"Gesamter Heizenergiebedarf: {Q_dot.sum():.0f} kWh/a")
print(f"Stunden ohne Heizbedarf: {(Q_dot == 0).sum()}")

# CSV exportieren
df_result = pd.DataFrame({
    'MESS_DATUM': df_temp['MESS_DATUM'].values[:n_hours],
    'T_aussen_C': T_a,
    'Heizlast_kW': Q_dot
})
df_result.to_csv('heizlast_2019.csv', index=False)
print(f"Exportiert nach: heizlast_2019.csv")

# Graph erstellen
plt.figure(figsize=(12, 5))
plt.plot(Q_dot, linewidth=0.5, color='crimson')
plt.xlabel("Stunde des Jahres")
plt.ylabel("Heizlast [kW]")
plt.title("Stündliche Heizlast Gewächshaus – Köln 2019")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
