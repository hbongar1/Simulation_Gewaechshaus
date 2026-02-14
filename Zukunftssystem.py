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


class ZukunftssystemParameter:
    def __init__(self):
        # Windkraftanlage (aus CSV)
        self.wind_nennleistung = 6000  # kW - Nennleistung der Anlage
        
        # Wärmepumpe
        self.wp_leistung_elektrisch = 2000  # kW - elektrische Leistung
        
        # Wärmespeicher
        self.waermespeicher_kapazitaet = 5000  # kWh
        
        # Netzinteraktion (falls benötigt als Backup)
        self.netz_import_kosten = 0.25  # €/kWh
        self.netz_export_erloese = 0.08  # €/kWh
        self.netz_max_import = 5000  # kW
        self.netz_max_export = 5000  # kW


def lade_heizlast(dateiname='heizlast_2019.csv'):
    """Lädt Heizlastdaten aus CSV-Datei"""
    df = pd.read_csv(dateiname, sep=',', encoding='utf-8')
    
    # Datum parsen
    df['datetime'] = pd.to_datetime(df['MESS_DATUM'].astype(str), format='%Y%m%d%H')
    
    # Setze datetime als Index
    df.set_index('datetime', inplace=True)
    
    return df[['Heizlast_kW']]


def lade_strombedarf(dateiname='hourly_lamp_energy_2019.csv'):
    """Lädt Strombedarfsdaten der Lampen aus CSV-Datei"""
    df = pd.read_csv(dateiname, sep=';', encoding='utf-8')
    
    # Datum parsen
    df['datetime'] = pd.to_datetime(df['DateTime'].astype(str), format='%Y%m%d%H')
    
    # Setze datetime als Index
    df.set_index('datetime', inplace=True)
    
    return df[['Energy_kW']]


def lade_cop_waermepumpe(dateiname='heatpump_cop_2019.csv'):
    """Lädt COP-Daten der Wärmepumpe aus CSV-Datei"""
    df = pd.read_csv(dateiname, sep=',', encoding='utf-8')
    
    # Datum parsen
    df['datetime'] = pd.to_datetime(df['MESS_DATUM'].astype(str), format='%Y%m%d%H')
    
    # Setze datetime als Index
    df.set_index('datetime', inplace=True)
    
    return df[['COP']]


def lade_windleistung(dateiname='Windanlage Leistungsdaten.csv'):
    """Lädt Windkraftanlagen-Leistungsdaten aus CSV-Datei"""
    # CSV hat besonderes Format mit vielen Spalten und Metadaten
    df = pd.read_csv(dateiname, sep=';', encoding='utf-8', skiprows=4)
    
    # Relevante Spalten: time und electricity
    df = df[['time', 'electricity']].copy()
    
    # Datum parsen (UTC Format)
    df['datetime'] = pd.to_datetime(df['time'])
    
    # Setze datetime als Index
    df.set_index('datetime', inplace=True)
    
    # Leistung in kW (bereits in kW laut CSV)
    df = df.rename(columns={'electricity': 'Wind_kW'})
    
    return df[['Wind_kW']]


