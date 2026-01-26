import pypsa
import pandas as pd
import numpy as np


class ZukunftssystemParameter:
    def __init__(self):
        # Geometrie Gewächshaus
        self.flaeche = 10000  # m² (1 Hektar)
        self.hoehe = 4.5  # m
        self.volumen = self.flaeche * self.hoehe  # m³
        
        # Thermische Eigenschaften
        self.u_wert = 3.5  # W/(m²·K) - Wärmedurchgangskoeffizient
        
        # Solltemperaturen
        self.temp_soll_tag = 22  # °C
        self.temp_soll_nacht = 18  # °C
        
        # Windkraftanlage
        self.wind_nennleistung = 500  # kW - Anpassen an deine Anlage!
        
        # Wärmepumpe
        self.wp_leistung_elektrisch = 100  # kW
        self.wp_temp_vorlauf = 35  # °C - Vorlauftemperatur
        self.wp_eta_carnot = 0.45  # Carnot-Wirkungsgrad
        
        # Batteriespeicher
        self.batterie_kapazitaet = 1000  # kWh
        self.batterie_wirkungsgrad_laden = 0.95
        self.batterie_wirkungsgrad_entladen = 0.95
        
        # Wärmespeicher
        self.waermespeicher_kapazitaet = 5000  # kWh
        
        # Netzinteraktion
        self.netz_import_kosten = 0.25  # €/kWh
        self.netz_export_erloese = 0.08  # €/kWh
        self.netz_max_import = 1000  # kW
        self.netz_max_export = 1000  # kW


def lade_windertragsdaten(datei_pfad, params):
    """
    Lädt Windertragsdaten von Renewables.ninja (CSV oder Excel)
    
    Parameters:
    - datei_pfad: Pfad zur Datei (CSV oder Excel)
    - params: ZukunftssystemParameter-Objekt
    
    Returns:
    - Array mit Windleistung in kW
    
    Erwartet:
    - Spalte 'electricity' mit Werten zwischen 0 und 1 (Capacity Factor)
    - Alternativ: Direkte kW-Werte
    """
    # Dateiendung prüfen
    if datei_pfad.endswith('.csv'):
        df = pd.read_csv(datei_pfad)
    elif datei_pfad.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(datei_pfad)
    else:
        raise ValueError("Datei muss CSV oder Excel sein (.csv, .xlsx, .xls)")
    
    # Capacity Factor Spalte finden (typisch bei Renewables.ninja)
    if 'electricity' in df.columns:
        # Capacity Factor * Nennleistung = kW
        windleistung = df['electricity'].values * params.wind_nennleistung
    elif 'capacity_factor' in df.columns:
        windleistung = df['capacity_factor'].values * params.wind_nennleistung
    elif 'power' in df.columns or 'Power' in df.columns:
        # Direkt kW-Werte
        spalte = 'power' if 'power' in df.columns else 'Power'
        windleistung = df[spalte].values
    else:
        # Erste numerische Spalte verwenden
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            windleistung = df[numeric_cols[0]].values * params.wind_nennleistung
        else:
            raise ValueError("Keine geeignete Spalte gefunden. Erwartet: 'electricity', 'capacity_factor' oder 'power'")
    
    return windleistung


def berechne_waermebedarf(temp_aussen, params):
    """
    Berechnet den Wärmebedarf des Gewächshauses
    
    Parameters:
    - temp_aussen: Außentemperatur in °C (Array)
    - params: ZukunftssystemParameter-Objekt
    
    Returns:
    - Wärmebedarf in kW (Array)
    """
    # Durchschnittliche Solltemperatur (vereinfacht)
    temp_soll = params.temp_soll_tag  # °C
    
    # Temperaturdifferenz
    delta_T = temp_soll - temp_aussen
    
    # Wärmeverluste durch Transmission: Q = U * A * ΔT
    waermeverlust = params.u_wert * params.flaeche * delta_T / 1000  # in kW
    
    # Nur positive Werte (keine "negative Heizung")
    waermeverlust = np.maximum(waermeverlust, 0)
    
    return waermeverlust


