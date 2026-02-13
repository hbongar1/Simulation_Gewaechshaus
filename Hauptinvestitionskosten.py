def hik_eur_per_kw(P_MW: float, SFL_W_per_m2: float, NH_m: float) -> float:
    '''
    Berechnet die spezifischen Hauptinvestitionskosten (HIK) in €/kW
    basierend auf einer Regressionsformel.

    Parameter
    ----------
    P : float
        Nennleistung in MW
    SFL : float
        Spezifische Flächenleistung in W/m², also Verhältnis von Nennleistung zu Rotorkreisfläche in Watt pro Quadratmeter (W/m²)
    NH : float
        Nabenhöhe in m

    Returns
    -------
    float
        HIK in €/kW
    '''
    # einfache Plausibilitätschecks
    if P <= 0:
        raise ValueError("P_MW muss > 0 sein.")
    if SFL <= 0:
        raise ValueError("SFL_W_per_m2 muss > 0 sein.")
    if NH <= 0:
        raise ValueError("NH_m muss > 0 sein.")

    hik = 1743.95 - 81.21 * P - 1.66 * SFL + 2.91 * NH
    cost_wea = hik*P_MW*1000
    return hik, cost_wea


P = 4.2
SFL = 283
NH = 120.0

hik, cost_wea = hik_eur_per_kw(P, SFL, NH)

print(f"HIK = {hik:.2f} €/kW")
print(f"Kosten WEA = {cost_wea:,.0f} €")
