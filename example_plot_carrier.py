import pypsa
import pandas as pd

import matplotlib.pyplot as plt

# 1. Setup (Simuliert, was in deinem Skript passiert)
network = pypsa.Network()
index = pd.date_range("2019-01-01", periods=24, freq="h")
network.set_snapshots(index)

# Busse mit Carriers
network.add("Bus", "StromBus", carrier="AC")
network.add("Bus", "GasBus", carrier="gas")

# Generatoren mit Carriers
network.add("Generator", "Windrad", bus="StromBus", p_nom=10, marginal_cost=0, carrier="wind", p_max_pu=[0.8]*24)
network.add("Generator", "GasKessel", bus="GasBus", p_nom=20, marginal_cost=50, carrier="gas")
network.add("Generator", "StromNetz", bus="StromBus", p_nom=100, marginal_cost=100, carrier="grid")

# Last
network.add("Load", "HausLast", bus="StromBus", p_set=5)

# 2. Lösen
network.optimize(solver_name='gurobi') # oder glpk

# 3. Plotten nach Carrier
# Hier siehst du, warum 'carrier' nützlich ist: Wir gruppieren danach!
p_generation = network.generators_t.p  # Erzeugung aller Generatoren
p_by_carrier = p_generation.T.groupby(network.generators.carrier).sum().T

# Plot
fig, ax = plt.subplots(figsize=(10, 5))
p_by_carrier.plot.area(ax=ax, alpha=0.7)

ax.set_title("Erzeugung nach Energieträger (Carrier)")
ax.set_ylabel("Leistung [MW]")
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("beispiel_plot_carrier.png")
print("Plot gespeichert: beispiel_plot_carrier.png")
