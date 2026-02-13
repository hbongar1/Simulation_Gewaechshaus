"""
Konventionelles Gewächshaus-Modell mit PyPSA
- Verwendet Gurobi als Optimizer
- Heizlast aus heizlast_2019.csv
- Strombedarf aus hourly_lamp_energy_2019.csv
"""

import pypsa
import pandas as pd
import numpy as np

# Definition Gewächshausparameter
class GewaechshausParameter:
    def __init__(self):
        # Energiesystem-Komponenten
        self.waermespeicher_kapazitaet = 5000  # kWh
        
        # Gaskessel
        self.gaskessel_leistung = 1500  # kW
        self.gaskessel_wirkungsgrad = 0.95  # 95%


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


def erstelle_netzwerk(zeitindex, params, waermebedarf, strombedarf):
    """Erstellt das PyPSA-Netzwerk für das konventionelle Gewächshaus"""
    
    network = pypsa.Network()
    network.set_snapshots(zeitindex)

    # Busse definieren
    network.add("Bus", "Strom", carrier="strom")
    network.add("Bus", "Waerme", carrier="waerme")
    network.add("Bus", "Gas", carrier="gas")
    
    # Lasten hinzufügen
    network.add("Load", 
                "Stromlast",
                bus="Strom",
                p_set=strombedarf)
    
    network.add("Load",
                "Waermelast",
                bus="Waerme",
                p_set=waermebedarf)
    
    # Netzstrom (Import aus öffentlichem Netz)
    network.add("Generator",
                "Netz_Import",
                bus="Strom",
                p_nom=10000,  # kW - ausreichend für Spitzenlast
                marginal_cost=0.25,  # €/kWh - Strompreis
                carrier="grid")
    
    # Gasversorgung
    network.add("Generator",
                "Gas_Versorgung",
                bus="Gas",
                p_nom=5000,  # kW - ausreichend Kapazität
                marginal_cost=0.08,  # €/kWh - Gaspreis (ca. 8 ct/kWh)
                carrier="gas")
    
    # Wärmespeicher
    network.add("Store",
                "Waermespeicher",
                bus="Waerme",
                e_nom=params.waermespeicher_kapazitaet,  # kWh
                e_cyclic=True,  # Anfangs- = Endzustand
                standing_loss=0.001)  # 0.1% Verlust pro Stunde
    
    # Gaskessel (Gas -> Wärme)
    network.add("Link",
                "Gaskessel",
                bus0="Gas",
                bus1="Waerme",
                p_nom=params.gaskessel_leistung,
                efficiency=params.gaskessel_wirkungsgrad,
                marginal_cost=0.01,  # Betriebskosten
                capital_cost=100)  # Investitionskosten €/kW
    
    return network


def main():
    """Hauptfunktion zum Ausführen der Simulation"""
    
    print("="*80)
    print("Konventionelles Gewächshaus - PyPSA Optimierung mit Gurobi")
    print("="*80)
    
    # Parameter initialisieren
    params = GewaechshausParameter()
    
    print("\n1. Lade Daten aus CSV-Dateien...")
    
    # Heizlast laden
    print("   - Heizlast aus heizlast_2019.csv")
    heizlast_df = lade_heizlast('heizlast_2019.csv')
    
    # Strombedarf laden
    print("   - Strombedarf aus hourly_lamp_energy_2019.csv")
    strombedarf_df = lade_strombedarf('hourly_lamp_energy_2019.csv')
    
    # Zeitindex erstellen (gemeinsame Zeitstempel)
    zeitindex = heizlast_df.index.intersection(strombedarf_df.index)
    
    # Nur die ersten 168 Stunden (1 Woche) für schnellere Tests
    # Kommentiere die nächste Zeile aus, um das ganze Jahr zu simulieren
    zeitindex = zeitindex[:168]  # 1 Woche
    
    print(f"   - Simulationszeitraum: {zeitindex[0]} bis {zeitindex[-1]}")
    print(f"   - Anzahl Zeitschritte: {len(zeitindex)}")
    
    # Daten auf Simulationszeitraum einschränken
    waermebedarf = heizlast_df.loc[zeitindex, 'Heizlast_kW']
    strombedarf = strombedarf_df.loc[zeitindex, 'Energy_kW']
    
    print("\n2. Datenübersicht...")
    print(f"   - Mittlere Heizlast: {waermebedarf.mean():.2f} kW")
    print(f"   - Maximale Heizlast: {waermebedarf.max():.2f} kW")
    print(f"   - Minimale Heizlast: {waermebedarf.min():.2f} kW")
    print(f"   - Mittlerer Strombedarf: {strombedarf.mean():.2f} kW")
    print(f"   - Maximaler Strombedarf: {strombedarf.max():.2f} kW")
    
    print("\n3. Erstelle PyPSA-Netzwerk...")
    network = erstelle_netzwerk(zeitindex, params, waermebedarf, strombedarf)
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
        strom_netz = network.generators_t.p['Netz_Import'].sum()
        strom_last = network.loads_t.p['Stromlast'].sum()
        
        print(f"Netzbezug:        {strom_netz:>12.2f} kWh")
        print(f"Stromlast:        {strom_last:>12.2f} kWh")
        
        # Energiebilanz Wärme
        print("\n--- Wärmebilanz ---")
        waerme_kessel = network.links_t.p1['Gaskessel'].sum()
        waerme_last = network.loads_t.p['Waermelast'].sum()
        
        print(f"Gaskessel Wärme:  {waerme_kessel:>12.2f} kWh")
        print(f"Wärmelast:        {waerme_last:>12.2f} kWh")
        
        # Gasverbrauch
        print("\n--- Gasverbrauch ---")
        gas_kessel = network.links_t.p0['Gaskessel'].sum()
        
        print(f"Gas Kessel:       {gas_kessel:>12.2f} kWh")
        
        # Kosten aufschlüsseln
        print("\n--- Kostenaufschlüsselung ---")
        kosten_strom = strom_netz * 0.25
        kosten_gas = gas_kessel * 0.08
        
        print(f"Stromkosten:      {kosten_strom:>12.2f} €")
        print(f"Gaskosten:        {kosten_gas:>12.2f} €")
        print(f"Summe:            {kosten_strom + kosten_gas:>12.2f} €")
        
        # Speicherstatus
        print("\n--- Wärmespeicher ---")
        speicher_e = network.stores_t.e['Waermespeicher']
        print(f"Durchschnitt:     {speicher_e.mean():>12.2f} kWh")
        print(f"Maximum:          {speicher_e.max():>12.2f} kWh")
        print(f"Minimum:          {speicher_e.min():>12.2f} kWh")
        
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



