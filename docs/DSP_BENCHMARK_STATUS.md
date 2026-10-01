# State-Of-The-Art And Human Parity Are Not Established

**We do not know that the current pipeline is state of the art, and we have not measured whether it matches human experts.** Neither the pruning plateau nor a difficult listening example establishes an irreducible classification limit. The current results support comparisons between our own pipeline variants on consumed development data, not a ranking against the best published system or a human performance ceiling.

## Published Scores Require Matching Tasks And Information

A comparable benchmark would need the same dataset version, microphone-only input, class taxonomy, independent acquisition split, cross-regime conditions, reference or training-label budget, and permission to abstain. Our fixed-reference classification with excluded-class rejection differs from supervised closed-set classification, sound-event localization, multimodal diagnosis and same-recording segment splits. Accuracy, ROC-AUC, average precision and event F1 are not interchangeable measures.

| Checked source | Evidence | What it does not establish |
| --- | --- | --- |
| [Ottawa UOEMD-VAFCVS v2](https://data.mendeley.com/datasets/msxs4vj48g/2) | Eight motors, eight labeled conditions, eight constant/variable speed profiles, two load states; microphone and accelerometer channels are distinct | A comparable audio-only leaderboard or expert listening score on our split |
| [Jin motor acoustic dataset](https://data.mendeley.com/datasets/9dpmkgpncw/1) | Four conditions, three acquisition directions, PCB microphone and smartphone subsets with several noise conditions | A verified state-of-the-art result or blind human comparison on our selected files |
| [Spadini, Nose-Filho and Suyama, low-frequency acoustic fault diagnosis](https://arxiv.org/html/2411.06299v1) | Reports 99.54% accuracy on 42 MAFAULDA fault/severity classes using microphone-only features and supervised XGBoost; original files are split before training/test segmentation | Performance on Jin or Ottawa, one-reference classification, unknown rejection or an independent-machine ceiling; preprocessing/selection validation boundaries still matter |
| [Fedorishin et al., fine-grained engine fault sound-event detection](https://arxiv.org/html/2403.11037v1) | Audio-only macro ROC-AUC 0.7586, mAP 0.3384, segment F1 0.3449 and event F1 0.0979 on 2,643 audio/vibration recordings covering 232 vehicle models and ten event categories | A percentage accuracy comparable with our per-clip decisions or a measured human baseline |

The Ottawa publisher links [Selective embedding for deep learning](https://doi.org/10.1016/j.knosys.2025.114535). Its identity and dataset citation were verified through [Crossref metadata](https://api.crossref.org/works/10.1016/j.knosys.2025.114535), but the full publisher page was inaccessible. Its sensor-specific performance and split were therefore not verified and no numerical claim from that article is used here. This is a bounded source check, not an exhaustive survey proving that no directly comparable work exists.

## Expert Difficulty Is Plausible But Not Quantified For This Task

Fedorishin et al. describe engine-knock versus internal-tick examples that can confuse engine experts. That supports the possibility of genuine acoustic ambiguity. It is a qualitative observation about another dataset, not a blind expert error rate on Jin/Ottawa or evidence that our model has reached human performance.

Human listening performance also does not define an upper limit for a classifier. Numeric representations can expose repeatable structure that a listener does not perceive, while experienced mechanics may use context absent from our inputs. Models can also exploit acquisition or motor-identity artifacts that do not generalize as diagnostic evidence. A valid comparison must state what information each participant receives.

The existing review pages reveal the correct publisher class and model decision. They are inspection tools, not blind experiments. Listening through them cannot be counted as an unbiased human benchmark, and no human classification score has been collected.

## Measure The Missing Baselines Before Claiming A Ceiling

Freeze the task and previously unexposed acquisition groups first. Compare the selected pipeline with deterministic spectral matching and suitable supervised or pretrained-audio baselines under the same reference/label budget, evaluating wrong assignments, false rejections and automatic coverage separately. The current Jin spectral controls already demonstrate strong forced-class separation on the observed groups; that is not proof of added value from an LLM or of generalization to new machines.

For a human pilot, recruit multiple domain experts, hide query labels and model responses, randomize order, standardize reference examples and available metadata, and allow the same explicit abstention choices. Separate an information-matched diagrams/measurements condition from an audio-listening condition; the current model experiments received DSP images and numerical evidence, not the original audio waveform as an audio input. Measure per-class errors, abstentions, elapsed review time and inter-rater agreement, with acquisition-level uncertainty. A small pilot would reveal disagreements, not establish a universal human ceiling. This protocol is proposed only; no participants or judgments are fabricated.

## The Essential Review Shows The Tested Candidate Without Promoting It

[The archived v15 comparison](../examples/archive/pruning-candidate/index.html) shows the recorded triple-removal candidate: band power, autocorrelation and dominant-frequency tracking were removed from its inference inputs. It includes all eight primary decisions and both candidate repeats, including the wrong C06 assignment on D03. Correct-reference and model-choice buttons remain independent; Other disables model choice with an explicit reason while reference browsing remains available.

The interface shows only Welch, FFT, spectrogram and cepstrum plus the original audio and recorded outcome. The model received 23 retained diagram types; displaying four is an interface simplification, not a new four-diagram inference experiment. The candidate remains unapproved, its conflicting repeat is visible, and no new inference or clean final evaluation was performed to create the page.
