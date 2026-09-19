# Public Audio Datasets for Motor Fault Classification

Research date: September 17, 2026; archive audits updated September 18. Ottawa v2, AI Mechanic v1 and Jin v1 were downloaded and audited; their measured evidence is recorded below. Other archive counts, durations and sizes remain publisher-reported.

## September 18 Ottawa Audit

The 1,386,524,669-byte archive from `https://data.mendeley.com/public-api/zip/msxs4vj48g/download/2` has SHA-256 `9c5e67145400e3806c4deb9df28cf41f2ccae22b9a7c5f1e8ee1b1a4d38c0907`. It contains 128 acquisition MAT files, 128 matching CSV measurement files and one time CSV. All microphone pairs matched at absolute tolerance 1e-6 with relative tolerance zero. Each MAT array has 420,000 rows and five finite columns; microphone column 2 alone was exported as mono 42 kHz PCM16 after per-record peak normalization to 0.95. These changes and the attribution to Mert Sehri and Patrick Dumond (2026), CC BY 4.0, are retained in the audit.

Actual stems use underscores: `H_H` healthy, `R_U` rotor unbalance, `R_M` rotor misalignment, `S_W` stator winding, `V_U` voltage unbalance, `B_R` bowed rotor, `K_A` broken rotor bars, and `F_B` faulty bearing. Each class has 16 acquisitions across eight speed profiles and two loads. CSV/MAT copies are not independent data. No duplicate canonical acoustic hashes were found.

The frozen local simulation uses profile 1 for development (16), profiles 2-7 for training (96), and profile 8 for final test (16). All partitions contain the same physical motor population: this split measures held-out operating conditions, not generalization to unseen motors. Source mappings and publisher labels are in a separate local reference file; operational manifests contain only opaque IDs, group IDs and partition. This is not OS-enforced access separation. The teacher trained no targets from publisher labels; it generated fallible silver labels instead. See the [aggregate audit](../ml/ottawa-v1-audit.json) and [completed simulation](../ml/README.md), whose diagnostic result was negative.

## September 18 Supervised Literature Review

The next experiment was requested after the negative one-shot result, to distinguish data limitations from teacher limitations. Published supervised performance and local reproduction are different evidence. A strong supervised control on the same held-out acquisitions would demonstrate learnable signal under that protocol; a weak control alone would not prove that the data contain no usable information. Publisher-label training belongs in a separately identified diagnostic control, never in the operational silver-only specialist path.

