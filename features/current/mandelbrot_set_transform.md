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

## Mapping Complex Numbers to Music

A complex number has two orthogonal components — real and imaginary — that together define a point in a 2D space. A Tone in this project has three independent properties: **frequency**, **duration**, and **amplitude**. We need a pair that behaves like the real and imaginary axes.

### Proposed mapping: Duration ↔ Real, Frequency ↔ Imaginary

- **Duration is linear**, like the real number line. Time flows forward; durations add together straightforwardly. It is the concrete, directly measurable dimension.

- **Frequency is cyclic**, like the imaginary axis. The key property of the imaginary unit *i* is that it causes **rotation** in the complex plane — multiplying by *i* rotates 90°, and multiplying by *i⁴* returns to the start. Pitch is fundamentally rotational: **octave equivalence** means A4 and A5 are "the same note" in a sense. The pitch space wraps around. Frequency ratios, not differences, determine musical intervals, which is inherently multiplicative — just like how complex multiplication works.

- In **standard musical notation**, this mapping is literally visual: time flows on the horizontal axis (real) and pitch lives on the vertical axis (imaginary).

- There is also a philosophical fit: the real part is what you can directly count and measure linearly. The imaginary part is the dimension that *shouldn't exist* but turns out to be essential — and arguably pitch, with its strange octave periodicity and logarithmic perception, has that quality.

### Amplitude as magnitude

**Amplitude** could serve as a third dimension, mapping to the **magnitude** `|z| = √(real² + imag²)` of the complex number. This represents the "energy" or intensity of the point — how far it is from the origin. In the Mandelbrot iteration, the magnitude determines whether an orbit escapes (diverges beyond the escape radius) or stays bounded.
