import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(1, 100, 100)
y = x  # grows fast

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Linear scale
axes[0].plot(x, y)
axes[0].set_title("Linear Y-axis")

# Log scale
axes[1].plot(x, y)
axes[1].set_yscale("log", base=2)
axes[1].set_title("Logarithmic Y-axis")

plt.show()
