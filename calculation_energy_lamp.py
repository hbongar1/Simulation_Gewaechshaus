# Berechnung des stündlichen Energieverbrauchs der Lampen für 2019
# Pflanzen benötigen 14 Stunden Licht pro Tag: 6:00 - 20:00 Uhr
# Lampen gehen in Stunden an, wenn Solareinstrahlung < 100 W/m²

import math
import csv
from datetime import datetime, timedelta
from collections import defaultdict

# Leistungsaufnahme einer Lampe in Watt für 1,44 m^2 (120cm * 120cm)
leistungsaufnahme_einzeln = 632  # W
abdeckungsflaeche_einzeln = 2.5  # m²

# Größe des Gewächshauses
flaeche = 10000  # m² (1 Hektar)

# Anzahl der Lampen, aufgerundet auf die nächste ganze Zahl
anzahl_lampen = math.ceil(flaeche / abdeckungsflaeche_einzeln)

# Energieverbrauch gesamtes Gewächshaus pro Stunde in Watt
energieverbrauch_gesamt_stunde = anzahl_lampen * leistungsaufnahme_einzeln

print(f"Anzahl Lampen: {anzahl_lampen}")
print(f"Energieverbrauch pro Stunde (wenn alle an): {energieverbrauch_gesamt_stunde} W")

# Schwellwert für ausreichende Solareinstrahlung
SOLAR_THRESHOLD = 100  # W/m²

# Lichtzeitfenster: 6:00 - 20:00 Uhr (14 Stunden)
LIGHT_START_HOUR = 6
LIGHT_END_HOUR = 20

# Solareinstrahlung einlesen aus Solareinstrahlung_Bochum.csv
# Spalte FG_LBERG enthält die Werte in J/(h*cm²)
# Umrechnung: J/(h*cm²) * 10000/3600 = W/m²
solar_data = {}
with open('Solareinstrahlung_Bochum.csv', 'r', encoding='utf-8') as f:
    # Erste Zeile überspringen (Header)
    next(f)
    for line in f:
        parts = line.strip().split(';')
        if len(parts) < 9:
            continue
        
        # Datum im Format YYYYMMDDHH:MM
        datum_str = parts[1]
        try:
            # Nur das Datum und die Stunde extrahieren (ersten 10 Zeichen)
            timestamp = datetime.strptime(datum_str[:10], '%Y%m%d%H')
            
            # FG_LBERG Wert (Index 5)
            fg_lberg_str = parts[5].replace(',', '.')
            
            # -999 als fehlende Daten behandeln
            if fg_lberg_str == '-999':
                solar_w_m2 = 0
            else:
                # Umrechnung von J/(h*cm²) zu W/m²
                fg_lberg = float(fg_lberg_str)
                solar_w_m2 = fg_lberg * 10000 / 3600  # W/m²
            
            solar_data[timestamp] = solar_w_m2
        except (ValueError, IndexError):
            continue

print(f"Solareinstrahlung-Daten geladen: {len(solar_data)} Stunden")

# Stündliche Energieverbrauchsdaten berechnen
results = []

# Für jede Stunde des Jahres 2019
start_date = datetime(2019, 1, 1, 0, 0, 0)
end_date = datetime(2020, 1, 1, 0, 0, 0)

current_time = start_date

while current_time < end_date:
    # Stunde des Tages (0-23)
    hour_of_day = current_time.hour
    
    # Prüfen, ob wir im Lichtzeitfenster sind (6:00 - 20:00 Uhr)
    if LIGHT_START_HOUR <= hour_of_day < LIGHT_END_HOUR:
        # Im Lichtzeitfenster: Prüfe Solareinstrahlung
        solar_radiation = solar_data.get(current_time, 0)
        
        if solar_radiation < SOLAR_THRESHOLD:
            # Nicht genug Sonnenlicht -> Lampen an
            energy_wh = energieverbrauch_gesamt_stunde
        else:
            # Genug Sonnenlicht -> Lampen aus
            energy_wh = 0
    else:
        # Außerhalb des Lichtzeitfensters -> Lampen aus
        energy_wh = 0
    
    # Datum/Uhrzeit-Format: YYYYMMDDHH
    timestamp = current_time.strftime('%Y%m%d%H')
    results.append([timestamp, round(energy_wh, 2)])
    
    # Zur nächsten Stunde
    current_time += timedelta(hours=1)

# Ergebnisse in CSV-Datei schreiben
output_file = 'hourly_lamp_energy_2019.csv'
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerow(['DateTime', 'Energy_Wh'])
    writer.writerows(results)

print(f"\nErgebnisse gespeichert in: {output_file}")
print(f"Anzahl Datensätze: {len(results)}")

# Statistik berechnen
total_lamp_hours = sum(1 for r in results if r[1] > 0)
total_energy_kwh = sum(r[1] for r in results) / 1000

print(f"\nStatistik für 2019:")
print(f"Gesamte Stunden mit Lampenbetrieb: {total_lamp_hours}")
print(f"Gesamter Energieverbrauch: {total_energy_kwh:.2f} kWh")