def lade_temperaturdaten(datei_pfad):
    """
    Lädt Temperaturdaten aus CSV
    
    Returns:
    - DataFrame mit Temperaturdaten
    """
    df = pd.read_csv(datei_pfad, sep=';', decimal=',')
    
    # Temperatur in float konvertieren
    if 'TT_TU' in df.columns:
        df['TT_TU'] = df['TT_TU'].astype(float)
    
    return df


def lade_cop_daten(datei_pfad):
    """
    Lädt COP-Daten aus CSV
    
    Returns:
    - Array mit COP-Werten
    """
    df = pd.read_csv(datei_pfad, sep=';', decimal=',')
    
    if 'COP' in df.columns:
        cop = df['COP'].astype(float).values
    else:
        # Falls keine COP-Spalte, Standard-COP verwenden
        cop = np.full(len(df), 3.0)
    
    return cop


def lade_lampendaten(datei_pfad):
    """
    Lädt Lampenenergiedaten aus CSV
    
    Returns:
    - Array mit Energieverbrauch in kWh
    """
    df = pd.read_csv(datei_pfad, sep=';')
    
    if 'Energy_Wh' in df.columns:
        energie_kwh = df['Energy_Wh'].astype(float).values / 1000  # Wh -> kWh
    else:
        energie_kwh = np.zeros(len(df))
    
    return energie_kwh



def erstelle_zukunftssystem(zeitindex, params, 
                             temp_aussen, 
                             windleistung,
                             cop_zeitreihe,
                             lampenbedarf):
                             
    network = pypsa.Network()
    network.set_snapshots(zeitindex)
    
    network.add("Bus", "Strom", carrier="AC")
    network.add("Bus", "Waerme", carrier="heat")
    
    # Wärmebedarf (dynamisch basierend auf Außentemperatur)
    waermebedarf = berechne_waermebedarf(temp_aussen, params)
    network.add("Load", "Waermelast", bus="Waerme", p_set=waermebedarf)
    
    # Strombedarf (Lampen + konstante Verbraucher)
    strombedarf_konstant = 5  # kW (Pumpen, Lüftung, etc.)
    strombedarf_gesamt = lampenbedarf + strombedarf_konstant
    network.add("Load", "Stromlast", bus="Strom", p_set=strombedarf_gesamt)


    # Windkraftanlage
    
    # p_max_pu: Verfügbarkeit als Anteil der Nennleistung (0 bis 1)
    p_max_pu = windleistung / params.wind_nennleistung
    # Auf [0, 1] begrenzen
    p_max_pu = np.clip(p_max_pu, 0, 1)
    
    network.add("Generator",
                "Windkraftanlage",
                bus="Strom",
                p_nom=params.wind_nennleistung,
                p_max_pu=p_max_pu,
                marginal_cost=0.01,  # Minimale Wartungskosten
                capital_cost=1200,  # €/kW
                carrier="wind")
    


    #Wärmepumpe
    # Wärmepumpe als Link mit zeitabhängiger Effizienz
    network.add("Link",
                "Waermepumpe",
                bus0="Strom",
                bus1="Waerme",
                p_nom=params.wp_leistung_elektrisch,
                efficiency=cop_zeitreihe,  # Zeitabhängiger COP
                marginal_cost=0.005,
                capital_cost=600)  # €/kW
       
    # Batteriespeicher
    network.add("Store",
                "Batterie",
                bus="Strom",
                e_nom=params.batterie_kapazitaet,
                e_cyclic=True,
                standing_loss=0.001,  # 0.1% pro Stunde
                capital_cost=400)  # €/kWh
    
    # Wärmespeicher
    network.add("Store",
                "Waermespeicher",
                bus="Waerme",
                e_nom=params.waermespeicher_kapazitaet,
                e_cyclic=True,
                standing_loss=0.01,  # 1% pro Stunde
                capital_cost=50)  # €/kWh
    
    # Netz-Import (Strom kaufen)
    network.add("Generator",
                "Netz_Import",
                bus="Strom",
                p_nom=params.netz_max_import,
                marginal_cost=params.netz_import_kosten,
                carrier="grid")
    
    # Netz-Export (Strom verkaufen) - als negative Last modelliert
    network.add("Generator",
                "Netz_Export",
                bus="Strom",
                p_nom=params.netz_max_export,
                marginal_cost=-params.netz_export_erloese,  # Negativ = Erlös
                carrier="grid_export")
    
    return network
