"""
Vergleich: Zukunftssystem vs. Konventionelles Gewächshaus
- Führt beide Systeme hintereinander aus
- Vergleicht die Ergebnisse direkt
"""

import pypsa
import pandas as pd
import numpy as np

# ============================================================
# 1. Gemeinsame Daten einlesen
# ============================================================

# Heizlast einlesen
df_heizlast = pd.read_csv('heizlast_2019.csv', sep=',', encoding='utf-8')
df_heizlast['datetime'] = pd.to_datetime(df_heizlast['MESS_DATUM'].astype(str), format='%Y%m%d%H')
df_heizlast.set_index('datetime', inplace=True)

# Strombedarf (Lampen) einlesen
df_strombedarf = pd.read_csv('hourly_lamp_energy_2019.csv', sep=';', encoding='utf-8')
df_strombedarf['datetime'] = pd.to_datetime(df_strombedarf['DateTime'].astype(str), format='%Y%m%d%H')
df_strombedarf.set_index('datetime', inplace=True)

# COP Wärmepumpe einlesen (nur Zukunftssystem)
df_cop = pd.read_csv('heatpump_cop_2019.csv', sep=',', encoding='utf-8')
df_cop['datetime'] = pd.to_datetime(df_cop['MESS_DATUM'].astype(str), format='%Y%m%d%H')
df_cop.set_index('datetime', inplace=True)

# Windkraftanlagen-Leistung einlesen (nur Zukunftssystem)
df_wind = pd.read_csv('Windanlage Leistungsdaten.csv', sep=';', encoding='utf-8', skiprows=4)
df_wind = df_wind[['time', 'electricity']].copy()
df_wind['datetime'] = pd.to_datetime(df_wind['time'])
df_wind.set_index('datetime', inplace=True)
df_wind = df_wind.rename(columns={'electricity': 'Wind_kW'})

# Gemeinsamer Zeitindex
zeitindex = df_heizlast.index.intersection(df_strombedarf.index)
zeitindex = zeitindex.intersection(df_cop.index)
zeitindex = zeitindex.intersection(df_wind.index)

print(f"Simulationszeitraum: {zeitindex[0]} bis {zeitindex[-1]}")
print(f"Anzahl Zeitschritte: {len(zeitindex)}")

# Zeitreihen
waermebedarf = df_heizlast.loc[zeitindex, 'Heizlast_kW']
strombedarf = df_strombedarf.loc[zeitindex, 'Energy_kW']
cop_zeitreihe = df_cop.loc[zeitindex, 'COP']
windleistung = df_wind.loc[zeitindex, 'Wind_kW']

# ============================================================
# 2. KONVENTIONELLES SYSTEM
# ============================================================

print("\n" + "=" * 80)
print("KONVENTIONELLES SYSTEM - Optimierung läuft...")
print("=" * 80)

# Parameter
waermespeicher_kap_konv = 5000
capital_cost_ws_konv = 10
ws_lifetime_konv = 25
ws_standing_loss_konv = 0.005

gaskessel_leistung = 1500
gaskessel_wirkungsgrad = 0.95
capital_cost_gaskessel = 7
gaskessel_lifetime = 20

strom_preis = 0.25
gas_preis = 0.08

# Netzwerk
n_konv = pypsa.Network()
n_konv.set_snapshots(zeitindex)

n_konv.add('Bus', name='Strom', carrier='strom')
n_konv.add('Bus', name='Waerme', carrier='waerme')
n_konv.add('Bus', name='Gas', carrier='gas')

n_konv.add('Load', name='Stromlast', bus='Strom', p_set=strombedarf)
n_konv.add('Load', name='Waermelast', bus='Waerme', p_set=waermebedarf)

n_konv.add('Generator', name='Netz_Import', bus='Strom',
           p_nom=10000, marginal_cost=strom_preis, carrier='grid')

