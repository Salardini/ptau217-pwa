# Bayesian Amyloid Helper - Comprehensive Application Documentation

## Overview

The Bayesian Amyloid Helper is a sophisticated Progressive Web Application (PWA) that implements Bayesian inference for amyloid pathology assessment in clinical and research settings. It provides dual-reference probability calculations (PET-anchored and autopsy-anchored) with support for sequential biomarker testing and comprehensive case management.

## Clinical Purpose

This tool computes posterior probability of amyloid positivity using Bayes theorem applied to biomarker test results. It addresses the critical clinical need for:
- **Diagnostic Support**: Quantitative probability assessment for amyloid pathology
- **Sequential Testing**: Optimal ordering and interpretation of multiple biomarkers
- **Clinical Decision Making**: Therapy triage and risk stratification
- **Research Applications**: Standardized probability calculations across studies

## Mathematical Methodology

### Core Bayesian Framework

The application implements classical Bayesian inference using odds ratio formulation:

**Mathematical Foundation:**
```
Prior Odds = P(A+) / (1 - P(A+))
Posterior Odds = Prior Odds × Likelihood Ratio
Posterior Probability = Posterior Odds / (1 + Posterior Odds)
```

**Key Advantages:**
- Mathematically robust probability updates
- Sequential test integration
- Uncertainty quantification
- Literature-grounded parameters

### Prior Probability Calculation

Prior probabilities are calculated using age and cognitive stage-adjusted empirical anchors derived from research cohorts:

**Stage-Based Anchors:**
- **CN (Cognitively Normal)**: 10% at age 50 → 44% at age 90
- **SCD (Subjective Cognitive Decline)**: 12% at age 50 → 43% at age 90  
- **MCI (Mild Cognitive Impairment)**: 27% at age 50 → 71% at age 90
- **DEM (Dementia)**: 60% at age 50 → 85% at age 90

**Age Interpolation:**
Linear interpolation between age 50 and 90 anchors provides continuous age adjustment based on epidemiological data.

### APOE Genotype Risk Adjustment

APOE genotype modifies prior probability via odds ratio multiplication:

| Genotype | Odds Ratio | Clinical Impact |
|----------|------------|-----------------|
| ε2/ε2    | 0.6        | Protective |
| ε2/ε3    | 0.6        | Protective |
| ε3/ε3    | 1.0        | Baseline (reference) |
| ε2/ε4    | 2.6        | Mixed risk |
| ε3/ε4    | 3.5        | Increased risk |
| ε4/ε4    | 12.0       | High risk |

**Application Method:**
APOE adjustment is applied to prior odds before biomarker likelihood ratio application, maintaining proper Bayesian sequence.

### Dual Reference System

The tool provides two complementary probability interpretations:

#### 1. PET-Referenced Probabilities
- **Direct Interpretation**: Biomarker performance directly against PET imaging
- **Clinical Relevance**: Immediate PET prediction utility
- **Research Standard**: Most biomarker validation studies use PET reference

#### 2. Autopsy-Anchored Probabilities
- **Gold Standard**: Cross-calibrated to neuropathological ground truth
- **Clinical Context**: More relevant for ultimate disease confirmation
- **Cross-Calibration Method**: Uses PET vs autopsy bridging (default: Se=92%, Sp=90%)

**Harmonization Process:**
1. Calculate PET-referenced posterior probability
2. Apply PET vs autopsy performance characteristics
3. Generate equivalent autopsy-anchored probability
4. Present both interpretations with appropriate clinical context

## Biomarker Test Library

### Test Categories and Performance

#### Imaging Biomarkers
**Amyloid PET (Visual Reading)**
- Reference Standard: Autopsy
- Sensitivity: 92%
- Specificity: 90%
- Clinical Interpretation: Direct binary readout (positive/negative)
- Likelihood Ratios: LR+ = 9.20, LR- = 0.089

#### CSF Biomarkers (PET-Referenced)

**CSF Aβ42/40 Ratio (Lumipulse Platform)**
- Sensitivity: 92%
- Specificity: 93%
- Likelihood Ratios: LR+ = 13.14, LR- = 0.086
- Clinical Notes: High analytical precision, standardized protocols

**CSF p-tau181/Aβ42 Ratio (Elecsys Platform)**
- Sensitivity: 91%
- Specificity: 89%
- Likelihood Ratios: LR+ = 8.27, LR- = 0.101
- Clinical Notes: Widely available, established cutoffs

#### Plasma Biomarkers (PET-Referenced)

**Plasma Aβ42/40 Ratio (Generic)**
- Sensitivity: 85%
- Specificity: 85%
- Likelihood Ratios: LR+ = 5.67, LR- = 0.176
- Clinical Notes: Moderate performance, improving methodologies

**Plasma p-tau217 (Generic)**
- Sensitivity: 92%
- Specificity: 94%
- Likelihood Ratios: LR+ = 15.33, LR- = 0.085
- Clinical Notes: Emerging high-performance biomarker

