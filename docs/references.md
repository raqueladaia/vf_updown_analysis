# Papers and practical questions

These linked papers explain the method and its limits. Publisher/DOI links and
available author manuscripts are provided rather than redistributing journal PDFs.

| Question | Read | What it contributes |
| --- | --- | --- |
| Where do up-down estimation and pattern coefficients come from? | Dixon WJ (1980), *Efficient Analysis of Experimental Observations*. Annual Review of Pharmacology and Toxicology 20:441–462. [DOI](https://doi.org/10.1146/annurev.pa.20.040180.002301) | Statistical background for the tabulated k approach. |
| Was this method established in rats? | Chaplan SR et al. (1994), *Quantitative assessment of tactile allodynia in the rat paw*. Journal of Neuroscience Methods 53:55–63. [DOI](https://doi.org/10.1016/0165-0270(94)90144-9), [PubMed](https://pubmed.ncbi.nlm.nih.gov/7990513/) | Original rat validation using approximately 0.41–15.1 g. |
| Why do force labels, handle codes, and spacing matter? | Bradman MJ et al. (2015), *Practical mechanical threshold estimation in rodents using von Frey hairs/Semmes–Weinstein monofilaments: Towards a rational method*. Journal of Neuroscience Methods 255:92–103. [DOI](https://doi.org/10.1016/j.jneumeth.2015.08.010), [author manuscript](https://iris.unito.it/retrieve/e27ce427-6b39-2581-e053-d805fe0acbaa/Bradman%20JNM%20Postprint%2C%202015.pdf) | Calibration and methodological limitations. |
| Why calculate logs from force? Is averaging spacing exact? | Christensen SL et al. (2020), *Von Frey testing revisited: Provision of an online algorithm for improved accuracy of 50% thresholds*. European Journal of Pain 24:783–790. [DOI](https://doi.org/10.1002/ejp.1528), [author manuscript](https://backend.orbit.dtu.dk/ws/files/213362370/Pesei_Christensen_et_al_2019_European_Journal_of_Pain.pdf) | Explains handle/target discrepancies and constant, flexible, and exact interval approaches. The exact method is not implemented here. |
| What related software exists? | Gonzalez-Cano R et al. (2018), *Up–Down Reader: An Open Source Program for Efficiently Processing 50% von Frey Thresholds*. Frontiers in Pharmacology 9:433. [Open-access paper](https://doi.org/10.3389/fphar.2018.00433) | A separate published tool for processing response patterns; not a validation of this repository. |
| Which rat handles and nominal labels are commonly used? | NIH/NINDS, [Rat hind paw mechanical allodynia protocol](https://pspp.ninds.nih.gov/TestDescription/TestPWT); Marvizon JC et al. (2015), *Latent sensitization: a model for stress-sensitive chronic pain*. Current Protocols in Neuroscience 71:9.50.1–14. [DOI](https://doi.org/10.1002/0471142301.ns0950s71), [full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC4532319/) | NIH specifies the eight handles; Marvizon et al. also list nominal gram labels and protocol-specific boundary assignments. |
| Are floor assignments universal? | Ding X et al. (2018), *BDNF contributes to the neonatal incision-induced facilitation of spinal long-term potentiation and the exacerbation of incisional pain in adult rats*. Neuropharmacology 137:114–132. [DOI](https://doi.org/10.1016/j.neuropharm.2018.04.032), [institution-hosted paper](https://nri.bjmu.edu.cn/docs/2020-08/4bb5d5f639024eb8abe3147429f2ee39.pdf) | Methods section 2.4.1 uses a 0.25 g floor and 15 g ceiling; another protocol above describes a different floor. Follow the chosen protocol explicitly. |

## FAQ

- **Is handle 4.08 filament number 4?** No. It identifies the nominal 1 g
  filament. In the rat subset it is ID 3; rat ID 4 is the 2 g filament.
- **Does calculating Log_new prove the force is correct?** No. It transforms the
  supplied force. Actual calibration requires physical measurement.
- **Does the mouse workbook apply to rats?** Its mouse calibration does not.
  The response-pattern coefficients are species-independent and are separately
  distributed in `data/dixon_k.csv` for rat/custom calculations.
- **Does a k table contain every possible response string?** No. This repository
  supports 248 tabulated patterns of lengths 2–9; other patterns need review.
- **Does a passing spacing check validate the entire experiment?** No. The
  experiment must still follow its acquisition and stopping protocol.
- **Does selecting endpoint substitution solve censoring statistically?** No.
  It is an explicit numerical convention. See [boundary handling](boundary_handling.md).
- **What should Methods report?** Species, tested/calibrated forces and ID map,
  start/stopping rules, response coding, log convention, k-table source, delta
  method/value, boundary policy and counts, exclusions, statistical method,
  and software version/commit. Preserve the exported ladder with the data.

Sources checked 2026-10-05. The papers support particular methodological choices;
their inclusion does not imply independent validation of all software outputs.
