# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

This is a Progressive Web App (PWA) for Bayesian Amyloid Helper - a medical calculator that computes diagnostic and prognostic probabilities for amyloid pathology using Bayesian statistics. The application helps clinicians assess amyloid positivity based on biomarker test results.

## Architecture

### Core Files
- **index.html** - Main HTML structure with diagnostic/prognostic UI tabs
- **app.js** - JavaScript application logic for Bayesian calculations, test libraries, and UI interactions
- **styles.css** - Styling with CSS custom properties and responsive design
- **sw.js** - Service worker for offline functionality and caching
- **manifest.webmanifest** - PWA manifest for installability
- **overrides.js** - Non-invasive overlay that provides color threshold customization and therapy triage controls

### Key Components

#### Test Library System
The application includes a comprehensive test library (`TEST_LIBRARY` in app.js) that defines:
- Different biomarker modalities (PET, CSF, plasma)
- Sensitivity/specificity values and likelihood ratios
- Reference standards (autopsy vs PET)
- Default values for positive/indeterminate/negative categories

#### Calculation Engine
Core Bayesian functions:
- `priorFromAgeStage()` - Age/stage-based prior probability calculation
- `applyAPOEonOdds()` - APOE genotype risk adjustment  
- `computePosterior()` - Bayesian posterior calculation with likelihood ratios
- `computeAutopsyPosteriors()` - Autopsy-anchored probability calculations

#### UI State Management
- Tab-based interface (Diagnostic/Prognostic/About)
- Dynamic form updates based on test selection
- Color-coded probability chips with thresholds
- Triage flag system for therapy decisions

## Development Workflow

### Service Worker Cache Management
When making changes to core files, always update the cache version in `sw.js`:
```javascript
const CACHE='amyloid-helper-vXXX'; // Increment version number
```

### Python Distribution (Optional)
The `ptau217_executable_pack/` directory contains:
- `run_ptau217_app.py` - Standalone Python server with embedded assets
- `build_ptau217_exe.ps1` - PowerShell script to build Windows executable
- `README.txt` - Instructions for Python/exe distribution

Build commands:
```powershell
# Run with Python
python .\run_ptau217_app.py

# Build executable
powershell -ExecutionPolicy Bypass -File .\build_ptau217_exe.ps1
```

## Code Patterns

### Probability Calculations
- All probabilities are clamped between safe bounds (1e-6 to 1-1e-6)
- Odds ratios are used for Bayesian updates: `toOdds()` and `fromOdds()`
- APOE genotype effects are applied as odds ratio multipliers

### DOM Updates
- Use `interpretP()` function for probability interpretation and color coding
- Chip updates via `setChip()` and `setAutopsyChip()` functions
- Format percentages consistently with `fmtPct()`

### Error Handling
- Graceful fallbacks for invalid inputs
- Safe defaults when calculations fail
- Mutation observers for dynamic UI updates

## File Naming Conventions

- `.bak-YYYYMMDD-HHMMSS` files are automatic backups
- `patch_*.py` files are development utilities for code modifications
- Core application files have no prefixes

## Testing Notes

This is a pure client-side application with no build system or test framework. Testing is primarily manual through the web interface. Key test scenarios:

1. Verify calculations across different age/stage combinations
2. Test APOE genotype adjustments
3. Validate autopsy vs PET reference scaling
4. Check offline functionality via service worker
5. Ensure responsive design across devices

## Deployment

The application is deployed as a static PWA. Core files needed for deployment:
- index.html, app.js, styles.css, sw.js, manifest.webmanifest
- Any additional assets referenced in the manifest

No build process is required - files can be served directly from any static web server.