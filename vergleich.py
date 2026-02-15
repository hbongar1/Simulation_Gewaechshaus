"""
Vergleich: Zukunftssystem vs. Konventionelles Gewächshaus
- Führt beide Systeme hintereinander aus
- Erstellt Vergleichs-Plots
"""

import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ============================================================
# 1. Gemeinsame Daten einlesen
# ============================================================

df_heizlast = pd.read_csv('heizlast_2019.csv', sep=',', encoding='utf-8')
df_heizlast['datetime'] = pd.to_datetime(df_heizlast['MESS_DATUM'].astype(str), format='%Y%m%d%H')
df_heizlast.set_index('datetime', inplace=True)

df_strombedarf = pd.read_csv('hourly_lamp_energy_2019.csv', sep=';', encoding='utf-8')
df_strombedarf['datetime'] = pd.to_datetime(df_strombedarf['DateTime'].astype(str), format='%Y%m%d%H')
df_strombedarf.set_index('datetime', inplace=True)

df_cop = pd.read_csv('heatpump_cop_2019.csv', sep=',', encoding='utf-8')
df_cop['datetime'] = pd.to_datetime(df_cop['MESS_DATUM'].astype(str), format='%Y%m%d%H')
df_cop.set_index('datetime', inplace=True)

df_wind = pd.read_csv('Windanlage Leistungsdaten.csv', sep=';', encoding='utf-8', skiprows=4)
df_wind = df_wind[['time', 'electricity']].copy()
df_wind['datetime'] = pd.to_datetime(df_wind['time'])
df_wind.set_index('datetime', inplace=True)
df_wind = df_wind.rename(columns={'electricity': 'Wind_kW'})

# Gemeinsamer Zeitindex
zeitindex = df_heizlast.index.intersection(df_strombedarf.index)
zeitindex = zeitindex.intersection(df_cop.index)
zeitindex = zeitindex.intersection(df_wind.index)

waermebedarf = df_heizlast.loc[zeitindex, 'Heizlast_kW']
strombedarf = df_strombedarf.loc[zeitindex, 'Energy_kW']
cop_zeitreihe = df_cop.loc[zeitindex, 'COP']
windleistung = df_wind.loc[zeitindex, 'Wind_kW']

# ============================================================
# 2. KONVENTIONELLES SYSTEM
# ============================================================

print("KONVENTIONELLES SYSTEM - Optimierung läuft...")

strom_preis = 0.25
gas_preis = 0.08

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
           e_nom_extendable=True, capital_cost=10,
           standing_loss=0.005, e_cyclic=True, lifetime=25)

n_konv.add('Link', name='Gaskessel', bus0='Gas', bus1='Waerme',
           p_nom=1500, efficiency=0.95,
           capital_cost=7, lifetime=20)

n_konv.optimize(solver_name='gurobi')

# Ergebnisse konventionell
konv_strom_netz = n_konv.generators_t.p['Netz_Import'].sum()
konv_gas_kessel = n_konv.links_t.p0['Gaskessel'].sum()
konv_strom_kosten = konv_strom_netz * strom_preis
konv_gas_kosten = konv_gas_kessel * gas_preis
konv_betriebskosten = konv_strom_kosten + konv_gas_kosten

konv_invest_year_stores = n_konv.stores.e_nom_opt * n_konv.stores.capital_cost
konv_invest_year_links  = n_konv.links.p_nom_opt * n_konv.links.capital_cost
konv_invest_year = konv_invest_year_stores.sum() + konv_invest_year_links.sum()
konv_gesamt_jahr = konv_betriebskosten + konv_invest_year

# ============================================================
# 3. ZUKUNFTSSYSTEM
# ============================================================

print("ZUKUNFTSSYSTEM - Optimierung läuft...")

wind_nennleistung_vergleich = 6000
netz_import_kosten = 0.25

wind_p_max_pu = (windleistung / wind_nennleistung_vergleich).clip(lower=0, upper=1)

n_zuk = pypsa.Network()
n_zuk.set_snapshots(zeitindex)

n_zuk.add('Bus', name='Strom', carrier='strom')
n_zuk.add('Bus', name='Wind', carrier='wind')
n_zuk.add('Bus', name='Waerme', carrier='waerme')

n_zuk.add('Load', name='Stromlast', bus='Strom', p_set=strombedarf)
n_zuk.add('Load', name='Waermelast', bus='Waerme', p_set=waermebedarf)

n_zuk.add('Generator', name='Windkraftanlage', bus='Wind',
          p_nom_extendable=True, p_max_pu=wind_p_max_pu,
          capital_cost=150, lifetime=20, carrier='wind')

n_zuk.add('Link', name='Wind_Eigenverbrauch', bus0='Wind', bus1='Strom',
          p_nom_extendable=True)

n_zuk.add('Store', name='Stromspeicher', bus='Strom',
          e_nom_extendable=True, capital_cost=45,
          lifetime=15, standing_loss=0.0001, e_cyclic=True)

