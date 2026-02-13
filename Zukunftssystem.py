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
        
        # Wärmespeicher
        self.waermespeicher_kapazitaet = 5000  # kWh
        
        # Netzinteraktion
        self.netz_import_kosten = 0.25  # €/kWh
        self.netz_export_erloese = 0.08  # €/kWh
        self.netz_max_import = 1000  # kW
        self.netz_max_export = 1000  # kW

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
    
    # Netz-Export (Strom verkaufen)
    network.add("Generator",
                "Netz_Export",
                bus="Strom",
                p_nom=params.netz_max_export,
                marginal_cost=-params.netz_export_erloese,  # Negativ = Erlös
                carrier="grid_export")
    
    return network