| Primary source | Audio-only supervised result | Evaluation and limitations |
| --- | --- | --- |
| Spadini, Nose-Filho and Suyama, [Intelligent Fault Diagnosis of Type and Severity in Low-Frequency, Low Bit-Depth Signals](https://arxiv.org/html/2411.06299v1), 2024 preprint, sections 4-9 | MAFAULDA microphone channel only; 42 fault/severity classes; XGBoost with statistical, spectral and MFCC/delta features: 99.54% accuracy, 99.52% F2. MFCC/deltas alone: 97.83% accuracy. | The authors explicitly assign 20% of original files to test and keep their windows out of training; augmentation is training-only. This addresses same-recording window leakage, but not independent-machine generalization. Extensive sequential parameter searches are described; nested selection, scaler fitting boundaries and an untouched post-selection test are not established by the text read. The abstract and final table disagree for the greedy-wrapper variant, so that variant is not adopted as a numerical benchmark. MAFAULDA reuse permission remains unresolved. |
| Fedorishin et al., [Fine-Grained Engine Fault Sound Event Detection Using Multimodal Signals](https://arxiv.org/html/2403.11037v1), 2024, Table 2 | The audio-only CRNN without pretraining reports macro ROC-AUC 0.7586, mAP 0.3384, segment-F1 0.3449 and event-F1 0.0979, averaged over three initializations. | 2,643 audio/vibration recordings, 232 vehicle models, ten engine-fault event categories; approximately 70/15/15 split. The audio-only row, not sensor fusion, is quoted. No vehicle-identity-disjoint split or public download/license was verified. ROC-AUC is not classification accuracy; event detection with simultaneous faults is not the same task as one label per clip. |

These papers do not support the blanket conclusion that motor sound datasets are intrinsically uninformative. They also do not establish that a general audio LLM can recover a diagnostic taxonomy without supervised training. Laboratory results cannot be transferred to heavy-vehicle field diagnosis. Scores attributed to vibration channels in search summaries were excluded. Search summaries were used only to locate primary sources, not as evidence.

### Additional Candidates Located During the Review

- [Motor pure sound signal and real industrial environment noise sound signal samples](https://data.mendeley.com/datasets/9dpmkgpncw/1), Linjie Jin, 2025, DOI 10.17632/9dpmkgpncw.1: the original card states CC BY 4.0, four conditions (healthy, magnet fracture, excessive Hall adhesive on the stator, bearing too tight), three observation directions, PCB condenser microphone and smartphone, and clean/production-line/laboratory-noise conditions. The archive is listed at 2.62 GB. This is a new motor-domain candidate for an audit and separate supervised control; acquisition independence, actual file quality and an associated supervised publication have not yet been verified. No teacher result exists on it.
- Yi, Choi and Lee, [Sound-Based Drone Fault Classification Using Multi-Task Learning](https://zenodo.org/records/7779574), 2023, DOI 10.5281/zenodo.7779574: CC BY 4.0; three drones, normal/motor-failure/propeller-cut conditions with component positions, paired microphones and repeated noise mixes. The card lists 7.6 GB and a 60/20/20 split. Original-recording and noise-mixture independence must be checked; published numerical results were not extracted. It changes the mechanical domain and is not selected in place of motors.
- [Squirrel-Cage Induction Motor Fault Diagnosis](https://github.com/MatPiech/motor-fault-diagnosis): the repository describes microphone JSON at 16 kHz as well as thermal/IMU data, but its cited study concerns thermal imaging and the dataset has CC BY-NC-ND 4.0 terms. The code's MIT license does not license the data. It is not selected for this business-facing experiment.

No new dataset download or inference had been performed when this review entry was written. Archive observations and experimental outcomes must be recorded separately below rather than retrospectively presented as prerequisites already known.

## September 18 Jin Audit And Comparison

After the literature review, the twelve PCB-microphone WAVs and legend were downloaded from the official version-1 catalog and individually SHA-256 checked. The full 2.62 GB archive was not downloaded: smartphone and noise subsets remain unused. The mono 44.1 kHz recordings total 7,218.741 seconds; eleven last 600 seconds and one normal recording 618.741 seconds. All selected source samples were finite. Canonical ten-second windows were nonconstant and unique. Nine fault WAVs contain FLOAT samples; three normal WAVs contain PCM16 samples, a potential acquisition confound. Rewriting all windows as PCM16 without metadata, with DC removal and peak normalization, removes explicit format metadata but does not prove removal of signal-level acquisition artifacts.

The frozen experiment uses front recordings for four one-shot supports, left recordings for 120 training windows and right recordings for twelve development windows. Four original acquisitions supply each role; physical-unit/session independence is undocumented. The source legend defines normal, magnet fracture, excess Hall adhesive and tight bearing. CC BY 4.0 attribution and changes are in the [aggregate audit and comparison](../ml/jin-directions-v1.json). No associated supervised paper on these exact files was verified, so the local methods are diagnostic controls, not a published-method reproduction.

Welch features plus logistic regression recognized 12/12 development clips using either the four supports or 120 labeled training windows. MFCC plus SVM recognized 6/12 and 8/12 respectively. The actual GPT Audio 1.5 teacher, using the same four supports and twelve queries, recognized 6/12 with macro-F1 0.375 and zero recall for healthy/tight-bearing conditions. The [preregistered protocol and full results](EXPERIMENTS.md#exp-007-new-motor-data-with-supervised-diagnostic-controls) preserve every attempt. This establishes usable class-discriminating signal under the direction-transfer protocol, not causal diagnosis on unseen motors. The full-data regime changes direction as well as label count; it is not a controlled n-shot curve. The teacher failed its predefined quality threshold, so no additional silver collection or promotion followed.

## Initial Recommendation (Before the Experiments)

Start the dataset audit with the University of Ottawa Electric Motor Dataset (UOEMD-VAFCVS), version 2. It provides real microphone measurements, labeled motor conditions, speed and load variation, and a CC BY 4.0 license. Use only the acoustic channel for the audio-only experiment. Treat this as a related-domain demonstration on electric motors, not as evidence of diagnostic performance on heavy-vehicle combustion engines.

MAFAULDA is a useful second candidate for mechanical fault categories, subject to confirming reuse permission with the original publisher. SUBF v2.0 offers a simple three-class bearing task, but its noncommercial license requires clarification before a manufacturer-facing use. MIMII is appropriate for normal/anomalous detection, not a substitute for a labeled multiclass fault dataset.

This search did not verify a freely downloadable, clearly licensed dataset that directly covers multiple diagnosed faults in heavy-vehicle combustion engines. Public automotive sources found have limited labels, small sample counts, restricted access, or no verified download.

## Candidate Comparison

| Dataset | What the audio represents | Labels and scale | Published license or access | Role |
| --- | --- | --- | --- | --- |
| [UOEMD-VAFCVS v2](https://data.mendeley.com/datasets/msxs4vj48g/2) | Eight three-phase electric motors with induced faults | Motor-condition codes; constant and variable speeds; loaded and unloaded; 10-second recordings | CC BY 4.0; download listed | Preferred multiclass audit |
| [MAFAULDA](https://www02.smt.ufrj.br/~offshore/mfs/page_01.html) | Laboratory rotating machinery; microphone plus other sensors | Normal, imbalance, horizontal/vertical misalignment, bearing faults; 1,951 recordings | Download listed; explicit reuse license not found on the original pages checked | Mechanical-fault alternative, permission pending |
| [SUBF v2.0](https://www.kaggle.com/datasets/sumairaziz/subf-v2-0-dataset-bearing-faults-sound-data) | Bearing sound from an electric-motor testbed | Normal, inner-race fault, outer-race fault; 6,480 segments | CC BY-NC-SA 4.0 | Three-class research alternative |
| [IDMT-ISA-ELECTRIC-ENGINE](https://www.idmt.fraunhofer.de/en/publications/datasets/isa-electric-engine.html) | Three small brushless DC motors | Good, heavy load, broken; 2,378 WAV files | CC BY-NC-ND 4.0; evaluation purposes | Small operational-state example |
| [MIMII public 1.0](https://zenodo.org/records/3384388) | Valves, pumps, fans, slide rails in factory noise | Normal/anomalous labels; four machine IDs per type in this release | CC BY-SA 4.0 | Anomaly detection and fallback evaluation |
| [AI Mechanic](https://www.kaggle.com/datasets/eoinedge/ai-mechanic-engine-condition-audio-fault-finding) | One BMW M54b25 engine with induced abnormal conditions | Actual archive: 34 train/5 test WAVs; 15 constant train signals excluded, 19 usable across normal, intake leak, open oil cap and background | Apache 2.0 on the dataset card | Small audited four-category experiment; negative learning result, no independent vehicle validation |
| [OtoMobile](https://zenodo.org/records/3382945) | Recordings of failing car components extracted from videos | 12 automobile issues across 65 recordings | Restricted files; access request; educational and research purposes only | Automotive reference, not immediately usable |

## Preferred Dataset: Ottawa

- Source: [Mendeley Data, version 2](https://data.mendeley.com/datasets/msxs4vj48g/2), published February 9, 2026; DOI: [10.17632/msxs4vj48g.2](https://doi.org/10.17632/msxs4vj48g.2). Authors: Mert Sehri and Patrick Dumond.
- Equipment: eight D396 Marathon Electric three-phase motors, with faults artificially created by SpectraQuest; a PCB 130F20 microphone, three accelerometers, and temperature measurement.
- Audio: column 2 of the measurement files is the microphone signal. Columns 1, 3, and 4 are accelerometers; column 5 is temperature. These channels must not be mixed into an experiment described as audio-only.
- Format: CSV and MATLAB representations; 42 kHz sampling rate; 10 seconds and 420,000 samples per recording. The publisher lists a 1.29 GB download containing the representations. CSV and MATLAB copies must not be counted as independent recordings.
- Conditions: filename codes describe motor health, speed profile, and load. The published legend covers healthy state and rotor, stator-winding, voltage, bowed-rotor, broken-rotor-bar, and bearing conditions. It explicitly gives `H-H` for healthy and `S-W` for stator-winding fault. Confirm the complete combinations against the actual file manifest before freezing class names.
- Operating variation: four constant settings labeled 15, 30, 45, and 60 Hz; four increasing/decreasing profiles; loaded and unloaded conditions. Verify the relationship between the published speed settings, electrical drive frequency, and shaft RPM before using RPM as metadata.
- License: CC BY 4.0, allowing commercial reuse subject to its terms, including attribution and identifying changes.
- Main limitation: these are electric motors with induced faults. Because different physical units carry different faults, unit identity may be confounded with fault class. Verify independent units and repeat acquisitions per condition; splitting recordings alone cannot establish generalization to unseen motors.

The first implementation experiment should test whether the microphone channel alone separates the documented conditions on a held-out acquisition or operating condition. Published results using other sensors would not establish this. No accuracy or teacher capability is assumed.

## Mechanical-Fault Alternatives

### MAFAULDA

The [UFRJ source](https://www02.smt.ufrj.br/~offshore/mfs/page_01.html) describes 1,951 five-second recordings, sampled at 50 kHz, from a SpectraQuest machinery fault simulator. Each CSV has eight columns: tachometer, six accelerometer channels, and the microphone in column 8. The microphone is a Shure SM81. The full archive is listed at approximately 13 GB, with separate downloads by condition.

The clearly described top-level conditions include normal operation (49 recordings), imbalance (333), horizontal misalignment (197), and vertical misalignment (301). Additional recordings cover damaged bearings at underhang and overhang positions. Those positions are not synonyms for inner-race and outer-race faults. The source's bearing summary table and detailed descriptions use inconsistent subcategory names; resolve them against the archive and author documentation before adopting fine-grained bearing labels. Some bearing experiments also add imbalance masses, so they are not necessarily isolated single-fault examples.

For an initial audit, the four unambiguous conditions above form a possible taxonomy. Retain speed and fault-severity metadata, and account for the small normal class. The original pages checked did not state an explicit reuse license. A permissive label on a third-party copy would not settle the original rights; obtain clarification before business use or redistribution.

### SUBF v2.0

The [author's dataset card](https://www.kaggle.com/datasets/sumairaziz/subf-v2-0-dataset-bearing-faults-sound-data) describes sound recorded with a BOYA BY-M1 microphone from a three-phase AC motor testbed. It reports 18 hours at 10 kHz, divided into 6,480 ten-second signals: 2,160 each for normal, inner-race fault, and outer-race fault. Signals are distributed as CSV files. SUBF v1.0 is a different, vibration-based dataset and must not be substituted for v2.0 audio.

Its CC BY-NC-SA 4.0 license is not an unrestricted commercial-use license. Also, 6,480 segments do not imply 6,480 independent experiments: check acquisition-session and bearing identities before designing evaluation splits. Related publication: [10.1016/j.dsp.2024.104776](https://doi.org/10.1016/j.dsp.2024.104776).

### IDMT-ISA-ELECTRIC-ENGINE

The [Fraunhofer source](https://www.idmt.fraunhofer.de/en/publications/datasets/isa-electric-engine.html) reports three small 24 V brushless DC motors and 2,378 mono WAV files at 44.1 kHz, totaling 42.32 minutes: 774 good, 815 heavy-load, and 789 broken examples. The acoustic conditions were provoked by changes in voltage and loading weight. Heavy load is an operating state, not inherently a diagnosed component defect.

The [download record](https://zenodo.org/records/7551261) is linked by Fraunhofer. The stated license is CC BY-NC-ND 4.0 for evaluation purposes. Check permission for the intended training, derived artifacts, and business demonstration before selecting it.

## Automotive and Anomaly Sources

### AI Mechanic

The [dataset card](https://www.kaggle.com/datasets/eoinedge/ai-mechanic-engine-condition-audio-fault-finding) identifies a 2004 BMW M54b25, recorded in 2021, with induced oil-cap and intake conditions, under Apache 2.0. Its simplified three-class description and listed file count do not match the finer actual archive annotations. Version 1, downloaded September 18, has SHA-256 `c09ee8d3793c1ccfb23a2171570c0ce5ef8295e1abfee6120a8ea374fffc7704` and contains 39 mono PCM16/16 kHz WAVs: 34 publisher-training and five publisher-testing recordings. Annotation files distinguish normal/idling, air leak, oil cap removed and background, with inside-cabin variants. Testing also contains unknown/testing labels that cannot be invented into diagnostic truth.

Fifteen publisher-training recordings are byte-identical constant PCM -8 throughout 21.12 seconds, yet carry incompatible annotations. The importer first rejected cross-partition duplicates and then conflicting labels; a subsequent label-independent constant-signal quality exclusion removed these 15 before splitting. Nonconstant conflicting duplicates still fail. Nineteen usable source recordings remain: normal 6, air_leak 4, oil_cap_open 4, background_noise 5. Two lowest full-source hashes per class define eight development recordings; eleven remain for training. Only one first-min(10 seconds, duration) window per source is retained, preserving source grouping and stripping metadata. Opaque UUIDs and a separate sealed manifest mask the model inputs. Same-vehicle and unknown-session dependence remain; there is no independent final set on this source. Publisher-testing audio was not imported or heard.

Actual GPT Audio experiments and the 4/8/11-arrival silver-only curve are documented in [EXPERIMENTS.md](EXPERIMENTS.md). The best development teacher scored 3/8, and the two fitted specialists scored 2/8 and 1/8. Peak normalization did not improve macro-F1. This source supports exercising the software workflow but has not established useful diagnosis, learning improvement or transfer to heavy-duty vehicles.

### OtoMobile

The [Northwestern University description](https://interactiveaudiolab.github.io/resources/datasets/otomobile.html) reports 65 clips covering 12 automobile issues. The diagnoses were supplied by mechanics or people who had consulted mechanics. Annotations include component location, operating context, source video, and excerpt start time.

The [Zenodo record](https://zenodo.org/records/3382945) currently restricts file access and specifies educational and research purposes only. It is not a verified open download or commercially cleared collection. Its small size also limits its use as a training and evaluation benchmark.

### MIMII

[MIMII public 1.0](https://zenodo.org/records/3384388) contains recordings of valves, pumps, fans, and slide rails at 16 kHz, 16-bit, with eight microphone channels. This release provides machine IDs 00, 02, 04, and 06. Factory noise is mixed at several signal-to-noise ratios. The full release is approximately 100.2 GB; subsets can be selected instead of downloading everything.

Although the description mentions contamination, leakage, imbalance, and rail damage, the verified archive structure supplies normal/abnormal folders, not a confirmed per-file taxonomy of those causes. Use it for anomaly detection unless additional fault annotations are verified. Its license is CC BY-SA 4.0; assess attribution and applicable share-alike requirements for the planned artifacts. Keep alternate noise mixes of the same source recording in the same split.

## Relevant Sources Not Suitable as the Main Dataset

- [Diesel Engine Faults Features Dataset, 3500-DEFault](https://data.mendeley.com/datasets/k22zxz29kr/1): 3,500 simulated operating scenarios involving intake pressure, compression, and injected fuel. The files contain features from a thermodynamic model, pressure curves, and torsional vibration, not microphone recordings. CC BY 4.0 does not make it suitable for an audio-input demonstration.
- [Sounds of Vehicle Internal Combustion Engines](https://zenodo.org/records/18777405): the description reports 350 cars sampled, 475 initial sound samples, and 320 usable samples after processing; diesel and petrol archives are listed under CC BY 4.0. No defect taxonomy was verified. Engine-type labels must not be treated as fault labels or proof that engines are healthy.
- [Fine-Grained Engine Fault Sound Event Detection Using Multimodal Signals](https://arxiv.org/html/2403.11037v1): a relevant automotive study describing 2,643 audio/vibration recordings across 232 vehicle models and ten event categories, including engine knock, belt squeal, unstable idle, and startup rattle. The paper is public, but this search did not identify a public dataset download or reuse license. It is a reference for task design, not an available training asset.

## Before Training

1. Pin the dataset version, source URLs, license, citation, file hashes, and allowed uses. Preserve the downloaded source outside Git; only publish data or derived examples when the rights permit it.
2. Audit actual recordings, class counts, microphone channels, units, sample rates, clipping, and missing data. Count original acquisitions separately from segments, format duplicates, and augmented copies.
3. Freeze a taxonomy that matches documented labels. Separate fault type, severity, operating condition, and machine identity. Do not combine a class from one dataset with a different class from another dataset as the main benchmark: the model could recognize the recording source instead of the defect.
4. Split by independent acquisition and physical unit where the data supports it, before segmentation or augmentation. If each fault occurs on only one unit, explicitly limit the evaluation claim and obtain further units for an unseen-motor test.
5. Keep trusted dataset labels separate from teacher-generated labels and reserve an untouched final test. Verify the audio teacher against those labels; a general audio model is not automatically a competent mechanical diagnostician.
6. Report class recall, macro-F1, confusion, abstention, latency, and cost for the actual task. A successful electric-motor proxy demonstrates the ModelMetis workflow, not accuracy on a manufacturer's engines. The latter requires manufacturer recordings with confirmed diagnoses and representative operating conditions.
