# Fix the frost_effect transform for chord clusters

- The current implementation does not sound right. The cluster sounds at the beginning, but subsequent iterations play the cluster tones one after the other.
- The seed cluster sounding all at once should be preserved across iterations and the edge tones should slowly stagger and spread out around each note of the cluster.