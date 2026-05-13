# Feigenbaum-Inspired Musical Transformation

## Core Musical Insight
Create evolving tone relationships that exhibit:
1. **Period Doubling** - Parameters change in ratios approaching δ≈4.669
2. **Increasing Complexity** - Simple → complex → controlled chaos
3. **Self-Similarity** - Preserve harmonic relationships through transformations

## Simplified Implementation

### 1. Transform Algorithm
```python
def feigenbaum_transform(tones: List[Tone], 
                        iterations: int = 4,
                        ratio: float = 4.669) -> List[Tone]:
    """
    Applies period-doubling transformations to create evolving tones.
    Each iteration adds complexity while preserving harmonic relationships.
    """
    MIN_FREQUENCY_HZ = 20       # Lower human hearing threshold
    MAX_FREQUENCY_HZ = 20000    # Upper human hearing threshold
    MAX_OCTAVE_DIVERGENCE = 8   # Maximum harmonic spread (3 octaves)
    
    transformed = []
    fundamental = tones[0].frequency  # Reference for harmonic preservation
    
    for tone in tones:
        current_freq = tone.frequency
        current_dur = tone.duration
        
        for i in range(iterations):
            # Create two variants per iteration
            var1 = current_freq * (ratio / (1 + i))
            var2 = current_freq / (ratio / (1 + i))
            
            # Maintain audible range and harmonicity
            var1 = min(max(var1, MIN_FREQUENCY_HZ), MAX_FREQUENCY_HZ)
            var2 = min(max(var2, MIN_FREQUENCY_HZ), MAX_FREQUENCY_HZ)
            
            if var1 / fundamental > MAX_OCTAVE_DIVERGENCE:
                var1 = fundamental * (2 ** int(math.log(var1/fundamental, 2)))
            
            transformed.append(Tone(
                frequency=(var1 + var2)/2,  # Center frequency
                duration=current_dur * (ratio**(-i/2)),  # Slow evolution
                amplitude=tone.amplitude * (0.9**i)  # Natural decay
            ))
    
    return transformed
```

### 2. Musical Parameters
- **Iterations**: Complexity levels (1-6, default 4)
- **Ratio**: Characteristic doubling ratio (4.0-5.0, default 4.669)
- **Automatic Limits**: 20Hz-20kHz range, 3 octave max divergence


### 4. Testing Strategy
1. **Harmonic Preservation** - Transformed tones relate to original frequencies
2. **Progressive Complexity** - Each iteration doubles tone variants
3. **Dynamic Range** - Output stays within 20Hz-20kHz
4. **Musicality** - Manual listening tests verify pleasant evolution

## Implementation Phases
1. Core transformation algorithm
2. CLI argument parsing
3. Range limiting and harmonic correction
4. Documentation with audio examples

## Key Advantages
- **Musical Focus** - Prioritizes audible texture over mathematical purity
- **Self-Contained** - No complex parameter tuning needed
- **Safe Exploration** - Hard limits prevent harsh sounds
- **Explainable** - Clear "iterations" parameter maps to audible complexity
