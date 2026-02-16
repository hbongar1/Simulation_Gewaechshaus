import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Temperaturdaten Köln einlesen (CSV mit allen Jahren) und nur 2019 filtern
df_data_temp = pd.read_csv('Temperatur Köln.csv', sep=';')
df_data_temp['MESS_DATUM'] = df_data_temp['MESS_DATUM'].astype(str)
df_data_temp = df_data_temp[df_data_temp['MESS_DATUM'].str.startswith('2019')]
df_data_temp = df_data_temp.reset_index(drop=True)

# Parameter
T_senke = 35 + 273.15          # Vorlauftemperatur Wärmepumpe in Kelvin (z.B. 35°C Fußbodenheizung)
eta_carnot = 0.5               # Gütegrad / Carnot-Wirkungsgrad (typisch 0.4-0.6)

# Außentemperatur als Quelltemperatur
T_a_celsius = df_data_temp['TT_TU']    # Werte sind bereits in °C
T_quelle = T_a_celsius + 273.15         # Umrechnung in Kelvin

# Stündliche COP-Berechnung
# COP = eta_carnot * T_senke / (T_senke - T_quelle)
delta_T = T_senke - T_quelle
delta_T[delta_T <= 0] = np.nan          # Vermeidung Division durch 0 (wenn T_außen >= T_senke)

COP = eta_carnot * T_senke / delta_T
COP = COP.clip(upper=10)               # COP auf max 10 begrenzen (realistische Obergrenze)
COP = COP.fillna(10)                   # NaN (T_außen >= T_senke) mit 10 füllen - keine Heizung nötig

# Ergebnisse ausgeben
print(f"Anzahl Stunden 2019: {len(COP)}")
print(f"Mittlerer COP: {COP.mean():.2f}")
print(f"Minimaler COP: {COP.min():.2f}")
print(f"Maximaler COP: {COP.max():.2f}")

# COP als CSV exportieren
df_result = pd.DataFrame({
    'MESS_DATUM': df_data_temp['MESS_DATUM'],
    'T_aussen_C': T_a_celsius,
    'COP': COP
})
df_result.to_csv('heatpump_cop_2019.csv', index=False)
print("COP-Daten exportiert nach: heatpump_cop_2019.csv")

# Graph erstellen
plt.figure(figsize=(12, 5))
plt.plot(COP.values, linewidth=0.5)
plt.xlabel("Stunde des Jahres")
plt.ylabel("COP")
plt.title("Stündlicher COP der Wärmepumpe – Köln 2019")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# Referenzen
# [4] Destatis, "Erdgas - und Strom - Durchschnittspreise," Destatis.de. [Online]. Verfügbar unter: https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Erdgas-Strom-DurchschnittsPreise/_inhalt.html . [Zugriff am: 16-02-2026]
