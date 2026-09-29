# Public Audio Datasets For Motor Fault Classification

**Ottawa v2, AI Mechanic v1, Jin v1 and drone v1 are audited development sources. None establishes heavy-vehicle diagnostic performance or a representative independent-machine benchmark.** Other entries below are publisher-reported unless an archive audit is stated. Dataset rights are distinct from paper and code licenses.

## Audited Sources

| Source | Verified audio and labels | Rights | Main limit |
| --- | --- | --- | --- |
| [Ottawa UOEMD-VAFCVS v2](https://data.mendeley.com/datasets/msxs4vj48g/2), Mert Sehri and Patrick Dumond | 128 ten-second microphone acquisitions, eight conditions, speed/load variation | CC BY 4.0 | Physical motor and fault class may be confounded; motors recur across partitions |
| [AI Mechanic v1](https://www.kaggle.com/datasets/eoinedge/ai-mechanic-engine-condition-audio-fault-finding), Eoin / AI Mechanic | 19 usable training-source recordings, four conditions, one BMW M54b25 | Apache-2.0 | One vehicle, unknown session dependence; 15 constant recordings excluded |
| [Jin v1](https://data.mendeley.com/datasets/9dpmkgpncw/1), Linjie Jin | Twelve PCB-microphone files, four conditions, three directions | CC BY 4.0 | Unit/session independence unknown; healthy/fault encoding differs |
| [Drone v1](https://zenodo.org/records/7779574), Yi, Choi and Lee | Three drones, nine conditions, six maneuvers, 324,000 half-second clips | CC BY 4.0 | Three heterogeneous devices; original-take lineage unresolved; shared noise mixtures |

Protocols and diagnostic scores are maintained in [Experiment History](EXPERIMENTS.md).

## Drone Archive Audit

All three archives, DOI `10.5281/zenodo.7779574`, were downloaded and streamed without TAR extraction. Total size: 7,622,850,560 bytes. Downloaded sizes and publisher MD5 values matched. The local SHA-256 fingerprints are:

| Archive | SHA-256 |
| --- | --- |
| A | `b3c6e3e1bc7ecd2c487dee154784fdb302634550118d33b923f010ef8616ad93` |
| B | `c8b20399eda5662f61e4a1483c57bfba666b4ff773678a4ae1eedb89252e8343` |
| C | `824f8d679f7df7c7adf5582f851fcf7dced2d0113238b6d693f63d603abd3e4a` |

All 324,000 files decode to mono 16 kHz PCM24, 8,000 samples each. Each drone contributes 108,000 clips: 64,800 training WAVs and 43,200 validation/test FLACs behind `.wav` suffixes. Container type must not become a feature. Decoded-PCM hashes use left-aligned little-endian int32 without normalization.

libsndfile failed on 93 FLACs, 55 in A and 38 in B. FFmpeg/PyAV decoded them with matching STREAMINFO MD5. All 129,600 FLAC embedded checksums passed. The complete audit took 214.950 s on native ARM64 Python 3.13.13, NumPy 2.5.3, soundfile 0.14.0 and PyAV 18.1.0.

### Labels And Dependence

All nine conditions and six maneuvers occur in each drone. A/C have 12,000 files per condition and 2,000 per condition/maneuver. B has normal 11,798, MF1 12,000, MF2 11,974, MF3 12,000, MF4 12,202, four PC classes of 12,000 each, and 26 missing condition codes. These anomalies affect microphone 2 in validation/test. Missing labels remain null; pairing without the fault field suggests MF1 while the aggregate deficit suggests MF2, so neither supports automatic repair.

| Drone | Filename source-index groups | Groups crossing publisher partitions | Complete labeled microphone pairs |
| --- | ---: | ---: | ---: |
| A | 40,535 | 13,465 | 54,000 |
| B | 41,222 | 14,284 | 52,022 |
| C | 40,915 | 13,085 | 54,000 |

Pair keys contain drone, maneuver, fault, source index, background, background index and SNR. B also has 3,956 incomplete key groups. Complete labeled pairs preserve all 54 condition/maneuver cells; the smallest B cell has 600 pairs, versus 1,000 for A/C. No complete labeled mixture key crosses publisher partitions.

C contains 5,257 exact PCM duplicate pairs across microphones within a partition, involving 10,514 clips. None crosses drones or has conflicting known labels. Repeated source indices are not verified continuous-take identities; differing microphone/noise versions can remain dependent without identical PCM. No archive manifest resolves original-session semantics.

### Signal Quality And Failed Attempts

No clip is constant. A has 253 saturated samples across 167 clips, B 141 across 104 clips and C none. Minimum AC RMS is 0.099954, 0.00003637 and 0.00007755 for A/B/C at full scale 1. B/C contain 90/91 clips below 0.01 and 64/45 below 0.001. These are measurements, not exclusion thresholds chosen after prediction errors.

| Attempt | Seconds | Inspected clips | Outcome |
| --- | ---: | ---: | --- |
| drone-audit-v1 | 40.765 | 64,800 | Filename parser failed because validation omits the training microphone token |
| drone-audit-v2 | 73.356 | 64,800 | WAV-only reader rejected FLAC content; content-aware decoding added |
| drone-audit-v3 | 44.052 | 64,856 | libsndfile failure; checksum-verified FFmpeg fallback added |
| drone-audit-v4 | 134.624 | 205,518 | Missing condition code; explicit null handling added |
| drone-audit-v5 | 214.950 | 324,000 | Complete audit; annotation and dependence limits retained |

The aggregate (`ml/drone-v1-audit.json`; local-only) retains archive fingerprints, counts, quality findings and all attempts. The auditor (`scripts/audit_drone.py`; local-only) keeps individual paths, labels and PCM hashes in restricted local outputs. C was source-audited but remains unevaluated by models. The later A-support/B-query experiments are recorded separately.

### Recording Protocol

[Sound-Based Drone Fault Classification Using Multitask Learning](https://arxiv.org/abs/2304.11708) describes Holy Stone HS720 (A), MJX Bugs 12 EIS (B) and ZLRC SG906 pro2 (C); one figure caption instead says SG960. Faults are approximately 10% propeller cuts or dented motor caps at positions 1-4. Three product types do not provide repeated units of each type, and component-position equivalence requires verification.

Two body-mounted RODE Wireless Go2 microphones recorded six maneuvers in an anechoic chamber with tethered drones. The 48 kHz signal was downsampled to 16 kHz, segmented to 0.5 s and mixed with five campus-noise locations at 10-15 dB SNR. The paper randomly splits each drone's constructed data 60/20/20. Published results therefore do not establish held-out-drone or source-recording-disjoint transfer. The paper license is CC BY-NC-ND; dataset rights are CC BY 4.0.

## Ottawa Audit

The v2 archive has 1,386,524,669 bytes and SHA-256 `9c5e67145400e3806c4deb9df28cf41f2ccae22b9a7c5f1e8ee1b1a4d38c0907`. It contains 128 MAT/CSV acquisition pairs and a time CSV. All pairs matched at absolute tolerance 1e-6, relative tolerance zero. MAT arrays have 420,000 finite rows and five columns: microphone in column 2, accelerometers in 1/3/4 and temperature in 5. Only the microphone was exported as mono 42 kHz PCM16 with peak normalization to 0.95.

Actual filename codes are `H_H` healthy, `R_U` rotor unbalance, `R_M` rotor misalignment, `S_W` stator winding, `V_U` voltage unbalance, `B_R` bowed rotor, `K_A` broken rotor bars and `F_B` faulty bearing. Each class has 16 acquisitions across eight speed profiles and two loads. CSV/MAT copies are duplicate representations; canonical acoustic hashes were unique.

The equipment comprises eight D396 Marathon Electric three-phase motors with induced faults and a PCB 130F20 microphone. Drive-frequency settings must not be treated as shaft RPM without verification. The split uses profile 1 for development (16), 2-7 for training (96) and 8 for final evaluation (16). It measures operating-condition transfer within the same motor population. [Audit](../ml/ottawa-v1-audit.json); [simulation](../ml/README.md).

## AI Mechanic Audit

Archive SHA-256: `c09ee8d3793c1ccfb23a2171570c0ce5ef8295e1abfee6120a8ea374fffc7704`. It contains 39 mono PCM16/16 kHz WAVs: 34 publisher-training and five publisher-testing recordings of one 2004 BMW M54b25. Actual annotations include normal/idling, intake air leak, open oil cap and background, with cabin variants; the card's simplified three-class description is incomplete.

Fifteen training recordings contain constant PCM -8 for 21.12 s despite contradictory labels. A label-independent quality gate excluded them before splitting; nonconstant conflicting duplicates still fail. The remaining class counts are normal 6, air leak 4, open oil cap 4 and background 5. Two lowest source hashes per class form eight development inputs; eleven remain for training. Inputs retain the first ten seconds or shorter full duration, with opaque IDs and sealed labels. Publisher-testing audio and its ambiguous `unknown`/`testing` annotations were not used. Same-vehicle and unknown-session dependence prevent independent-vehicle claims.

## Jin Audit And Comparison

The twelve PCB-microphone WAVs and legend from DOI `10.17632/9dpmkgpncw.1` were individually checked against publisher SHA-256 values. Smartphone/noise subsets and the full 2.62 GB archive were not downloaded. Selected audio is mono 44.1 kHz: eleven files last 600 seconds and one normal file 618.741 seconds, totaling 7,218.741 seconds. Samples are finite; extracted windows are nonconstant and unique.

Nine fault files use FLOAT and three normal files PCM16. Canonical PCM16 export with DC removal and peak scaling removes explicit container differences but may retain acquisition artifacts. The legend maps b1 to magnet fracture, b2 to excess Hall adhesive, b3 to tight bearing and n to healthy. Physical-unit/session independence is undocumented.

Front recordings supply four supports, left recordings 120 training windows and right recordings twelve queries. Four original acquisitions supply each role. [Aggregate](../ml/jin-directions-v1.json) and [EXP-007](EXPERIMENTS.md#exp-007-new-motor-data-with-supervised-diagnostic-controls) report the controls and teacher comparison. No supervised publication tied to these exact files was verified.

## Supervised Literature Review

| Primary source | Audio-only result | Evaluation limits |
| --- | --- | --- |
| Spadini, Nose-Filho and Suyama, [Low-Frequency, Low Bit-Depth Fault Diagnosis](https://arxiv.org/html/2411.06299v1) | MAFAULDA microphone, 42 fault/severity classes: XGBoost accuracy 99.54%, F2 99.52%; MFCC/deltas alone 97.83% accuracy | Original-file 20% test split; training-only augmentation. Independent-machine generalization, nested selection and scaler boundaries not established. Greedy-wrapper abstract/table disagree. Dataset permission unresolved. |
| Fedorishin et al., [Fine-Grained Engine Fault Sound Event Detection](https://arxiv.org/html/2403.11037v1) | Audio-only CRNN: macro ROC-AUC 0.7586, mAP 0.3384, segment-F1 0.3449, event-F1 0.0979, three initializations | 2,643 audio/vibration recordings, 232 vehicle models, ten event categories, approximately 70/15/15 split. No verified vehicle-disjoint split, public archive or data license. |

These tasks and metrics are not interchangeable. Supervised laboratory separability does not establish generative-teacher competence or field diagnosis. Supervised controls remain separate from operational silver-only training.

## Other Candidates

| Source | Task and metadata | Rights and remaining checks |
| --- | --- | --- |
| [UMGED](https://github.com/LeeJMJM/UM-GearEccDataset) | 352 multisensor MAT files with gear condition, eccentricity, structure and speed; structure ID is not motor identity | [Two-file Mendeley subset](https://data.mendeley.com/datasets/ym6pk4889r/1) is CC BY 4.0; full-release rights, microphone channel and independent units unverified. [Paper](https://doi.org/10.1016/j.ymssp.2024.112068). |
| [ToyADMOS2](https://zenodo.org/records/4580270) | `CarID` hardware identity differs from `Model` configuration and `FileID` recording pattern; 48 kHz lossless ALS audio in MP4 | Custom noncommercial internal-evaluation agreement restricts modification/disclosure. Business use uncleared. Hardware-by-fault coverage and recipe/source dependence require audit. [Manual](https://raw.githubusercontent.com/nttcslab/ToyADMOS2-dataset/master/UsersManual.md). |
| [UMFDD v1](https://data.mendeley.com/datasets/3bz24t6tf4/1) | 8.06 GB listed, aggregated public/experimental signals | CC BY 4.0; includes consumed Ottawa data. Measurement-unit normalization does not establish independent machines. |
| [IM-VACD v2](https://data.mendeley.com/datasets/yc8yhg5xjd/2) | Eight D396 motors, three phones and mounting variants; nominal 42 kHz, ten seconds | CC BY 4.0; repeated faults across units and relationship to Ottawa hardware unverified. |
| [AHU acoustic-mirror bearings](https://github.com/Lab-of-AMFD/AHU-Parabolic-Acoustic-Mirror-Bearing-Dataset) | Nine fault combinations, simultaneous direct/mirror audio, 20 kHz, 25 seconds, three speeds | No explicit data license found; repeated specimens, sessions and healthy counts unaudited. |
| [MAFAULDA](https://www02.smt.ufrj.br/~offshore/mfs/page_01.html) | 1,951 five-second 50 kHz recordings; Shure SM81 microphone in CSV column 8; normal, imbalance, misalignment and bearing damage | Original reuse license unresolved. Bearing subcategory descriptions conflict and some runs combine faults. Same-rig recordings. |
| [SUBF v2.0](https://www.kaggle.com/datasets/sumairaziz/subf-v2-0-dataset-bearing-faults-sound-data) | BOYA BY-M1, 10 kHz, 6,480 ten-second segments across normal/inner-race/outer-race conditions | CC BY-NC-SA 4.0; bearing/session grouping unverified. V1 is vibration and cannot substitute for audio. [Paper](https://doi.org/10.1016/j.dsp.2024.104776). |
| [IDMT-ISA-ELECTRIC-ENGINE](https://zenodo.org/records/7551261) | Three motors, 2,378 mono 44.1 kHz WAVs: good 774, heavy load 815, broken 789 | CC BY-NC-ND 4.0; heavy load is an operating state, not necessarily a fault. |
| [OtoMobile](https://zenodo.org/records/3382945) | 65 clips, twelve automobile issues, mechanic-informed diagnoses | Restricted files, educational/research use; business clearance unverified. |
| [Squirrel-Cage Motor Diagnosis](https://github.com/MatPiech/motor-fault-diagnosis) | 16 kHz microphone JSON plus thermal/IMU data | Dataset CC BY-NC-ND 4.0; code MIT does not license the data. |

### Anomaly Datasets

[MIMII public 1.0](https://zenodo.org/records/3384388) is CC BY-SA 4.0 and contains valves, pumps, fans and slide rails at 16 kHz/16-bit with eight microphones and noise variants. IDs 00/02/04/06 describe product models; they are not verified repeated units of one product. Confirmed labels are normal/abnormal, not per-file fault causes. Keep channels and noise variants of each source together.

[DCASE 2025 Task 2](https://dcase.community/challenge2025/task-first-shot-unsupervised-anomalous-sound-detection-for-machine-condition-monitoring) uses normal-only training and domain changes. Each development section has 990 source-domain and ten target-domain normal training clips. Sections are metric subsets, not necessarily physical units. AUC/pAUC are not classification accuracy. The [development release](https://zenodo.org/records/15097779) is CC BY-NC-SA 4.0; additional/evaluation release rights were not audited. This is a separate objective with target-domain data requirements.

### Excluded Inputs

- [MCC5-THU gearbox v2](https://data.mendeley.com/datasets/p92gj2732w/2): primary description specifies vibration; no microphone channel verified.
- [3500-DEFault](https://data.mendeley.com/datasets/k22zxz29kr/1): simulated thermodynamic features, pressure and torsional vibration rather than microphone audio.
- [Vehicle Internal Combustion Engine Sounds](https://zenodo.org/records/18777405): CC BY 4.0 engine-type recordings, with no verified defect taxonomy. Type labels do not certify health.

## Before Another Experiment

1. Pin source version, license, allowed uses and file hashes. Keep source archives and private mappings outside Git.
2. Audit channels, rates, actual labels, quality and original acquisitions. Count segments, paired microphones and augmentations separately from independent units.
3. Define a taxonomy supported across units. Avoid assigning different classes to different datasets, which confounds source and condition.
4. Split physical units and original recordings before augmentation. If a fault occurs on only one unit, limit the claim and obtain replicated acquisitions.
5. Keep publisher truth sealed from operational inference/training. Record explicitly disclosed support labels and reserve independent confirmation data.
6. Report per-class errors, coverage, review effort, latency and total cost. Manufacturer deployment requires representative recordings with confirmed diagnoses and operating context.