n_konv.add('Generator', name='Gas_Versorgung', bus='Gas',
           p_nom=5000, marginal_cost=gas_preis, carrier='gas')

n_konv.add('Store', name='Waermespeicher', bus='Waerme',
           e_nom=waermespeicher_kap_konv, e_nom_extendable=True,
           capital_cost=capital_cost_ws_konv,
           standing_loss=ws_standing_loss_konv,
           e_cyclic=True, lifetime=ws_lifetime_konv)

n_konv.add('Link', name='Gaskessel', bus0='Gas', bus1='Waerme',
           p_nom=gaskessel_leistung, efficiency=gaskessel_wirkungsgrad,
           capital_cost=capital_cost_gaskessel, lifetime=gaskessel_lifetime)

n_konv.optimize(solver_name='gurobi')

# Ergebnisse konventionell
konv_gesamtkosten = n_konv.objective
konv_strom_netz = n_konv.generators_t.p['Netz_Import'].sum()
konv_gas_kessel = n_konv.links_t.p0['Gaskessel'].sum()
konv_strom_kosten = konv_strom_netz * strom_preis
konv_gas_kosten = konv_gas_kessel * gas_preis
konv_betriebskosten = konv_strom_kosten + konv_gas_kosten

# ============================================================
# 3. ZUKUNFTSSYSTEM
# ============================================================

print("\n" + "=" * 80)
print("ZUKUNFTSSYSTEM - Optimierung läuft...")
print("=" * 80)

# Parameter
wind_nennleistung = 6000
capital_cost_wind = 150
wind_lifetime = 20

capital_cost_wp = 480
wp_lifetime = 20

waermespeicher_kap_zuk = 5000
capital_cost_ws_zuk = 5
ws_lifetime_zuk = 25
ws_standing_loss_zuk = 0.005

netz_import_kosten = 0.25
netz_export_erloese = 0.08
netz_max_export = 5000

wind_p_max_pu = (windleistung / wind_nennleistung).clip(lower=0, upper=1)

# Netzwerk
n_zuk = pypsa.Network()
n_zuk.set_snapshots(zeitindex)

n_zuk.add('Bus', name='Strom', carrier='strom')
n_zuk.add('Bus', name='Wind', carrier='wind')
n_zuk.add('Bus', name='Waerme', carrier='waerme')

n_zuk.add('Load', name='Stromlast', bus='Strom', p_set=strombedarf)
n_zuk.add('Load', name='Waermelast', bus='Waerme', p_set=waermebedarf)

n_zuk.add('Generator', name='Windkraftanlage', bus='Wind',
          p_nom_extendable=True, p_nom_max=wind_nennleistung,
          p_max_pu=wind_p_max_pu, capital_cost=capital_cost_wind,
          lifetime=wind_lifetime, carrier='wind')

n_zuk.add('Generator', name='Netz_Export', bus='Wind',
          p_nom=netz_max_export, marginal_cost=-netz_export_erloese,
          sign=-1, carrier='grid_export')

n_zuk.add('Link', name='Wind_Eigenverbrauch', bus0='Wind', bus1='Strom',
          p_nom=wind_nennleistung)

n_zuk.add('Link', name='Waermepumpe', bus0='Strom', bus1='Waerme',
          efficiency=cop_zeitreihe, p_nom_extendable=True,
          capital_cost=capital_cost_wp, lifetime=wp_lifetime)

n_zuk.add('Store', name='Waermespeicher', bus='Waerme',
          e_nom=waermespeicher_kap_zuk, e_nom_extendable=True,
          capital_cost=capital_cost_ws_zuk,
          standing_loss=ws_standing_loss_zuk,
          e_cyclic=True, lifetime=ws_lifetime_zuk)

n_zuk.add('Generator', name='Netz_Import', bus='Strom',
          p_nom=np.inf, marginal_cost=netz_import_kosten, carrier='grid')

n_zuk.optimize(solver_name='gurobi')

