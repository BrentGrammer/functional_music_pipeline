# Mandelbrot Set Transform

## Relevant Mathematical Properties

The following properties of the Mandelbrot set are candidates for translation into musical transforms:

1. **The core iteration `z = z² + c`** — iterating a simple rule to produce complex behavior. This is directly aligned with the project's core philosophy of computational irreducibility: simple deterministic rules producing surprising, emergent results.

2. **Bounded vs. unbounded orbits** — for a given `c` value, the orbit of `z = 0` either stays bounded (c is in the Mandelbrot set) or escapes to infinity (c is not). This binary classification creates a natural boundary between order and chaos.

3. **Escape time** — *how quickly* an orbit escapes to infinity determines the "color" in standard Mandelbrot visualizations. Points near the boundary escape slowly; points far from the set escape quickly. This gradient is a rich source of continuous values that could map to musical properties (frequency, duration, amplitude).

4. **Self-similarity at different scales** — zooming into the Mandelbrot set reveals smaller copies of the overall structure ("baby Mandelbrot sets"), though each copy has subtle differences. This property could drive recursive or nested musical structures.

5. **The boundary is where complexity lives** — the most intricate, interesting behavior happens at the boundary between the set and its complement. Points near the boundary produce the most complex Julia sets. This is analogous to the "edge of chaos" concept — the region between order and randomness where the most interesting emergent behavior occurs.

6. **Each point on the Mandelbrot set corresponds to a Julia set** — the `c` value determines the shape of the Julia set for `f(z) = z² + c`. Julia sets near the boundary are fractal and complex; those from deep inside the set are simple closed curves.

7. **Period of bulbs** — each bulb on the Mandelbrot set has an associated period. The main cardioid is period-1, the large circle to its left is period-2, and so on. The number of spokes/branches on a bulb equals its period.

8. **Critical orbit** — the orbit of `z = 0` for a given `c`. If this orbit is bounded, `c` is in the set. The trajectory of this orbit (the sequence of complex values it visits) is itself a rich data source.
