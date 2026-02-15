# Vorbereitung der Solareinstrahlung-Daten
# Kombiniert Daten aus Bochum und Bremen (als Fallback)
# Erstellt bereinigte CSV-Datei für weitere Berechnungen

import csv
from datetime import datetime

print("="*80)
print("Solareinstrahlung-Daten vorbereiten")
print("="*80)

# Erst Bochum-Daten laden
print("\n1. Lade Bochum-Daten...")
solar_data_bochum = {}
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
            
            # Wert speichern (auch -999, wird später behandelt)
            solar_data_bochum[timestamp] = fg_lberg_str
        except (ValueError, IndexError):
            continue

print(f"   Bochum-Daten geladen: {len(solar_data_bochum)} Stunden")

# Dann Bremen-Daten als Fallback laden
print("\n2. Lade Bremen-Daten (Fallback)...")
solar_data_bremen = {}
with open('Solareinstrahlung_Bremen.csv', 'r', encoding='utf-8') as f:
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
            
            # Wert speichern
            solar_data_bremen[timestamp] = fg_lberg_str
        except (ValueError, IndexError):
            continue

print(f"   Bremen-Daten geladen: {len(solar_data_bremen)} Stunden")

# Kombinierte Solardaten erstellen: Bochum mit Bremen als Fallback
print("\n3. Kombiniere Daten mit Fallback-Logik...")
solar_data = {}
fallback_bremen_count = 0
fallback_previous_count = 0
last_valid_value = 0  # Startwert für den Fall, dass die ersten Werte fehlen

# Timestamps sortieren für chronologische Verarbeitung
sorted_timestamps = sorted(solar_data_bochum.keys())

for timestamp in sorted_timestamps:
    fg_lberg_str = solar_data_bochum[timestamp]
    source = "Bochum"
    
    # Wenn Bochum fehlerhaft (-999), versuche Bremen
    if fg_lberg_str == '-999':
        if timestamp in solar_data_bremen and solar_data_bremen[timestamp] != '-999':
            fg_lberg_str = solar_data_bremen[timestamp]
            fallback_bremen_count += 1
            source = "Bremen"
        else:
            # Auch Bremen hat keinen gültigen Wert - nutze vorherigen Wert
            fallback_previous_count += 1
            solar_data[timestamp] = last_valid_value
            source = "Previous"
            continue
    
    # Umrechnung von J/(h*cm²) zu W/m²
    try:
        fg_lberg = float(fg_lberg_str)
        solar_w_m2 = fg_lberg * 10000 / 3600  # W/m²
        solar_data[timestamp] = solar_w_m2
        last_valid_value = solar_w_m2  # Aktualisiere letzten gültigen Wert
    except ValueError:
        solar_data[timestamp] = last_valid_value
        fallback_previous_count += 1

print(f"   Verarbeitete Zeitstempel: {len(solar_data)}")
print(f"   - Bochum-Werte verwendet: {len(solar_data) - fallback_bremen_count - fallback_previous_count}")
print(f"   - Bremen-Werte verwendet: {fallback_bremen_count}")
print(f"   - Vorherige Werte verwendet: {fallback_previous_count}")

# Ergebnisse in CSV-Datei schreiben
print("\n4. Speichere bereinigte Daten...")
output_file = 'Solareinstrahlung_Bochum_Bremen.csv'
results = []

for timestamp in sorted(solar_data.keys()):
    timestamp_str = timestamp.strftime('%Y%m%d%H')
    solar_w_m2 = solar_data[timestamp]
    results.append([timestamp_str, round(solar_w_m2, 2)])

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerow(['DateTime', 'Solar_W_m2'])
    writer.writerows(results)

print(f"   Gespeichert: {output_file}")
print(f"   Anzahl Datensätze: {len(results)}")

# Statistik
if solar_data:
    values = list(solar_data.values())
    print("\n5. Statistik:")
    print(f"   Mittelwert: {sum(values) / len(values):.2f} W/m²")
    print(f"   Maximum: {max(values):.2f} W/m²")
    print(f"   Minimum: {min(values):.2f} W/m²")

print("\n" + "="*80)
print("Fertig! Bereinigte Daten können nun verwendet werden.")
print("="*80)
