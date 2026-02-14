"""
Zukunftssystem Gewächshaus-Modell mit PyPSA
- Verwendet Gurobi als Optimizer
- Heizlast aus heizlast_2019.csv
- Strombedarf aus hourly_lamp_energy_2019.csv
- COP Wärmepumpe aus heatpump_cop_2019.csv
- Windkraftanlagen-Leistung aus Windanlage Leistungsdaten.csv
"""

import pypsa
import pandas as pd
import numpy as np

# ============================================================
# 1. Daten einlesen
# ============================================================

# Heizlast einlesen
df_heizlast = pd.read_csv('heizlast_2019.csv', sep=',', encoding='utf-8')
df_heizlast['datetime'] = pd.to_datetime(df_heizlast['MESS_DATUM'].astype(str), format='%Y%m%d%H')
df_heizlast.set_index('datetime', inplace=True)

# Strombedarf (Lampen) einlesen
df_strombedarf = pd.read_csv('hourly_lamp_energy_2019.csv', sep=';', encoding='utf-8')
df_strombedarf['datetime'] = pd.to_datetime(df_strombedarf['DateTime'].astype(str), format='%Y%m%d%H')
df_strombedarf.set_index('datetime', inplace=True)

# COP Wärmepumpe einlesen
df_cop = pd.read_csv('heatpump_cop_2019.csv', sep=',', encoding='utf-8')
df_cop['datetime'] = pd.to_datetime(df_cop['MESS_DATUM'].astype(str), format='%Y%m%d%H')
df_cop.set_index('datetime', inplace=True)

# Windkraftanlagen-Leistung einlesen
df_wind = pd.read_csv('Windanlage Leistungsdaten.csv', sep=';', encoding='utf-8', skiprows=4)
df_wind = df_wind[['time', 'electricity']].copy()
df_wind['datetime'] = pd.to_datetime(df_wind['time'])
df_wind.set_index('datetime', inplace=True)
df_wind = df_wind.rename(columns={'electricity': 'Wind_kW'})

# ============================================================
# 2. Parameter definieren
# ============================================================

# Windkraftanlage
wind_nennleistung = 6000        # kW - maximale Nennleistung
capital_cost_wind = 150         # €/kW/a als Annuität
wind_lifetime = 20              # Jahre

# Wärmepumpe
capital_cost_wp = 480           # €/kW/a als Annuität
wp_lifetime = 20                # Jahre

# Wärmespeicher
waermespeicher_kapazitaet = 5000            # kWh
capital_cost_waermespeicher = 5              # €/kWh/a als Annuität
waermespeicher_lifetime = 25                # Jahre
waermespeicher_standing_loss = 0.005         # Verlust pro Stunde

# Netzinteraktion
netz_import_kosten = 0.25       # €/kWh
netz_export_erloese = 0.08      # €/kWh
netz_max_export = 5000          # kW

# ============================================================
# 3. Daten vorbereiten
# ============================================================

# Gemeinsamen Zeitindex erstellen
zeitindex = df_heizlast.index.intersection(df_strombedarf.index)
zeitindex = zeitindex.intersection(df_cop.index)
zeitindex = zeitindex.intersection(df_wind.index)

print(f"Simulationszeitraum: {zeitindex[0]} bis {zeitindex[-1]}")
print(f"Anzahl Zeitschritte: {len(zeitindex)}")

# Zeitreihen auf Simulationszeitraum einschränken
waermebedarf = df_heizlast.loc[zeitindex, 'Heizlast_kW']
strombedarf = df_strombedarf.loc[zeitindex, 'Energy_kW']
cop_zeitreihe = df_cop.loc[zeitindex, 'COP']
windleistung = df_wind.loc[zeitindex, 'Wind_kW']

# Zeitliche Verfügbarkeit der Windanlage (p_max_pu)
wind_p_max_pu = windleistung / wind_nennleistung
wind_p_max_pu = wind_p_max_pu.clip(lower=0, upper=1)



# Datenübersicht
print(f"\nMittlere Heizlast:      {waermebedarf.mean():.2f} kW")
print(f"Maximale Heizlast:      {waermebedarf.max():.2f} kW")
print(f"Mittlerer Strombedarf:  {strombedarf.mean():.2f} kW")
print(f"Maximaler Strombedarf:  {strombedarf.max():.2f} kW")
print(f"Mittlerer COP:          {cop_zeitreihe.mean():.2f}")
print(f"Mittlere Windleistung:  {windleistung.mean():.2f} kW")
print(f"Maximale Windleistung:  {windleistung.max():.2f} kW")

# ============================================================
# 4. PyPSA-Netzwerk erstellen
# ============================================================

network = pypsa.Network()
network.set_snapshots(zeitindex)

# Busse
network.add('Bus', name='Strom', carrier='strom')
network.add('Bus', name='Wind', carrier='wind')
network.add('Bus', name='Waerme', carrier='waerme')

# Lasten
network.add('Load', name='Stromlast', bus='Strom', p_set=strombedarf)
network.add('Load', name='Waermelast', bus='Waerme', p_set=waermebedarf)

