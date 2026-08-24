from pylmgc90 import pre
import numpy as np

radii = pre.granulo_Random(1, 0.05, 0.1)
print("granulo_Random OK", radii)

result = pre.depositInBox2D(radii, 4.0, 4.0)
print("deposit OK", result)