def erstelle_zukunftssystem(zeitindex, params, waermebedarf, strombedarf, cop_zeitreihe, windleistung):
    """Erstellt das PyPSA-Netzwerk für das Zukunftssystem"""
    
    network = pypsa.Network()
    network.set_snapshots(zeitindex)
    
    # Busse definieren
    network.add("Bus", "Strom", carrier="strom")
    network.add("Bus", "Wind", carrier="wind")
    network.add("Bus", "Waerme", carrier="waerme")
    
    # Lasten hinzufügen
    network.add("Load", 
                "Stromlast",
                bus="Strom",
                p_set=strombedarf)
    
    network.add("Load",
                "Waermelast",
                bus="Waerme",
                p_set=waermebedarf)
    
    # Windkraftanlage -> Wind-Bus
    # p_max_pu: Verfügbarkeit als Anteil der Nennleistung (0 bis 1)
    p_max_pu = windleistung / params.wind_nennleistung
    p_max_pu = p_max_pu.clip(lower=0, upper=1)
    
    network.add("Generator",
                "Windkraftanlage",
                bus="Wind",
                p_nom=params.wind_nennleistung,
                p_max_pu=p_max_pu,
                marginal_cost=0.01,  # Minimale Wartungskosten
                capital_cost=1200,  # €/kW
                carrier="wind")
    
    # Netz-Export (Überschuss-Windstrom verkaufen)
    # sign=-1: Generator wirkt als Senke auf Wind-Bus (nimmt Strom auf = Einspeisung ins Netz)
    network.add("Generator",
                "Netz_Export",
                bus="Wind",
                p_nom=params.netz_max_export,
                marginal_cost=-params.netz_export_erloese,  # Negativ = Erlös
                sign=-1,
                carrier="grid_export")
    
    # Wind-Eigenverbrauch (Wind-Bus -> Strom-Bus)
    network.add("Link",
                "Wind_Eigenverbrauch",
                bus0="Wind",
                bus1="Strom",
                p_nom=params.wind_nennleistung)
    
    # Wärmepumpe (Strom -> Wärme) mit zeitabhängigem COP
    network.add("Link",
                "Waermepumpe",
                bus0="Strom",
                bus1="Waerme",
                p_nom=params.wp_leistung_elektrisch,
                efficiency=cop_zeitreihe,  # Zeitabhängiger COP
                marginal_cost=0.005,  # Geringe Betriebskosten
                capital_cost=600)  # €/kW Investitionskosten
    
    # Wärmespeicher
    network.add("Store",
                "Waermespeicher",
                bus="Waerme",
                e_nom=params.waermespeicher_kapazitaet,  # kWh
                e_cyclic=True,  # Anfangs- = Endzustand
                standing_loss=0.001)  # 0.1% Verlust pro Stunde
    
    # Netz-Import (Backup, falls Wind nicht ausreicht)
    network.add("Generator",
                "Netz_Import",
                bus="Strom",
                p_nom=params.netz_max_import,
                marginal_cost=params.netz_import_kosten,
                carrier="grid")
    
    return network


