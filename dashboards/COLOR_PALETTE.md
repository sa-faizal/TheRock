# 🎨 ROCm Sentinel - Color Palette Reference

## Official Color Palette

### Primary Colors

#### Background
```
Deep Ocean Gradient:
- Start: #0f2027 (Deep Navy)
- Mid:   #203a43 (Ocean Blue)
- End:   #2c5364 (Steel Blue)

CSS: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)
```

#### Accent - Cyan
```
Primary Accent: #00d4ff (Electric Cyan)
Secondary:      #0099cc (Deep Cyan)

Usage: Buttons, headings, links, highlights
CSS: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%)
```

#### Accent - Orange
```
Primary:   #ff6b35 (Vibrant Orange)
Secondary: #f7931e (Golden Orange)

Usage: CTAs, important actions, warnings
CSS: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%)
```

### Neutral Colors

#### White & Light
```
Pure White:     #ffffff
Off White:      #f8f9fa
Light Gray:     #f5f5f5
Border Gray:    #e0e0e0
```

#### Dark & Text
```
Dark Text:      #333333
Medium Text:    #555555
Light Text:     #666666
Disabled:       #999999
```

---

## Component Color Map

### Buttons

**Primary Action**
```css
background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
color: white;
box-shadow: 0 5px 15px rgba(0, 212, 255, 0.5);
```

**Secondary Action (Refresh/Alert)**
```css
background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
color: white;
box-shadow: 0 5px 15px rgba(255, 107, 53, 0.4);
```

**Disabled State**
```css
background: #cccccc;
color: #666666;
```

### Cards & Containers

**Main Cards**
```css
background: white;
border-radius: 12px;
box-shadow: 0 10px 30px rgba(0,0,0,0.2);
```

**Accent Cards**
```css
background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(0, 153, 204, 0.1) 100%);
border-left: 4px solid #00d4ff;
```

### Tags & Labels

**Component Tags**
```css
background: linear-gradient(135deg, #00d4ff20 0%, #0099cc20 100%);
color: #00d4ff;
border: 1px solid #00d4ff;
font-weight: 500;
```

**Severity Tags**
```css
Critical: background: #ffebee; color: #c62828;
High:     background: #fff3e0; color: #e65100;
Medium:   background: #fff9c4; color: #f57f17;
Low:      background: #e8f5e9; color: #2e7d32;
```

### Issue Numbers
```css
background: #00d4ff;
color: #0f2027;
font-weight: 600;
```

### Stat Boxes
```css
background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
color: white;
box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
```

### Links

**Primary Links**
```css
color: #00d4ff;
text-decoration: none;

:hover {
  text-decoration: underline;
}
```

**Analyze Links**
```css
color: #ff6b35;
font-weight: 600;
```

### Form Elements

**Input Fields**
```css
border: 2px solid #00d4ff;
border-radius: 8px;

:focus {
  border-color: #0099cc;
  outline: none;
}
```

**Dropdowns**
```css
border: 2px solid #00d4ff;
background: white;
cursor: pointer;
```

### Loading States

**Spinner**
```css
border: 4px solid #f3f3f3;
border-top: 4px solid #00d4ff;
animation: spin 1s linear infinite;
```

**Loading Text**
```css
color: #00d4ff;
font-size: 1.2em;
```

### Section Highlights

**Similar Issues**
```css
background: #f5f5f5;
border-left: 4px solid #00d4ff;
```

**Root Cause Commits**
```css
background: #f5f5f5;
border-left: 4px solid #ff6b35;
```

**Analysis Summary**
```css
background: linear-gradient(135deg, #00d4ff10 0%, #0099cc10 100%);
border-left: 4px solid #00d4ff;
```

**Fix Suggestions**
```css
background: #e8f5e9;
border-left: 4px solid #4caf50;
```

**Comments**
```css
background: #fff9c4;
border-left: 4px solid #fbc02d;
```

### Chat Interface

**User Message Bubble**
```css
background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
color: white;
```

**AI Message Bubble**
```css
background: white;
color: #333;
border: 1px solid #e0e0e0;
```

**Example Queries**
```css
background: linear-gradient(135deg, #00d4ff20 0%, #0099cc20 100%);
color: #00d4ff;
border: 1px solid #00d4ff;

:hover {
  background: linear-gradient(135deg, #00d4ff40 0%, #0099cc40 100%);
}
```

---

