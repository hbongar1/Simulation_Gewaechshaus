import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

# Konfiguration
csv_pfad = 'Abgabeordner Gruppe 9/heatpump_cop_2019.csv'

# 1. Daten einlesen
print(f"Lese Daten aus: {csv_pfad}")
# Das Trennzeichen ist ',' laut CSV-Check
df_cop = pd.read_csv(csv_pfad, sep=',', encoding='utf-8')

# Zeitindex erstellen
# Format YYYYMMDDHH
df_cop['datetime'] = pd.to_datetime(df_cop['MESS_DATUM'].astype(str), format='%Y%m%d%H')
df_cop.set_index('datetime', inplace=True)

# 2. Plotten
fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(df_cop.index, df_cop['COP'], color='#27ae60', linewidth=0.5, label='COP')

# Formatierung
ax.set_ylabel('COP [-]')
ax.set_xlabel('Zeit')
ax.set_title('Wärmepumpe Coefficient of Performance (COP) 2019')

# X-Achse: Monate
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))

ax.grid(True, alpha=0.3)
plt.tight_layout()

# Speichern und Anzeigen
output_file = 'plot_heatpump_cop.png'
plt.savefig(output_file, dpi=150)
print(f"Plot gespeichert als: {output_file}")
plt.show()

# Ausgabe von Kennwerten
print("\n--- Kennwerte ---")
print(f"Maximaler COP: {df_cop['COP'].max():.2f}")
print(f"Mittlerer COP: {df_cop['COP'].mean():.2f}")
print(f"Minimaler COP: {df_cop['COP'].min():.2f}")
