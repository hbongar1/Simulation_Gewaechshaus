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

# Gaskessel
gaskessel_wirkungsgrad = 0.95               # 95%
capital_cost_gaskessel = 7                  # €/kW/a als Annuität
gaskessel_lifetime = 20                     # Jahre

# Netzstrom
strom_preis = 0.1361                          # €/kWh
gas_preis = 0.03                            # €/kWh

# ============================================================
# 3. Daten vorbereiten
# ============================================================

# Gemeinsamen Zeitindex erstellen
zeitindex = df_heizlast.index.intersection(df_strombedarf.index)

# Nur die ersten 168 Stunden (1 Woche) für schnellere Tests
# Kommentiere die nächste Zeile aus, um das ganze Jahr zu simulieren
# zeitindex = zeitindex[:168]  # 1 Woche

print(f"Simulationszeitraum: {zeitindex[0]} bis {zeitindex[-1]}")
print(f"Anzahl Zeitschritte: {len(zeitindex)}")

# Zeitreihen auf Simulationszeitraum einschränken
waermebedarf = df_heizlast.loc[zeitindex, 'Heizlast_kW']
strombedarf = df_strombedarf.loc[zeitindex, 'Energy_kW']

# Datenübersicht
print(f"\nMittlere Heizlast:      {waermebedarf.mean():.2f} kW")
print(f"Maximale Heizlast:      {waermebedarf.max():.2f} kW")
print(f"Minimale Heizlast:      {waermebedarf.min():.2f} kW")
print(f"Mittlerer Strombedarf:  {strombedarf.mean():.2f} kW")
print(f"Maximaler Strombedarf:  {strombedarf.max():.2f} kW")

# ============================================================
# 4. PyPSA-Netzwerk erstellen
# ============================================================

network = pypsa.Network()
network.set_snapshots(zeitindex)

# Busse
network.add('Bus', name='Strom', carrier='strom')
network.add('Bus', name='Waerme', carrier='waerme')
network.add('Bus', name='Gas', carrier='gas')

# Lasten
network.add('Load', name='Stromlast', bus='Strom', p_set=strombedarf)
network.add('Load', name='Waermelast', bus='Waerme', p_set=waermebedarf)

# Netzstrom (Import aus öffentlichem Netz)
network.add('Generator',
            name='Netz_Import',
            bus='Strom',
            p_nom=np.inf,
            marginal_cost=strom_preis,
            carrier='grid')

# Gasversorgung
network.add('Generator',
            name='Gas_Versorgung',
            bus='Gas',
            p_nom=5000,
            marginal_cost=gas_preis,
            carrier='gas')

# Gaskessel (Gas -> Wärme)
network.add('Link',
            name='Gaskessel',
            bus0='Gas',
            bus1='Waerme',
            p_nom_extendable=True,
            efficiency=gaskessel_wirkungsgrad,
            capital_cost=capital_cost_gaskessel,
            lifetime=gaskessel_lifetime)

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

# Strombilanz
print("\n--- Strombilanz ---")
strom_netz = network.generators_t.p['Netz_Import'].sum()
strom_last = network.loads_t.p['Stromlast'].sum()

print(f"Netzbezug:        {strom_netz:>12.2f} kWh")
print(f"Stromlast:        {strom_last:>12.2f} kWh")

# Wärmebilanz
print("\n--- Wärmebilanz ---")
waerme_kessel = network.links_t.p1['Gaskessel'].sum()
waerme_last = network.loads_t.p['Waermelast'].sum()

print(f"Gaskessel Wärme:  {waerme_kessel:>12.2f} kWh")
print(f"Wärmelast:        {waerme_last:>12.2f} kWh")

# Gasverbrauch
print("\n--- Gasverbrauch ---")
gas_kessel = network.links_t.p0['Gaskessel'].sum()

print(f"Gas Kessel:       {gas_kessel:>12.2f} kWh")

# Betriebskosten
print("\n--- Betriebskosten ---")
kosten_strom = strom_netz * strom_preis
kosten_gas = gas_kessel * gas_preis
operational_costs = round(kosten_strom + kosten_gas, 2)

print(f"Stromkosten:      {kosten_strom:>12.2f} €")
print(f"Gaskosten:        {kosten_gas:>12.2f} €")
print(f"Betriebskosten:   {operational_costs:>12.2f} €")

# Jährliche Investitionskosten
invest_cost_year_gaskessel = network.links.p_nom_opt['Gaskessel'] * capital_cost_gaskessel
invest_cost_year = round(invest_cost_year_gaskessel, 2)

print(f"\n--- Jährliche Investitionskosten ---")
print(f"Gaskessel:        {invest_cost_year:>12.2f} €")

# Gesamtkosten pro Jahr (= Betriebskosten + Investitions-Annuitäten)
gesamt_kosten = operational_costs + invest_cost_year
print(f"\n--- Gesamtkosten pro Jahr ---")
print(f"Betriebskosten:               {operational_costs:>12.2f} €")
print(f"Jährliche Investitionskosten:  {invest_cost_year:>12.2f} €")
print(f"Gesamtkosten pro Jahr:         {gesamt_kosten:>12.2f} €")



print("\n" + "=" * 80)
print("Optimierung erfolgreich abgeschlossen!")
print("=" * 80)