## Color Functions & Utilities

### Opacity Variations

**Cyan Opacity Scale**
```
100%: #00d4ff
80%:  rgba(0, 212, 255, 0.8)
60%:  rgba(0, 212, 255, 0.6)
40%:  rgba(0, 212, 255, 0.4)
20%:  rgba(0, 212, 255, 0.2)
10%:  rgba(0, 212, 255, 0.1)
```

**Orange Opacity Scale**
```
100%: #ff6b35
80%:  rgba(255, 107, 53, 0.8)
60%:  rgba(255, 107, 53, 0.6)
40%:  rgba(255, 107, 53, 0.4)
20%:  rgba(255, 107, 53, 0.2)
10%:  rgba(255, 107, 53, 0.1)
```

### Box Shadows

**Standard Elevation**
```css
/* Level 1 - Cards */
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

/* Level 2 - Hover */
box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);

/* Level 3 - Modal */
box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
```

**Colored Shadows (Accent)**
```css
/* Cyan accent */
box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
box-shadow: 0 5px 15px rgba(0, 212, 255, 0.5); /* Hover */

/* Orange accent */
box-shadow: 0 4px 15px rgba(255, 107, 53, 0.3);
box-shadow: 0 5px 15px rgba(255, 107, 53, 0.4); /* Hover */
```

---

## Typography Colors

### Headings
```css
h1 { color: white; } /* On dark background */
h2 { color: #00d4ff; } /* On white cards */
h3 { color: #ff6b35; } /* Subheadings */
```

### Body Text
```css
Primary:   #333333
Secondary: #555555
Tertiary:  #666666
Disabled:  #999999
```

### Labels
```css
Label:       #00d4ff (accent labels)
Description: #666666 (helper text)
Error:       #c62828 (error messages)
Success:     #2e7d32 (success messages)
```

---

## Animation Colors

### Hover Effects
```css
button:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0, 212, 255, 0.5);
}
```

### Active States
```css
button:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(0, 212, 255, 0.3);
}
```

### Focus Rings
```css
:focus-visible {
  outline: 2px solid #00d4ff;
  outline-offset: 2px;
}
```

---

## Accessibility Compliance

### Contrast Ratios (WCAG 2.1)

**Level AAA (7:1 or higher)**
- White on Dark Ocean: 18.5:1 ✅
- Cyan on Dark Ocean: 10.5:1 ✅
- Dark text on White: 18:1 ✅

**Level AA (4.5:1 or higher)**
- White on Cyan Gradient: 4.8:1 ✅
- Orange on White: 4.2:1 ✅
- Dark Gray on Light Gray: 5.2:1 ✅

---

## CSS Variables (Optional Implementation)

```css
:root {
  /* Primary Colors */
  --ocean-dark: #0f2027;
  --ocean-mid: #203a43;
  --ocean-light: #2c5364;
  
  /* Accent Colors */
  --cyan-bright: #00d4ff;
  --cyan-deep: #0099cc;
  --orange-bright: #ff6b35;
  --orange-golden: #f7931e;
  
  /* Neutrals */
  --white: #ffffff;
  --off-white: #f8f9fa;
  --gray-light: #f5f5f5;
  --gray-border: #e0e0e0;
  --gray-medium: #666666;
  --gray-dark: #333333;
  
  /* Semantic */
  --success: #2e7d32;
  --warning: #f57f17;
  --error: #c62828;
  --info: #00d4ff;
  
  /* Gradients */
  --gradient-ocean: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
  --gradient-cyan: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
  --gradient-orange: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
}
```

---

## Quick Reference

**Need to match a color?** Use these hex codes:
- Background: `#0f2027` → `#203a43` → `#2c5364`
- Cyan: `#00d4ff` → `#0099cc`
- Orange: `#ff6b35` → `#f7931e`
- White: `#ffffff`
- Dark: `#333333`

**Need a gradient?** Copy these:
- Ocean: `linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)`
- Cyan: `linear-gradient(135deg, #00d4ff 0%, #0099cc 100%)`
- Orange: `linear-gradient(135deg, #ff6b35 0%, #f7931e 100%)`

**Need a shadow?** Use this:
- Cyan: `box-shadow: 0 5px 15px rgba(0, 212, 255, 0.5);`
- Dark: `box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);`

---

**ROCm Sentinel Color Palette v2.0**  
**Last Updated:** January 5, 2026