def main():
    """Hauptfunktion zum Ausführen der Simulation"""
    
    print("="*80)
    print("Zukunftssystem Gewächshaus - PyPSA Optimierung mit Gurobi")
    print("="*80)
    
    # Parameter initialisieren
    params = ZukunftssystemParameter()
    
    print("\n1. Lade Daten aus CSV-Dateien...")
    
    # Heizlast laden
    print("   - Heizlast aus heizlast_2019.csv")
    heizlast_df = lade_heizlast('heizlast_2019.csv')
    
    # Strombedarf laden
    print("   - Strombedarf aus hourly_lamp_energy_2019.csv")
    strombedarf_df = lade_strombedarf('hourly_lamp_energy_2019.csv')
    
    # COP Wärmepumpe laden
    print("   - COP Wärmepumpe aus heatpump_cop_2019.csv")
    cop_df = lade_cop_waermepumpe('heatpump_cop_2019.csv')
    
    # Windleistung laden
    print("   - Windleistung aus Windanlage Leistungsdaten.csv")
    wind_df = lade_windleistung('Windanlage Leistungsdaten.csv')
    
    # Zeitindex erstellen (gemeinsame Zeitstempel aller Datenquellen)
    zeitindex = heizlast_df.index.intersection(strombedarf_df.index)
    zeitindex = zeitindex.intersection(cop_df.index)
    zeitindex = zeitindex.intersection(wind_df.index)
    
    # Nur die ersten 168 Stunden (1 Woche) für schnellere Tests
    # Kommentiere die nächste Zeile aus, um das ganze Jahr zu simulieren
    # zeitindex = zeitindex[:168]  # 1 Woche
    
    print(f"   - Simulationszeitraum: {zeitindex[0]} bis {zeitindex[-1]}")
    print(f"   - Anzahl Zeitschritte: {len(zeitindex)}")
    
    # Daten auf Simulationszeitraum einschränken
    waermebedarf = heizlast_df.loc[zeitindex, 'Heizlast_kW']
    strombedarf = strombedarf_df.loc[zeitindex, 'Energy_kW']
    cop_zeitreihe = cop_df.loc[zeitindex, 'COP']
    windleistung = wind_df.loc[zeitindex, 'Wind_kW']
    
    print("\n2. Datenübersicht...")
    print(f"   - Mittlere Heizlast: {waermebedarf.mean():.2f} kW")
    print(f"   - Maximale Heizlast: {waermebedarf.max():.2f} kW")
    print(f"   - Minimale Heizlast: {waermebedarf.min():.2f} kW")
    print(f"   - Mittlerer Strombedarf: {strombedarf.mean():.2f} kW")
    print(f"   - Maximaler Strombedarf: {strombedarf.max():.2f} kW")
    print(f"   - Mittlerer COP: {cop_zeitreihe.mean():.2f}")
    print(f"   - Mittlere Windleistung: {windleistung.mean():.2f} kW")
    print(f"   - Maximale Windleistung: {windleistung.max():.2f} kW")
    
    print("\n3. Erstelle PyPSA-Netzwerk...")
    network = erstelle_zukunftssystem(zeitindex, params, waermebedarf, strombedarf, 
                                       cop_zeitreihe, windleistung)
    print(f"   - Anzahl Busse: {len(network.buses)}")
    print(f"   - Anzahl Generatoren: {len(network.generators)}")
    print(f"   - Anzahl Links: {len(network.links)}")
    print(f"   - Anzahl Lasten: {len(network.loads)}")
    print(f"   - Anzahl Speicher: {len(network.stores)}")
    
    print("\n4. Optimiere mit Gurobi...")
    try:
        # Optimierung mit Gurobi durchführen
        network.optimize(solver_name='gurobi')
        
        print("\n" + "="*80)
        print("OPTIMIERUNGSERGEBNISSE")
        print("="*80)
        
        # Gesamtkosten
        print(f"\nGesamtkosten: {network.objective:.2f} €")
        
        # Energiebilanz Strom
        print("\n--- Strombilanz ---")
        strom_wind_gesamt = network.generators_t.p['Windkraftanlage'].sum()
        strom_wind_eigen = network.links_t.p0['Wind_Eigenverbrauch'].sum()  # Eigenverbrauch
        strom_netz_import = network.generators_t.p['Netz_Import'].sum()
        strom_netz_export = network.generators_t.p['Netz_Export'].sum()  # Exportmenge
        strom_wp = network.links_t.p0['Waermepumpe'].sum()  # Strombedarf WP
        strom_last = network.loads_t.p['Stromlast'].sum()
        
        print(f"Windkraft gesamt: {strom_wind_gesamt:>12.2f} kWh")
        print(f"  Eigenverbrauch: {strom_wind_eigen:>12.2f} kWh")
        print(f"  Netz Export:    {strom_netz_export:>12.2f} kWh")
        print(f"Netz Import:      {strom_netz_import:>12.2f} kWh")
        print(f"Wärmepumpe:       {strom_wp:>12.2f} kWh")
        print(f"Stromlast:        {strom_last:>12.2f} kWh")
        
        # Energiebilanz Wärme
        print("\n--- Wärmebilanz ---")
        waerme_wp = network.links_t.p1['Waermepumpe'].sum()
        waerme_last = network.loads_t.p['Waermelast'].sum()
        
        print(f"Wärmepumpe:       {waerme_wp:>12.2f} kWh")
        print(f"Wärmelast:        {waerme_last:>12.2f} kWh")
        
        # Kosten aufschlüsseln
        print("\n--- Kostenaufschlüsselung ---")
        kosten_import = strom_netz_import * params.netz_import_kosten
        erloese_export = strom_netz_export * params.netz_export_erloese
        
        print(f"Stromimport:      {kosten_import:>12.2f} €")
        print(f"Stromexport:     -{erloese_export:>12.2f} €")
        print(f"Netto:            {kosten_import - erloese_export:>12.2f} €")
        
        # Speicherstatus
        print("\n--- Wärmespeicher ---")
        speicher_e = network.stores_t.e['Waermespeicher']
        print(f"Durchschnitt:     {speicher_e.mean():>12.2f} kWh")
        print(f"Maximum:          {speicher_e.max():>12.2f} kWh")
        print(f"Minimum:          {speicher_e.min():>12.2f} kWh")
        
        # Autarkiegrad (Eigenverbrauch Wind / Gesamtstrombedarf)
        print("\n--- Kennzahlen ---")
        strom_verbrauch = strom_wind_eigen + strom_netz_import
        if strom_verbrauch > 0:
            autarkie_strom = (strom_wind_eigen / strom_verbrauch) * 100
        else:
            autarkie_strom = 0.0
        print(f"Stromautarkie:    {autarkie_strom:>12.2f} %")
        
        # COP: Wärmeoutput / Strominput (p1 ist negativ in PyPSA, daher abs)
        mittlerer_cop = abs(waerme_wp / strom_wp) if strom_wp > 0 else 0
        print(f"Realisierter COP: {mittlerer_cop:>12.2f}")
        
        print("\n" + "="*80)
        print("Optimierung erfolgreich abgeschlossen!")
        print("="*80)
        
        return network
        
    except Exception as e:
        print(f"\n[FEHLER] Optimierung fehlgeschlagen: {e}")
        print("\nHinweis: Stelle sicher, dass Gurobi installiert und lizenziert ist.")
        print("Alternativ kann PyPSA auch mit anderen Solvern arbeiten (z.B. 'glpk', 'cbc')")
        return None


if __name__ == "__main__":
    network = main()
