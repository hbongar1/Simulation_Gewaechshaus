import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

# Konfiguration
csv_pfad = 'Abgabeordner Gruppe 9/hourly_lamp_energy_2019.csv'

# 1. Daten einlesen
print(f"Lese Daten aus: {csv_pfad}")
# Das Trennzeichen ist ';' laut CSV-Check
df_lamp = pd.read_csv(csv_pfad, sep=';', encoding='utf-8')

# Zeitindex erstellen
# Format YYYYMMDDHH
df_lamp['datetime'] = pd.to_datetime(df_lamp['DateTime'].astype(str), format='%Y%m%d%H')
df_lamp.set_index('datetime', inplace=True)

# 2. Plotten
fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(df_lamp.index, df_lamp['Energy_kW'], color='#f1c40f', linewidth=0.5, label='Lampenstrombedarf')

# Formatierung
ax.set_ylabel('Leistung [kW]')
ax.set_xlabel('Zeit')
ax.set_title('Strombedarf Belichtung 2019')

# Y-Achse mit Tausendertrennzeichen
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))

# X-Achse: Monate
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))

ax.grid(True, alpha=0.3)
plt.tight_layout()

# Speichern und Anzeigen
output_file = 'plot_lamp_energy.png'
plt.savefig(output_file, dpi=150)
print(f"Plot gespeichert als: {output_file}")
plt.show()

# Ausgabe von Kennwerten
print("\n--- Kennwerte ---")
print(f"Maximaler Bedarf: {df_lamp['Energy_kW'].max():,.2f} kW")
print(f"Mittlerer Bedarf: {df_lamp['Energy_kW'].mean():,.2f} kW")
print(f"Summe Energie:    {df_lamp['Energy_kW'].sum():,.2f} kWh")
