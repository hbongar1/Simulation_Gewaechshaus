"""
Konventionelles Gewächshaus-Modell mit PyPSA
- Verwendet Gurobi als Optimizer
- Heizlast aus heizlast_2019.csv
- Strombedarf aus hourly_lamp_energy_2019.csv
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

# ============================================================
# 2. Parameter definieren
# ============================================================

# Netzstrom
strom_preis = 0.1361                          # €/kWh
gas_preis = 0.03                            # €/kWh

# Gaskessel
gaskessel_wirkungsgrad = 0.95               # 95%
gas_cost_heat = gas_preis/gaskessel_wirkungsgrad

# ============================================================
# 3. Daten vorbereiten
# ============================================================

# Gemeinsamen Zeitindex erstellen
zeitindex = df_heizlast.index.intersection(df_strombedarf.index)

# Nur die ersten 168 Stunden (1 Woche) für schnellere Tests
# Kommentiere die nächste Zeile aus, um das ganze Jahr zu simulieren
# zeitindex = zeitindex[:168]  # 1 Woche

print(f"\n")
print(f"Simulationszeitraum: {zeitindex[0]} bis {zeitindex[-1]}")
print(f"Anzahl Zeitschritte: {len(zeitindex)}")

# Zeitreihen auf Simulationszeitraum einschränken
waermebedarf = df_heizlast.loc[zeitindex, 'Heizlast_kW']
strombedarf = df_strombedarf.loc[zeitindex, 'Energy_kW']

# Datenübersicht
print(f"\nMittlere Heizlast:     {waermebedarf.mean():>12.2f} kW")
print(f"Maximale Heizlast:     {waermebedarf.max():>12.2f} kW")
print(f"Minimale Heizlast:     {waermebedarf.min():>12.2f} kW")
print(f"Mittlerer Strombedarf: {strombedarf.mean():>12.2f} kW")
print(f"Maximaler Strombedarf: {strombedarf.max():>12.2f} kW")
print(f"Minimale Strombedarf:  {strombedarf.min():>12.2f} kW")
print(f"\n")
# ============================================================
# 4. PyPSA-Netzwerk erstellen
# ============================================================

network = pypsa.Network()
network.set_snapshots(zeitindex)

# Busse
network.add('Bus', name='Strom', carrier='strom')
network.add('Bus', name='Waerme', carrier='waerme')
network.add('Bus', 'Gas', carrier='gas')

# Lasten
network.add('Load', name='Stromlast', bus='Strom', p_set=strombedarf)
network.add('Load', name='Waermelast', bus='Waerme', p_set=waermebedarf)

# Netzstrom (Import aus öffentlichem Netz)
network.add('Generator',
            name='Stromimport',
            bus='Strom',
            p_nom = np.inf,
            marginal_cost=strom_preis,
            carrier='grid')

# Gasversorgung
network.add('Generator',
            name='Gasimport',
            bus='Gas',
            p_nom = np.inf,
            marginal_cost=gas_preis,
            carrier='gas')

# Gaskessel
network.add("Link",
            name="Gaskessel",
            bus0="Gas",        
            bus1="Waerme",     
            p_nom=waermebedarf.max()/gaskessel_wirkungsgrad,
            efficiency=gaskessel_wirkungsgrad,
            carrier="gas")

# ============================================================
# 5. Optimierung mit Gurobi
# ============================================================

network.optimize(solver_name='gurobi')

# ============================================================
# 6. Ergebnisse ausgeben
# ============================================================

print("\n" + "=" * 80)
print("ERGEBNISSE")
print("=" * 80)

# Nennleisungen 
p_nom_gaskessel = waermebedarf.max()/gaskessel_wirkungsgrad
print(f"\nNennleistung Gaskessel: {p_nom_gaskessel:>12.2f} kW")


# Strombilanz
print("\n--- Strombilanz ---")
strom_netz = network.generators_t.p['Stromimport'].sum()
strom_last = network.loads_t.p['Stromlast'].sum()
print(f"Netzimport:       {strom_netz:>12.2f} kWh")
print(f"Stromlast:        {strom_last:>12.2f} kWh")

# Wärmebilanz
print("\n--- Wärmebilanz ---")
gas_import = network.generators_t.p['Gasimport'].sum()

waerme_last = network.loads_t.p['Waermelast'].sum()
print(f"Gasimport:    {gas_import:>12.2f} kWh")
print(f"Wärmelast:    {waerme_last:>12.2f} kWh")

# Betriebskosten
print("\n--- Betriebskosten pro Jahr ---")
kosten_strom = strom_netz * strom_preis
kosten_gas = gas_import * gas_cost_heat
operational_costs = round(kosten_strom + kosten_gas, 2)
print(f"Stromkosten:          {kosten_strom:>12.2f} €")
print(f"Gaskosten:            {kosten_gas:>12.2f} €")
print(f"Betriebskosten:       {operational_costs:>12.2f} €")
print(f"\n")