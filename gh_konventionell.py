import pypsa
import pandas as pd
import numpy as np

# Definition Gewächshausparameter
class GewaechshausParameter:
    def __init__(self):
        # Geometrie
        self.flaeche = 10000  # m² (1 Hektar)
        self.hoehe = 4.5  # m
        self.volumen = self.flaeche * self.hoehe  # m³
        
        # Thermische Eigenschaften
        self.u_wert = 3.5  # W/(m²·K) - Wärmedurchgangskoeffizient
        
        # Solltemperaturen
        self.temp_soll_tag = 22  # °C
        self.temp_soll_nacht = 18  # °C
        
        # Beleuchtung
        self.beleuchtung_leistung = 100  # W/m²
        self.beleuchtung_stunden_winter = 14  # h/Tag
        self.beleuchtung_stunden_sommer = 8  # h/Tag
        
        # Energiesystem-Komponenten
        self.waermespeicher_kapazitaet = 5000  # kWh
        
        # BHKW (Blockheizkraftwerk / KWK)
        self.bhkw_leistung_elektrisch = 200  # kW
        self.bhkw_wirkungsgrad_elektrisch = 0.38  # 38%
        self.bhkw_wirkungsgrad_thermisch = 0.52  # 52%
        
        # Gaskessel
        self.gaskessel_leistung = 400  # kW
        self.gaskessel_wirkungsgrad = 0.95  # 95%

def erstelle_netzwerk(zeitindex, params, waermebedarf, strombedarf):

    network = pypsa.Network()

    network.add("Bus", "Strom", carrier="AC")
    network.add("Bus", "Waerme", carrier="heat")
    network.add("Bus", "Gas", carrier="gas")
    

    network.add("Load", "Stromlast", bus="Strom", p_set=strombedarf)
    network.add("Load", "Waermelast", bus="Waerme", p_set=waermebedarf)
    
    # Netzstrom
    network.add("Generator",
                "Netz_Import",
                bus="Strom",
                p_nom=1000,  # kW
                marginal_cost=0.25,  # €/kWh
                carrier="grid")
    
    # Gasversorgung
    network.add("Generator",
                "Gas_Versorgung",
                bus="Gas",
                p_nom=1500,  # kW
                marginal_cost=0.08,  # €/kWh
                carrier="gas")
    
    # Wärmespeicher
    network.add("Store",
                "Waermespeicher",
                bus="Waerme",
                e_nom=params.waermespeicher_kapazitaet,
                e_cyclic=True,
                standing_loss=0.01)
    
    # BHKW (Gas -> Strom + Wärme)
    network.add("Link",
                "BHKW",
                bus0="Gas",
                bus1="Strom",
                bus2="Waerme",
                p_nom=params.bhkw_leistung_elektrisch / params.bhkw_wirkungsgrad_elektrisch,
                efficiency=params.bhkw_wirkungsgrad_elektrisch,
                efficiency2=params.bhkw_wirkungsgrad_thermisch,
                marginal_cost=0.02,
                capital_cost=800)
    
    # Gaskessel (Gas -> Wärme)
    network.add("Link",
                "Gaskessel",
                bus0="Gas",
                bus1="Waerme",
                p_nom=params.gaskessel_leistung,
                efficiency=params.gaskessel_wirkungsgrad,
                marginal_cost=0.01,
                capital_cost=100)    
    return network
