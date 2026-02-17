import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

# Konfiguration
csv_pfad = 'Abgabeordner Gruppe 9/heizlast_2019.csv'

# 1. Daten einlesen
print(f"Lese Daten aus: {csv_pfad}")
df_heizlast = pd.read_csv(csv_pfad, sep=',', encoding='utf-8')

# Zeitindex erstellen
# Format ist YYYYMMDDHH (z.B. 2019010100)
df_heizlast['datetime'] = pd.to_datetime(df_heizlast['MESS_DATUM'].astype(str), format='%Y%m%d%H')
df_heizlast.set_index('datetime', inplace=True)

# 2. Plotten
fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(df_heizlast.index, df_heizlast['Heizlast_kW'], color='#e74c3c', linewidth=0.5, label='Heizlast')

# Formatierung
ax.set_ylabel('Heizlast [kW]')
ax.set_xlabel('Zeit')
ax.set_title('Heizlastverlauf 2019')

# Y-Achse mit Tausendertrennzeichen
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))

# X-Achse: Monate
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))

ax.grid(True, alpha=0.3)
ax.legend(loc='upper right')
plt.tight_layout()

# Speichern und Anzeigen
output_file = 'plot_heizlast.png'
plt.savefig(output_file, dpi=150)
print(f"Plot gespeichert als: {output_file}")
plt.show()

# Ausgabe von Kennwerten
print("\n--- Kennwerte ---")
print(f"Maximale Heizlast: {df_heizlast['Heizlast_kW'].max():,.2f} kW")
print(f"Mittlere Heizlast: {df_heizlast['Heizlast_kW'].mean():,.2f} kW")
print(f"Summe Heizlast:    {df_heizlast['Heizlast_kW'].sum():,.2f} kWh")
