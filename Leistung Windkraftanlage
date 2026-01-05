import numpy as np

# Definition Kennwerte

luftdruck = 1000                                                          # Luftdruck in Pa hängt auch von Höhe des Windrads und der Höhe gegenüber des Meeresspiegels ab, wie genau soll der Wert sein?
gaskonstante = 287.05                                                     
temperatur_celsis = 20  
temperatur_kelvin = temperatur_celsis + 273.15
dichte_Luft = luftdruck / (gaskonstante * temperatur_kelvin)              

Leistungsbeiwert = 0.5                                                    # Realistischer Wert bei guten Anlagen oder cp hänt auch von Windgeschwindkeit ab, aber keine Formel findbar

durchmesser_rotorkreis = 120                                              # Variiert stark nach Modell
rotorflaeche = (np.pi * durchmesser_rotorkreis ** 2)/4                    # Formel Rotorfläche (Formel Für Flächeninhalt Kreis)

windgeschwindigkeit = 4                                                   # Variiert stark

# Entnommene Leistung aus dem Wind
entnommene_Leistung_Wind = Leistungsbeiwert * 1/2 * dichte_Luft * rotorflaeche * windgeschwindigkeit**3   

# Einschalt- und Abschaltgeschwingkeit
if windgeschwindigkeit < 3:
    entnommene_Leistung_Wind = 0
elif windgeschwindigkeit > 20:
    entnommene_Leistung_Wind = 0

print(entnommene_Leistung_Wind)
 