**Plasma p-tau217/Aβ42 Ratio (Lumipulse)**
- Sensitivity: 96%
- Specificity: 92%
- Likelihood Ratios: LR+ = 12.00, LR- = 0.043
- Clinical Notes: Combined biomarker approach, mixed reference standards

### Platform-Specific Considerations

The test library accounts for:
- **Assay Variability**: Platform-specific performance characteristics
- **Reference Standard Differences**: PET vs autopsy vs mixed references
- **Analytical Performance**: Precision and accuracy considerations
- **Clinical Validation**: Literature-supported parameters

## Clinical Workflow

### Input Parameters

#### Essential Clinical Data
1. **Age**: 18-100 years (continuous age adjustment)
2. **Cognitive Stage**: CN, SCD, MCI, or DEM classification
3. **APOE Genotype**: Optional risk modification (unknown defaults to ε3/ε3)

#### Biomarker Testing
1. **Primary Test (Test A)**:
   - Biomarker modality selection
   - Result interpretation (positive/indeterminate/negative)
   - Custom likelihood ratio editing (advanced mode)

2. **Optional Secondary Test (Test B)**:
   - Sequential application using Test A posterior as prior
   - Independent biomarker assumption
   - Correlation warning system

#### Advanced Parameters (Expert Mode)
1. **PET vs Autopsy Harmonization**:
   - PET sensitivity vs autopsy (default: 0.92)
   - PET specificity vs autopsy (default: 0.90)
   - Prevalence for PPV/NPV calibration (default: 0.50)

2. **Custom Likelihood Ratios**:
   - Manual LR adjustment for research applications
   - Literature-based parameter exploration
   - Sensitivity analysis capabilities

### Result Interpretation System

#### Probability Thresholds and Color Coding
- **Green (≥90%)**: "High likelihood of PET positivity"
- **Amber (70-89%)**: "Likely PET positivity" 
- **Grey (30-69%)**: "Indeterminate"
- **Red (≤30%)**: "Low likelihood of PET positivity"

#### Autopsy-Anchored Terminology
- **Green (≥90%)**: "High probability of autopsy A+"
- **Amber (70-89%)**: "Likely autopsy A+"
- **Grey (30-69%)**: "Indeterminate"
- **Red (≤30%)**: "Low probability of autopsy A+"

#### Clinical Decision Support
- **Therapy Triage Cutoffs**: Customizable threshold (default: 80%)
- **Risk Stratification**: Visual probability scales
- **Plain Language Interpretation**: Non-technical result summaries
- **Confidence Intervals**: Uncertainty quantification (planned feature)

### Sequential Testing Logic

#### Test A Application
1. Calculate age/stage-adjusted prior
2. Apply APOE genotype modification
3. Update with Test A likelihood ratio
4. Generate PET and autopsy-anchored posteriors

#### Optional Test B Integration
1. Use Test A posterior as new prior probability
2. Apply Test B likelihood ratio
3. Generate final integrated probabilities
4. Display correlation warnings if applicable

#### Independence Assumptions
- Tests assumed conditionally independent given disease status
- Violation warning for potentially correlated biomarkers
- Conservative interpretation recommendations

## Technical Architecture

### Progressive Web App Features

#### Service Worker Implementation
- **Offline Functionality**: Full app capability without internet
- **Cache Management**: Version-controlled asset caching
- **Update Mechanism**: Automatic cache invalidation for new versions
- **Performance Optimization**: Instant loading from cache

#### PWA Manifest
- **Installability**: Native app-like installation
- **Cross-Platform**: iOS, Android, desktop compatibility
- **Icon System**: Branded app icons and splash screens
- **Display Modes**: Standalone app experience

#### Responsive Design
- **Mobile-First**: Optimized touch interfaces
- **Tablet Support**: Enhanced layouts for medium screens
- **Desktop Features**: Full keyboard navigation
- **Accessibility**: WCAG 2.1 AA compliance

### Client-Side Processing

#### Pure JavaScript Implementation
- **No Server Dependencies**: Complete client-side calculation
- **Real-Time Updates**: Instant recalculation on input changes
- **Mathematical Precision**: Robust numerical computation
- **Error Handling**: Graceful degradation for edge cases

#### Local Data Management
- **Browser Storage**: LocalStorage for case persistence
- **Privacy-First**: No data transmission to servers
- **Cross-Session Continuity**: Persistent user preferences
- **Export/Import**: JSON-based data portability

#### Theme System
- **Dark/Light Modes**: Complete visual theme switching
- **CSS Custom Properties**: Systematic color management
- **Accessibility**: High contrast and reduced motion support
- **User Preference**: Persistent theme selection

### Advanced Features

#### Guided Tutorial System
- **Interactive Walkthrough**: Step-by-step user guidance
- **UI Element Highlighting**: Visual focus on relevant controls
- **Progress Tracking**: Tutorial completion monitoring
- **Skip/Resume**: Flexible tutorial navigation

#### Case Management System
- **Save/Load Functionality**: Clinical scenario persistence
- **Metadata Support**: Case names, notes, timestamps
- **Bulk Operations**: Export all cases as JSON
- **Version Control**: Case modification tracking

