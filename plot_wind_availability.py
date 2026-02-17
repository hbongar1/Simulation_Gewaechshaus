import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

# Konfiguration
csv_pfad = 'Abgabeordner Gruppe 9/Windanlage Leistungsdaten.csv'
nennleistung_kw = 6000  # Aus der CSV-Datei

# 1. Daten einlesen
print(f"Lese Daten aus: {csv_pfad}")
# skiprows=4 weil die Daten erst in Zeile 6 beginnen (Header in Zeile 5, aber pandas zählt Header als Zeile 0)
# Die Header-Zeile ist Zeile 5 (0-indiziert 4), also skiprows=4 überspringt Metadata
df_wind = pd.read_csv(csv_pfad, sep=';', encoding='utf-8', skiprows=4)

# Relevante Spalten auswählen und umbenennen
df_wind = df_wind[['time', 'electricity']].copy()
df_wind = df_wind.rename(columns={'electricity': 'Wind_kW'})

# Zeitindex erstellen
df_wind['datetime'] = pd.to_datetime(df_wind['time'])
df_wind.set_index('datetime', inplace=True)

# 2. Verfügbarkeit berechnen
# Verfügbarkeit = Leistung / Nennleistung
df_wind['availability'] = df_wind['Wind_kW'] / nennleistung_kw

# Nur zur Sicherheit: Werte auf maximal 1 begrenzen (falls Datenfehler > Nennleistung)
df_wind['availability'] = df_wind['availability'].clip(upper=1.0)

# 3. Plotten
fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(df_wind.index, df_wind['availability'], color='#3498db', linewidth=0.5, label='Wind-Verfügbarkeit')

# Formatierung
ax.set_ylabel('Verfügbarkeit (Leistung / Nennleistung)')
ax.set_xlabel('Zeit')
ax.set_title(f'Windkraftanlagen-Verfügbarkeit 2019 (Nennleistung {nennleistung_kw} kW)')
ax.set_ylim(0, 1.05)  # Von 0 bis knapp über 1

# Y-Achse als Prozent formatieren
ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

# X-Achse: Monate
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))

ax.grid(True, alpha=0.3)
plt.tight_layout()

# Speichern und Anzeigen
output_file = 'plot_wind_availability.png'
plt.savefig(output_file, dpi=150)
print(f"Plot gespeichert als: {output_file}")
plt.show()

# Ausgabe von Kennwerten
print("\n--- Kennwerte ---")
print(f"Mittlere Verfügbarkeit: {df_wind['availability'].mean()*100:.2f} %")
print(f"Maximale Verfügbarkeit: {df_wind['availability'].max()*100:.2f} %")
print(f"Minimale Verfügbarkeit: {df_wind['availability'].min()*100:.2f} %")