n_zuk.add('Link', name='Waermepumpe', bus0='Strom', bus1='Waerme',
          efficiency=cop_zeitreihe, p_nom_extendable=True,
          capital_cost=480, lifetime=20)

n_zuk.add('Store', name='Waermespeicher', bus='Waerme',
          e_nom_extendable=True, capital_cost=5,
          standing_loss=0.005, e_cyclic=True, lifetime=25)

n_zuk.add('Generator', name='Netz_Import', bus='Strom',
          p_nom=np.inf, marginal_cost=netz_import_kosten, carrier='grid')

n_zuk.optimize(solver_name='gurobi')

# Ergebnisse Zukunft
zuk_strom_import = n_zuk.generators_t.p['Netz_Import'].sum()
zuk_strom_wind = n_zuk.generators_t.p['Windkraftanlage'].sum()
zuk_strom_eigen = n_zuk.links_t.p0['Wind_Eigenverbrauch'].sum()
zuk_kosten_import = zuk_strom_import * netz_import_kosten

zuk_invest_year_stores = n_zuk.stores.e_nom_opt * n_zuk.stores.capital_cost
zuk_invest_year_gens   = n_zuk.generators.p_nom_opt * n_zuk.generators.capital_cost
zuk_invest_year_links  = n_zuk.links.p_nom_opt * n_zuk.links.capital_cost
zuk_invest_year = pd.concat([zuk_invest_year_stores, zuk_invest_year_gens, zuk_invest_year_links]).fillna(0).sum()
zuk_betriebskosten = zuk_kosten_import
zuk_gesamt_jahr = zuk_betriebskosten + zuk_invest_year

# ============================================================
# 4. VERGLEICH AUSGABE
# ============================================================

print("\n" + "=" * 60)
print("SYSTEMVERGLEICH")
print("=" * 60)
print(f"{'':30s} {'Konventionell':>14s} {'Zukunft':>14s}")
print("-" * 60)
print(f"Netzimport [kWh]:              {konv_strom_netz:>14,.0f} {zuk_strom_import:>14,.0f}")
print(f"Stromimportkosten [€/a]:       {konv_strom_kosten:>14,.2f} {zuk_kosten_import:>14,.2f}")
print(f"Gaskosten [€/a]:               {konv_gas_kosten:>14,.2f} {'---':>14s}")
print(f"Betriebskosten [€/a]:          {konv_betriebskosten:>14,.2f} {zuk_betriebskosten:>14,.2f}")
print(f"Investitionskosten [€/a]:      {konv_invest_year:>14,.2f} {zuk_invest_year:>14,.2f}")
print(f"Gesamtkosten [€/a]:            {konv_gesamt_jahr:>14,.2f} {zuk_gesamt_jahr:>14,.2f}")

einsparung = konv_gesamt_jahr - zuk_gesamt_jahr
print(f"\nEinsparung Zukunft: {einsparung:,.2f} €/Jahr ({einsparung/konv_gesamt_jahr*100:.1f}%)")

# ============================================================
# 5. PLOTS
# ============================================================

# --- Plot 1: Balkendiagramm Netzimport ---
fig, ax = plt.subplots(figsize=(8, 5))
systeme = ['Konventionell', 'Zukunftssystem']
netz_import_werte = [konv_strom_netz, zuk_strom_import]
farben = ['#e74c3c', '#2ecc71']
bars = ax.bar(systeme, netz_import_werte, color=farben, width=0.5)
for bar, val in zip(bars, netz_import_werte):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50000,
            f'{val:,.0f} kWh', ha='center', fontsize=11, fontweight='bold')
ax.set_ylabel('Netzimport [kWh/Jahr]')
ax.set_title('Netzimport – Konventionell vs. Zukunftssystem')
ax.set_ylim(0, max(netz_import_werte) * 1.15)
plt.tight_layout()
plt.savefig('plot_vergleich_netzimport.png', dpi=150)
plt.show()

# --- Plot 2: Stromimportkosten beider Systeme ---
fig, ax = plt.subplots(figsize=(8, 5))
strom_kosten_werte = [konv_strom_kosten, zuk_kosten_import]
bars = ax.bar(systeme, strom_kosten_werte, color=farben, width=0.5)
for bar, val in zip(bars, strom_kosten_werte):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10000,
            f'{val:,.0f} €', ha='center', fontsize=11, fontweight='bold')
ax.set_ylabel('Stromimportkosten [€/Jahr]')
ax.set_title('Stromimportkosten – Konventionell vs. Zukunftssystem')
ax.set_ylim(0, max(strom_kosten_werte) * 1.15)
plt.tight_layout()
plt.savefig('plot_vergleich_stromkosten.png', dpi=150)
plt.show()