#### What-If Analysis
- **Parameter Sensitivity**: Real-time parameter exploration
- **Scenario Comparison**: Side-by-side probability comparisons
- **Range Visualization**: Probability confidence bands
- **Clinical Insights**: Smart suggestions based on results

#### Export Functionality
- **Text Reports**: Formatted clinical summaries
- **PDF Generation**: Printable result documents (planned)
- **Data Export**: Machine-readable JSON formats
- **Custom Templates**: Flexible report formatting

## Quality Assurance and Validation

### Mathematical Validation
- **Literature Concordance**: Parameters derived from peer-reviewed studies
- **Numerical Stability**: Robust bounds and error handling
- **Edge Case Testing**: Extreme value behavior verification
- **Cross-Validation**: Independent calculation verification

### Clinical Validation
- **Expert Review**: Clinical accuracy assessment
- **Use Case Testing**: Real-world scenario validation  
- **Educational Feedback**: User experience optimization
- **Continuous Updates**: Literature-based parameter refinement

### Software Quality
- **Version Control**: Git-based development tracking
- **Documentation**: Comprehensive code and user documentation
- **Testing**: Automated unit and integration testing (planned)
- **Security**: Client-side privacy protection

## Literature Foundation

### Key Reference Studies

#### PET vs Autopsy Validation
- **Clark et al. (2012)**: Cerebral PET with florbetapir compared with neuropathology at autopsy
- **Curtis et al. (2015)**: Phase 3 trial of flutemetamol labeled with radioactive fluorine 18
- **Sabri et al. (2015)**: Florbetaben PET imaging to detect amyloid beta plaques in Alzheimer's disease

#### CSF Biomarker Performance
- **Leuzy et al. (2019)**: Diagnostic performance of RO948 F 18 tau positron emission tomography
- **Hansson et al. (2018)**: CSF biomarkers of Alzheimer's disease concord with amyloid-β PET
- **Palmqvist et al. (2020)**: Performance of an automated cerebrospinal fluid assay

#### Plasma Biomarker Validation
- **Palmqvist et al. (2020)**: Discriminative accuracy of plasma phospho-tau217
- **Ashton et al. (2024)**: The validation of plasma phospho-tau217 as a prognostic biomarker
- **Janelidze et al. (2020)**: Plasma P-tau181 in Alzheimer's disease

#### APOE Risk Assessment
- **Liu et al. (2013)**: Apolipoprotein E and Alzheimer disease: risk, mechanisms and therapy
- **Farrer et al. (1997)**: Effects of age, sex, and ethnicity on the association between APOE genotype

### Population Priors
Prior probability anchors derived from:
- **Alzheimer's Disease Neuroimaging Initiative (ADNI)**
- **Australian Imaging, Biomarkers and Lifestyle (AIBL)**
- **Swedish BioFINDER Study**
- **Mayo Clinic Study of Aging**

## Clinical Disclaimers and Limitations

### Educational Purpose
- **Research Tool**: Designed for educational and research applications
- **Not Clinical Software**: Explicitly not for clinical diagnosis
- **Expert Interpretation**: Requires clinical expertise for result interpretation
- **Validation Required**: Independent validation needed for clinical use

### Mathematical Assumptions
- **Conditional Independence**: Tests assumed independent given disease status
- **Population Priors**: Based on research cohort data
- **Reference Standards**: Accounts for imperfect gold standards
- **Literature Parameters**: Subject to ongoing research updates

### Technical Limitations
- **Browser Dependency**: Requires modern web browser
- **Local Storage**: Cases limited to single device/browser
- **Offline Functionality**: Limited without internet for updates
- **Calculation Precision**: JavaScript floating-point limitations

## Future Development

### Planned Features
- **Enhanced Statistics**: Confidence intervals and uncertainty quantification
- **Advanced Visualizations**: Interactive probability plots and risk curves
- **Cloud Synchronization**: Cross-device case management
- **API Integration**: Connection to laboratory information systems
- **Multi-Language Support**: International accessibility
- **Mobile App**: Native iOS and Android applications

### Research Integration
- **Literature Updates**: Automated parameter updating from new studies
- **Biomarker Expansion**: Integration of novel biomarker assays
- **Population Specificity**: Demographic-specific prior adjustments
- **Outcomes Research**: Long-term validation studies

### Technical Enhancements
- **Performance Optimization**: Faster calculations and rendering
- **Accessibility Improvements**: Enhanced screen reader support
- **Security Hardening**: Advanced client-side privacy protection
- **Analytics Integration**: Usage pattern analysis for UX improvement

## Conclusion

The Bayesian Amyloid Helper represents a comprehensive implementation of Bayesian inference for amyloid pathology assessment. By combining robust mathematical methodology with modern web technologies, it provides researchers and clinicians with a powerful tool for probability-based diagnostic reasoning. The dual-reference system, extensive biomarker library, and sophisticated user interface make it uniquely suited for educational and research applications in the evolving landscape of Alzheimer's disease biomarker assessment.

---

*This documentation reflects the application state as of version 215. For the most current information, consult the embedded About tab and CLAUDE.md development documentation.*