# Windkraftanlage -> Wind-Bus
network.add('Generator',
            name='Windkraftanlage',
            bus='Wind',
            p_nom_extendable=True,
            p_nom_max=wind_nennleistung,
            p_max_pu=wind_p_max_pu,
            capital_cost=capital_cost_wind,
            carrier='wind')

# Netz-Export (Überschuss-Windstrom verkaufen)
network.add('Generator',
            name='Netz_Export',
            bus='Wind',
            p_nom=netz_max_export,
            marginal_cost=-netz_export_erloese,
            sign=-1,
            carrier='grid_export')

# Wind-Eigenverbrauch (Wind-Bus -> Strom-Bus)
network.add('Link',
            name='Wind_Eigenverbrauch',
            bus0='Wind',
            bus1='Strom',
            p_nom=wind_nennleistung)

# Wärmepumpe (Strom -> Wärme) mit zeitabhängigem COP
network.add('Link',
            name='Waermepumpe',
            bus0='Strom',
            bus1='Waerme',
            efficiency=cop_zeitreihe,
            p_nom_extendable=True,
            capital_cost=capital_cost_wp,
            lifetime=wp_lifetime)

# Wärmespeicher
network.add('Store',
            name='Waermespeicher',
            bus='Waerme',
            e_nom=waermespeicher_kapazitaet,
            e_nom_extendable=True,
            capital_cost=capital_cost_waermespeicher,
            standing_loss=waermespeicher_standing_loss,
            e_cyclic=True,
            lifetime=waermespeicher_lifetime)

# Netz-Import (Backup)
network.add('Generator',
            name='Netz_Import',
            bus='Strom',
            p_nom=np.inf,
            marginal_cost=netz_import_kosten,
            carrier='grid')

# ============================================================
# 5. Optimierung mit Gurobi
# ============================================================

network.optimize(solver_name='gurobi')

# ============================================================
# 6. Ergebnisse ausgeben
# ============================================================

print("\n" + "=" * 80)
print("OPTIMIERUNGSERGEBNISSE")
print("=" * 80)

# Gesamtkosten
print(f"\nGesamtkosten: {network.objective:.2f} €")

# Optimierte Kapazitäten
print("\n--- Optimierte Kapazitäten ---")
wind_opt = network.generators.p_nom_opt['Windkraftanlage']
print(f"Windanlage:       {wind_opt:>12.2f} kW (max: {wind_nennleistung} kW)")

# Strombilanz
print("\n--- Strombilanz ---")
strom_wind_gesamt = network.generators_t.p['Windkraftanlage'].sum()
strom_wind_eigen = network.links_t.p0['Wind_Eigenverbrauch'].sum()
strom_netz_import = network.generators_t.p['Netz_Import'].sum()
strom_netz_export = network.generators_t.p['Netz_Export'].sum()
strom_wp = network.links_t.p0['Waermepumpe'].sum()
strom_last = network.loads_t.p['Stromlast'].sum()

print(f"Windkraft gesamt: {strom_wind_gesamt:>12.2f} kWh")
print(f"  Eigenverbrauch: {strom_wind_eigen:>12.2f} kWh")
print(f"  Netz Export:    {strom_netz_export:>12.2f} kWh")
print(f"Netz Import:      {strom_netz_import:>12.2f} kWh")
print(f"Wärmepumpe:       {strom_wp:>12.2f} kWh")
print(f"Stromlast:        {strom_last:>12.2f} kWh")

# Wärmebilanz
print("\n--- Wärmebilanz ---")
waerme_wp = network.links_t.p1['Waermepumpe'].sum()
waerme_last = network.loads_t.p['Waermelast'].sum()

print(f"Wärmepumpe:       {waerme_wp:>12.2f} kWh")
print(f"Wärmelast:        {waerme_last:>12.2f} kWh")

# Kostenaufschlüsselung
print("\n--- Kostenaufschlüsselung ---")
kosten_import = strom_netz_import * netz_import_kosten
erloese_export = strom_netz_export * netz_export_erloese

print(f"Stromimport:      {kosten_import:>12.2f} €")
print(f"Stromexport:     -{erloese_export:>12.2f} €")
print(f"Netto:            {kosten_import - erloese_export:>12.2f} €")

# Wärmespeicher
print("\n--- Wärmespeicher ---")
speicher_e = network.stores_t.e['Waermespeicher']
print(f"Durchschnitt:     {speicher_e.mean():>12.2f} kWh")
print(f"Maximum:          {speicher_e.max():>12.2f} kWh")
print(f"Minimum:          {speicher_e.min():>12.2f} kWh")

# Kennzahlen
print("\n--- Kennzahlen ---")
strom_verbrauch = strom_wind_eigen + strom_netz_import
if strom_verbrauch > 0:
    autarkie_strom = (strom_wind_eigen / strom_verbrauch) * 100
else:
    autarkie_strom = 0.0
print(f"Stromautarkie:    {autarkie_strom:>12.2f} %")

mittlerer_cop = abs(waerme_wp / strom_wp) if strom_wp > 0 else 0
print(f"Realisierter COP: {mittlerer_cop:>12.2f}")

print("\n" + "=" * 80)
print("Optimierung erfolgreich abgeschlossen!")
print("=" * 80)
