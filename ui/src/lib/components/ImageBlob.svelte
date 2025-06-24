<script lang="ts">
  interface Props {
    imageName: string;
    borderRadius: string;
    bgPosition?: string;
    bgSize?: string;
  }
  
  let { imageName, borderRadius, bgPosition = "bg-center", bgSize = "bg-cover" }: Props = $props();
  
  // Parse border-radius and create variations
  function createMorphingVariations(radius: string) {
    // Handle elliptical border-radius format: "60% 40% 80% 20% / 25% 75% 35% 65%"
    const parts = radius.split('/');
    const horizontal = parts[0].trim().split(/\s+/);
    const vertical = parts[1] ? parts[1].trim().split(/\s+/) : horizontal;
    
    // Create variation multipliers for each keyframe
    const variations = [
      [1.0, 1.0, 1.0, 1.0], // 0%, 100% - original
      [0.9, 1.1, 0.8, 1.2], // 25%
      [1.1, 0.9, 1.2, 0.8], // 50%
      [0.8, 1.2, 1.1, 0.9]  // 75%
    ];
    
    return variations.map(multipliers => {
      const newHorizontal = horizontal.map((val, i) => {
        const numVal = parseFloat(val);
        const unit = val.replace(/[\d.]/g, '');
        return `${(numVal * multipliers[i % 4]).toFixed(1)}${unit}`;
      });
      
      const newVertical = vertical.map((val, i) => {
        const numVal = parseFloat(val);
        const unit = val.replace(/[\d.]/g, '');
        return `${(numVal * multipliers[i % 4]).toFixed(1)}${unit}`;
      });
      
      return parts[1] ? `${newHorizontal.join(' ')} / ${newVertical.join(' ')}` : newHorizontal.join(' ');
    });
  }
  
  const morphVariations = createMorphingVariations(borderRadius);
</script>

<style>
  .morphing-blob {
    animation: morph 15s ease-in-out infinite;
  }
  
  @keyframes morph {
    0%, 100% {
      border-radius: var(--morph-0);
    }
    25% {
      border-radius: var(--morph-1);
    }
    50% {
      border-radius: var(--morph-2);
    }
    75% {
      border-radius: var(--morph-3);
    }
  }
</style>

<div
  class="h-full w-full {bgSize} {bgPosition} morphing-blob drop-shadow-xl drop-shadow-muted"
  style="--morph-0: {morphVariations[0]}; --morph-1: {morphVariations[1]}; --morph-2: {morphVariations[2]}; --morph-3: {morphVariations[3]}; background-image: url(/{imageName})">
</div>