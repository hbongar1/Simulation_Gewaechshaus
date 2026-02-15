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
capital_cost_wind = 150                     # €/kW/a als Annuität
wind_lifetime = 20                          # Jahre
wind_nennleistung_vergleichsanlage = 6000   # kW - Nennleistung der Vergleichsanlage

# Stromspeicher
capital_cost_stromspeicher = 45             # €/kWh/a als Annuität     Wert prüfen ????
stromspeicher_lifetime = 15
stromspeicher_standing_loss = 0.0001         # Verlust pro Stunde

# Wärmepumpe
capital_cost_wp = 480           # €/kW/a als Annuität
wp_lifetime = 20                # Jahre

# Wärmespeicher
capital_cost_waermespeicher = 5              # €/kWh/a als Annuität
waermespeicher_lifetime = 25                # Jahre
waermespeicher_standing_loss = 0.005         # Verlust pro Stunde

# Netzinteraktion
netz_import_kosten = 0.25       # €/kWh
netz_export_erloese = 0         # €/kWh


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
wind_p_max_pu = windleistung / wind_nennleistung_vergleichsanlage
wind_p_max_pu = wind_p_max_pu.clip(lower=0, upper=1)

# Datenübersicht
print(f"\nMittlere Heizlast:      {waermebedarf.mean():.2f} kW")
print(f"Maximale Heizlast:      {waermebedarf.max():.2f} kW")
print(f"Mittlerer Strombedarf:  {strombedarf.mean():.2f} kW")
print(f"Maximaler Strombedarf:  {strombedarf.max():.2f} kW")
print(f"Mittlerer COP:          {cop_zeitreihe.mean():.2f}")

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
            p_max_pu=wind_p_max_pu,
            capital_cost=capital_cost_wind,
            lifetime=wind_lifetime,
            carrier='wind')

# Wind-Eigenverbrauch (Wind-Bus -> Strom-Bus)
network.add('Link',
            name='Wind_Eigenverbrauch',
            bus0='Wind',
            bus1='Strom',
            p_nom_extendable=True)    #Problem war noch auf alter nennletung von windanlage

# Speichen für Windenergie
network.add('Store',
            name = 'Stromspeicher',
            bus = 'Strom',
            e_nom_extendable = True,
            capital_cost = capital_cost_stromspeicher,
            lifetime= stromspeicher_lifetime,
            standing_loss = stromspeicher_standing_loss ,
            e_cyclic = True)


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


# Investitionskosten insgesamt 
invest_cost_stores      = network.stores.e_nom_opt * network.stores.capital_cost * network.stores.lifetime
invest_cost_generators  = network.generators.p_nom_opt * network.generators.capital_cost * network.generators.lifetime
invest_cost_links       = network.links.p_nom_opt * network.links.capital_cost * network.links.lifetime
df_invest_cost          = pd.concat([invest_cost_stores, invest_cost_generators, invest_cost_links]).fillna(0)
invest_cost             = round(df_invest_cost.sum(), 2)

print(f"\n--- Investitionskosten insgesamt ---")
print(df_invest_cost)
print(f"\nInvestitionskosten insgesamt: {invest_cost:.2f} €")

# Investitionskosten pro Jahr
invest_cost_year_stores      = network.stores.e_nom_opt * network.stores.capital_cost 
invest_cost_year_generators  = network.generators.p_nom_opt * network.generators.capital_cost 
invest_cost_year_links       = network.links.p_nom_opt * network.links.capital_cost 
df_invest_cost_year          = pd.concat([invest_cost_year_stores, invest_cost_year_generators, invest_cost_year_links]).fillna(0)
invest_cost_year             = round(df_invest_cost_year.sum(), 2)

print(f"\n--- Jährliche Investitionskosten ---")
print(df_invest_cost_year)
print(f"\nJährliche Investitionskosten: {invest_cost_year:.2f} €")


# Optimierte Leistung
print("\n--- Optimierte Leistung ---")
wind_opt = network.generators.p_nom_opt['Windkraftanlage']
print(f"Windanlage:       {wind_opt:>12.2f} kW ")
waermepume_opt = network.links.p_nom_opt['Waermepumpe']
print(f"Wärmepumpe:       {waermepume_opt:>12.2f} kW")

# Optimierte Speicherkapazität
stormspeicher_opt = network.stores.e_nom_opt['Stromspeicher']
print(f"Stromspeicher:       {stormspeicher_opt:>12.2f} kWh")
waermespeicher_opt = network.stores.e_nom_opt['Waermespeicher']
print(f"Wärmespeicher:       {waermespeicher_opt:>12.2f} kWh")


# Strombilanz
print("\n--- Strombilanz ---")
strom_wind_gesamt = network.generators_t.p['Windkraftanlage'].sum()
strom_wind_eigen = network.links_t.p0['Wind_Eigenverbrauch'].sum()
strom_netz_import = network.generators_t.p['Netz_Import'].sum()
strom_wp = network.links_t.p0['Waermepumpe'].sum()
strom_last = network.loads_t.p['Stromlast'].sum()

print(f"Windkraft gesamt: {strom_wind_gesamt:>12.2f} kWh")
print(f"  Eigenverbrauch: {strom_wind_eigen:>12.2f} kWh")
print(f"Netz Import:      {strom_netz_import:>12.2f} kWh")
print(f"Wärmepumpe:       {strom_wp:>12.2f} kWh")
print(f"Stromlast:        {strom_last:>12.2f} kWh")


# Gesamtkosten Gewächshaus für ein Jahr 
print("\n--- Gesamtkosten pro Jahr ---")
kosten_strom_import = strom_netz_import * netz_import_kosten
gesamt_kosten_gewaechshaus = kosten_strom_import + invest_cost_year
print(f"Stromimportkosten:            {kosten_strom_import:>12.2f} €")
print(f"Jährliche Investitionskosten:  {invest_cost_year:>12.2f} €")
print(f"Gesamtkosten pro Jahr:         {gesamt_kosten_gewaechshaus:>12.2f} €")

# Wärmebilanz
print("\n--- Wärmebilanz ---")
waerme_wp = network.links_t.p1['Waermepumpe'].sum()
waerme_last = network.loads_t.p['Waermelast'].sum()
print(f"Wärmepumpe:       {waerme_wp:>12.2f} kWh")
print(f"Wärmelast:        {waerme_last:>12.2f} kWh")

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