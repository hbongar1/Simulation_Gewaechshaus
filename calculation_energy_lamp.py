# Berechnung des stündlichen Energieverbrauchs der Lampen für 2019

import math
import csv
from datetime import datetime, timedelta

# Leistungsaufnahme einer Lampe in Watt für 1,44 m^2 (120cm * 120cm)
leistungsaufnahme_einzeln = 632  # W
abdeckungsflaeche_einzeln = 2.5  # m²

# Größe des Gewächshauses
flaeche = 10000  # m² (1 Hektar)

# Anzahl der Lampen, aufgerundet auf die nächste ganze Zahl
anzahl_lampen = math.ceil(flaeche / abdeckungsflaeche_einzeln)

# Energieverbrauch gesamtes Gewächshaus pro Stunde in Watt
energieverbrauch_gesamt_stunde = anzahl_lampen * leistungsaufnahme_einzeln

# Energieverbrauch gesamtes Gewächshaus pro Minute in Watt
energieverbrauch_gesamt_minute = energieverbrauch_gesamt_stunde / 60

print(f"Anzahl Lampen: {anzahl_lampen}")
print(f"Energieverbrauch pro Stunde (wenn alle an): {energieverbrauch_gesamt_stunde} W")
print(f"Energieverbrauch pro Minute (wenn alle an): {energieverbrauch_gesamt_minute} W")

# Sonnenauf- und -untergangszeiten einlesen
sonnenzeiten = {}
with open('sunrise_sunset_2019.csv', 'r', encoding='utf-8') as f:
    # Erste Zeile überspringen (Header)
    next(f)
    for line in f:
        parts = line.strip().split(';')
        datum_str = parts[0]
        datum = datetime.strptime(datum_str, '%Y%m%d')
        
        # Sonnenaufgang und -untergang in datetime umwandeln
        sunrise_time = datetime.strptime(parts[1], '%H:%M:%S').time()
        sunset_time = datetime.strptime(parts[2], '%H:%M:%S').time()
        
        sunrise = datetime.combine(datum, sunrise_time)
        sunset = datetime.combine(datum, sunset_time)
        
        sonnenzeiten[datum.date()] = {
            'sunrise': sunrise,
            'sunset': sunset
        }

# Stündliche Energieverbrauchsdaten berechnen
results = []

# Für jede Stunde des Jahres 2019
start_date = datetime(2019, 1, 1, 0, 0, 0)
end_date = datetime(2020, 1, 1, 0, 0, 0)

current_time = start_date

while current_time < end_date:
    # Ende der aktuellen Stunde
    hour_end = current_time + timedelta(hours=1)
    
    # Tag bestimmen
    day = current_time.date()
    
    # Sonnenzeiten für diesen Tag abrufen
    if day in sonnenzeiten:
        sunrise = sonnenzeiten[day]['sunrise']
        sunset = sonnenzeiten[day]['sunset']
        
        # Berechnen, wie viele Minuten die Lampen in dieser Stunde leuchten
        minutes_on = 0
        
        # Lampen leuchten zwischen Sonnenuntergang und Sonnenaufgang
        # Fall 1: Sonnenaufgang liegt in dieser Stunde
        if current_time < sunrise <= hour_end:
            # Lampen sind an von Stundenbeginn bis Sonnenaufgang
            minutes_on = (sunrise - current_time).total_seconds() / 60
        # Fall 2: Sonnenuntergang liegt in dieser Stunde
        elif current_time < sunset <= hour_end:
            # Lampen sind an von Sonnenuntergang bis Stundenende
            minutes_on = (hour_end - sunset).total_seconds() / 60
        # Fall 3: Aktuelle Stunde ist komplett in der Nacht (vor Sonnenaufgang oder nach Sonnenuntergang)
        elif hour_end <= sunrise or current_time >= sunset:
            minutes_on = 60
        # Fall 4: Aktuelle Stunde ist komplett am Tag (zwischen Sonnenaufgang und -untergang)
        else:
            minutes_on = 0
        
        # Energieverbrauch in dieser Stunde in Wh (Wattstunden)
        energy_wh = minutes_on * energieverbrauch_gesamt_minute
        
        # Datum/Uhrzeit-Format: YYYYMMDDHH
        timestamp = current_time.strftime('%Y%m%d%H')
        
        results.append([timestamp, round(energy_wh, 2)])
    
    # Zur nächsten Stunde
    current_time = hour_end

# Ergebnisse in CSV-Datei schreiben
output_file = 'hourly_lamp_energy_2019.csv'
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerow(['DateTime', 'Energy_Wh'])
    writer.writerows(results)


