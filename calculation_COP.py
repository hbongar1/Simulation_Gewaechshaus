import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

#Datentypen Einlesen Temperatur und Solareinstrahlung
df_data_solar = pd.read_excel('Solareinstrahlung Bochum.xlsx')
df_data_temp = pd.read_excel('Köln Temp.xlsx')

#Code für Heizlastberechnung
T_i= 20                         #Temperatur im Gewächshaus °C
A= 10000                        #Außenfläche m°2
U= 4                            #U-Wert inklusive latenter Wärme m^2*K*W^-1
V= 30000                        #Luftvolumenn m^3
n= 0.5                          #Luftwechsel 1/h
#T_a = [-10, -9, -8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]                 #Außentemperatur °C eig importiert als Liste 

T_a = df_data_temp['TT_TU']/10
#G_series=None                  #Solarstrahlung
G_series = df_data_solar['FG_LBERG']/100
eta_solar=0.8                   #Wert liegt etwa zwischen 0.75 und 0.9 
cp_luft= 0.33333                # Spezifische Wärmekapazität Luft Wh/K*m^3

#Solareinstrahlung umrechnen
for i in range(len(G_series)):
    if G_series[i] < 0:
        G_series[i] = 0
    solar_clean=G_series[i]*10000/3600


def simulate_heating_load(
    T_i,
    A,
    U,
    V,
    n,
    T_a,
    cp_luft,
    G_series=None,
    eta_solar=0.0
    ):

    #Stündliche Heizlastsimulation

    Q_dot = []

    for t in range(len(G_series)):              #eig nicht an G_series orientieren weil falsch
        T_e = T_a[t]

        Q_trans = (A*(T_i-T_a[t])/U)
        Q_luft = (V*(T_i-T_a[t])*n*cp_luft)
    
        Q_solar = 0.0
        Q_solar = solar_clean[t] * A * eta_solar

        Q = Q_trans + Q_luft - Q_solar
        Q_dot.append(max(Q, 0))  # keine Kühlung

    return np.array(Q_dot)


# Funktion auslösen
Q_dot = simulate_heating_load(
    T_i=T_i,
    A=A,
    U=U,
    V=V,
    n=n,
    T_a=T_a,
    cp_luft=cp_luft,
    G_series=G_series,
    eta_solar=eta_solar
)

#Graph erstellen
plt.plot(G_series)
plt.xlabel("Index")
plt.ylabel("Q_dot")
plt.show()