# Ergebnisse Zukunft
zuk_gesamtkosten = n_zuk.objective
zuk_strom_import = n_zuk.generators_t.p['Netz_Import'].sum()
zuk_strom_export = n_zuk.generators_t.p['Netz_Export'].sum()
zuk_strom_wind = n_zuk.generators_t.p['Windkraftanlage'].sum()
zuk_strom_eigen = n_zuk.links_t.p0['Wind_Eigenverbrauch'].sum()
zuk_wp_strom = n_zuk.links_t.p0['Waermepumpe'].sum()
zuk_kosten_import = zuk_strom_import * netz_import_kosten
zuk_erloese_export = zuk_strom_export * netz_export_erloese

# Investitionskosten Zukunft
invest_stores = n_zuk.stores.e_nom_opt * n_zuk.stores.capital_cost * n_zuk.stores.lifetime
invest_gens = n_zuk.generators.p_nom_opt * n_zuk.generators.capital_cost * n_zuk.generators.lifetime
invest_links = n_zuk.links.p_nom_opt * n_zuk.links.capital_cost * n_zuk.links.lifetime
zuk_invest_gesamt = pd.concat([invest_stores, invest_gens, invest_links]).fillna(0).sum()

# ============================================================
# 4. VERGLEICH
# ============================================================

print("\n\n")
print("█" * 80)
print("█" + " " * 28 + "SYSTEMVERGLEICH" + " " * 36 + "█")
print("█" * 80)

print(f"""
{'':40s} {'Konventionell':>15s} {'Zukunft':>15s}
{'─' * 72}

JÄHRLICHE GESAMTKOSTEN (PyPSA)
  Gesamtkosten (network.objective):  {konv_gesamtkosten:>14,.2f} € {zuk_gesamtkosten:>14,.2f} €

BETRIEBSKOSTEN
  Stromimport:                       {konv_strom_kosten:>14,.2f} € {zuk_kosten_import:>14,.2f} €
  Gaskosten:                         {konv_gas_kosten:>14,.2f} €          {'---':>10s}
  Stromexport-Erlöse:                         {'---':>10s} {-zuk_erloese_export:>14,.2f} €

INVESTITIONSKOSTEN (Gesamt über Lebensdauer)
  Zukunftssystem:                              {'---':>10s} {zuk_invest_gesamt:>14,.2f} €

ENERGIEBILANZ
  Strombezug Netz:                   {konv_strom_netz:>14,.2f} kWh {zuk_strom_import:>14,.2f} kWh
  Gasverbrauch:                      {konv_gas_kessel:>14,.2f} kWh          {'---':>10s}
  Windkraft-Erzeugung:                        {'---':>10s} {zuk_strom_wind:>14,.2f} kWh
  Windkraft-Eigenverbrauch:                   {'---':>10s} {zuk_strom_eigen:>14,.2f} kWh
  Windkraft-Export:                            {'---':>10s} {zuk_strom_export:>14,.2f} kWh
""")

# Einsparung
einsparung = konv_gesamtkosten - zuk_gesamtkosten
einsparung_pct = (einsparung / konv_gesamtkosten) * 100

print("─" * 72)
print(f"\n  ERGEBNIS:")
if einsparung > 0:
    print(f"  ✅ Das Zukunftssystem spart {einsparung:,.2f} €/Jahr ({einsparung_pct:.1f}%)")
    print(f"     gegenüber dem konventionellen System.")
    if zuk_invest_gesamt > 0:
        amortisation = zuk_invest_gesamt / einsparung
        print(f"  📊 Amortisationszeit: {amortisation:.1f} Jahre")
else:
    print(f"  ❌ Das konventionelle System ist {-einsparung:,.2f} €/Jahr ({-einsparung_pct:.1f}%)")
    print(f"     günstiger als das Zukunftssystem.")

print("\n" + "█" * 80)