# --- Plot 3: Windenergie-Leistungskurve über das Jahr ---
fig, ax = plt.subplots(figsize=(14, 5))
wind_erzeugung = n_zuk.generators_t.p['Windkraftanlage']
ax.plot(wind_erzeugung.index, wind_erzeugung.values, color='#3498db', alpha=0.7, linewidth=0.5, label='Windkraft-Erzeugung')
ax.set_ylabel('Leistung [kW]')
ax.set_xlabel('Zeit')
ax.set_title('Windkraftanlage – Erzeugte Leistung über das Jahr')
ax.legend(loc='upper right')
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
plt.tight_layout()
plt.savefig('plot_wind_leistungskurve.png', dpi=150)
plt.show()

# --- Plot 4: Windproduktion vs. Gewächshaus-Verbrauch ---
fig, ax = plt.subplots(figsize=(14, 5))
# Tägliche Mittelwerte für bessere Übersicht
wind_daily = wind_erzeugung.resample('D').mean()
verbrauch_daily = (strombedarf + n_zuk.links_t.p0['Waermepumpe']).resample('D').mean()

ax.plot(wind_daily.index, wind_daily.values, color='#3498db', linewidth=1.5, label='Windkraft-Erzeugung')
ax.plot(verbrauch_daily.index, verbrauch_daily.values, color='#e74c3c', linewidth=1.5, label='Gesamtverbrauch (Strom + WP)')
ax.fill_between(wind_daily.index, wind_daily.values, verbrauch_daily.values,
                where=wind_daily.values > verbrauch_daily.values, alpha=0.3, color='green',
                label='Wind > Verbrauch')
ax.fill_between(wind_daily.index, wind_daily.values, verbrauch_daily.values,
                where=wind_daily.values < verbrauch_daily.values, alpha=0.3, color='red',
                label='Verbrauch > Wind (Netzimport)')
ax.set_ylabel('Leistung [kW] (Tagesmittel)')
ax.set_xlabel('Zeit')
ax.set_title('Windproduktion vs. Gewächshaus-Verbrauch (Tagesmittel)')
ax.legend(loc='upper right')
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
plt.tight_layout()
plt.savefig('plot_wind_vs_verbrauch.png', dpi=150)
plt.show()

# --- Plot 5: Speicher-Füllstand ---
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

strom_speicher = n_zuk.stores_t.e['Stromspeicher']
axes[0].plot(strom_speicher.index, strom_speicher.values, color='#3498db', linewidth=0.8)
axes[0].set_ylabel('Energie [kWh]')
axes[0].set_title('Stromspeicher – Füllstand über das Jahr')

waerme_speicher = n_zuk.stores_t.e['Waermespeicher']
axes[1].plot(waerme_speicher.index, waerme_speicher.values, color='#e74c3c', linewidth=0.8)
axes[1].set_ylabel('Energie [kWh]')
axes[1].set_xlabel('Zeit')
axes[1].set_title('Wärmespeicher – Füllstand über das Jahr')

for a in axes:
    a.xaxis.set_major_locator(mdates.MonthLocator())
    a.xaxis.set_major_formatter(mdates.DateFormatter('%b'))

plt.tight_layout()
plt.savefig('plot_speicher_fuellstand.png', dpi=150)
plt.show()

# --- Plot 6: Betriebskosten-Vergleich (gestapelt) ---
fig, ax = plt.subplots(figsize=(10, 6))

x = np.arange(2)
breite = 0.5

# Konventionell: Strom + Gas + Invest
konv_stack = [konv_strom_kosten, konv_gas_kosten, konv_invest_year]
# Zukunft: Stromimport + Invest
zuk_stack = [zuk_kosten_import, 0, zuk_invest_year]

p1 = ax.bar(x, [konv_stack[0], zuk_stack[0]], breite, color='#e74c3c', label='Stromkosten')
p2 = ax.bar(x, [konv_stack[1], zuk_stack[1]], breite, bottom=[konv_stack[0], zuk_stack[0]],
            color='#f39c12', label='Gaskosten')
p3 = ax.bar(x, [konv_stack[2], zuk_stack[2]], breite,
            bottom=[konv_stack[0]+konv_stack[1], zuk_stack[0]+zuk_stack[1]],
            color='#3498db', label='Investitionskosten (Annuität)')

# Gesamtwerte oben anzeigen
for i, total in enumerate([konv_gesamt_jahr, zuk_gesamt_jahr]):
    ax.text(i, total + 20000, f'{total:,.0f} €', ha='center', fontsize=11, fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels(['Konventionell', 'Zukunftssystem'])
ax.set_ylabel('Kosten [€/Jahr]')
ax.set_title('Jährliche Gesamtkosten – Vergleich beider Systeme')
ax.legend(loc='upper right')
ax.set_ylim(0, max(konv_gesamt_jahr, zuk_gesamt_jahr) * 1.15)
plt.tight_layout()
plt.savefig('plot_vergleich_betriebskosten.png', dpi=150)
plt.show()

print("\nAlle Plots wurden gespeichert!")
