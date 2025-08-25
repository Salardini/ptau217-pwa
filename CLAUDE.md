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

#### Test Library System (`app.js:23-70`)
The `TEST_LIBRARY` object defines biomarker tests with their performance characteristics:
- **Structure**: Each test has `label`, `ref` (reference standard), `se`/`sp` (sensitivity/specificity), and `defaults` (LR values)
- **Modalities**: PET (autopsy-referenced), CSF (PET-referenced), plasma (PET-referenced)
- **Likelihood Ratios**: Pre-computed positive/indeterminate/negative LRs for Bayesian updates

#### Bayesian Calculation Engine
Core probability functions handle the mathematical foundation:
- `priorFromAgeStage()` - Age/stage-based clinical priors using `PRIOR_ANCHORS`
- `applyAPOEonOdds()` - APOE genotype risk adjustment via `APOE_OR` multipliers
- `computeDiagnostic()` - Sequential Bayesian updates for 1-2 tests
- `computeAutopsyPosteriors()` - Cross-reference harmonization using PET bridge

#### Autopsy Harmonization Architecture
The application implements a dual-layer probability system:
- **PET Layer**: Direct biomarker→PET calculations using published LRs
- **Autopsy Layer**: PET→autopsy conversion using mixture bounds [1-NPV, PPV]
- **Bridge Functions**: `petPPV()`, `petNPV()`, `autopsyPosteriorFromB()` handle cross-reference scaling

#### UI State Management
- **Tab System**: `showTab()` function manages 3-panel interface (Diagnostic/Prognostic/About)  
- **Form Updates**: Event listeners auto-populate LRs when test modality changes
- **Chip System**: `interpretP()` + `setChip()` provide color-coded probability interpretation
- **Cache-aware**: Service worker registration for offline functionality

## Development Workflow

### Service Worker Cache Management
**CRITICAL**: When making changes to core files, always update the cache version in `sw.js`:
```javascript
const CACHE='amyloid-helper-vXXX'; // Increment version number
```
This prevents users from seeing stale cached versions of the application.

### Development Commands
This is a pure client-side PWA with no build system:
- **Local development**: Serve files directly from any static web server (e.g., `python -m http.server 8000`)
- **Testing**: Manual testing through the web interface - no automated test framework
- **No linting/TypeScript**: Pure JavaScript with no compilation step required

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

### Patch Scripts
Development utilities for code modifications are prefixed `patch_*.py`. These are temporary development tools for applying specific fixes or features.

## Code Patterns

### Probability Mathematics
- **Safe Bounds**: All probabilities clamped to [1e-6, 1-1e-6] to prevent edge cases
- **Odds Operations**: `toOdds(p) = p/(1-p)`, `fromOdds(o) = o/(1+o)` for Bayesian multiplication
- **LR Multiplication**: Sequential tests multiply LRs in odds space, then convert back to probability
- **APOE Effects**: Applied as odds ratio multipliers via `APOE_OR` lookup table

### UI Updates & Formatting
- **Percentage Display**: `fmtPct()` formats probabilities with appropriate precision (<0.1% shows 2 decimals)
- **Chip Coloring**: `interpretP()` returns `[bucket, label]` tuples for CSS class application  
- **Autopsy Labels**: `setAutopsyChip()` wrapper provides autopsy-specific text while preserving PET color thresholds
- **Dynamic Forms**: Modality selectors trigger `setDefaults()` to populate LR fields from `TEST_LIBRARY`

### State Management
- **Global State**: `window.__POSTERIOR__` and `window.__POSTERIOR_AUTOPSY__` store results for prognostic tab
- **Event-driven Updates**: Input changes trigger `updateAutoPrior()` and form recalculation
- **Toggle Visibility**: Test B panel and result blocks show/hide based on `useB` selection

### Error Handling
- **Input Validation**: Number inputs have min/max bounds and fallback to defaults
- **Calculation Safety**: `isFinite()` checks before mathematical operations
- **Graceful Degradation**: Missing DOM elements are checked with optional chaining

## File Organization

### Core Application Files
- `index.html` - Main application interface and structure
- `app.js` - All JavaScript logic (no modules/bundling)  
- `styles.css` - Complete styling with CSS custom properties
- `sw.js` - Service worker for caching and offline support
- `manifest.webmanifest` - PWA configuration
- `overrides.js` - Non-invasive overlay for customizations

### Development Files
- `.bak-YYYYMMDD-HHMMSS` - Automatic timestamped backups
- `patch_*.py` - Temporary development utilities for code modifications
- `fix_*.py` - One-off repair scripts
- `ptau217_executable_pack/` - Optional Python standalone distribution

### Architecture Notes
- **No bundling**: All files loaded directly via `<script>` tags
- **No modules**: Uses global scope and `window` object for state
- **No TypeScript**: Pure JavaScript with inline documentation  
- **Single-page**: All UI managed through tab visibility toggles

## Testing & Validation

### Manual Testing Approach
No automated testing framework - validation is manual through the web interface:

1. **Prior Calculations**: Verify age/stage/APOE combinations produce expected baseline probabilities
2. **Bayesian Updates**: Test LR applications across different biomarker modalities  
3. **Autopsy Harmonization**: Validate PET↔autopsy conversions using bridge functions
4. **Sequential Tests**: Ensure Test A→B combinations multiply LRs correctly
5. **UI Responsiveness**: Check form updates, chip coloring, and tab switching
6. **Offline Functionality**: Verify service worker caching and offline access

## Deployment

The application is deployed as a static PWA. Core files needed for deployment:
- index.html, app.js, styles.css, sw.js, manifest.webmanifest
- Any additional assets referenced in the manifest

No build process is required - files can be served directly from any static web server.