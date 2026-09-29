# EXP-010: Audio embedding similarity

## Question and boundaries

Test whether embedding similarity retrieves the same publisher condition, and compare it with maneuver and drone identity. This is exploratory development analysis. C, new human labels, fitting, taxonomy changes, threshold selection and promotion are excluded.

The frozen EXP-009 package supplies nine A references and 54 B queries, one B recording for each of nine conditions and six maneuvers. These are half-second, 16 kHz mono recordings, not independent machines. The existing A labels remain in the validated support manifest but are not used for embedding extraction, clustering or retrieval. Only the isolated evaluator reads the 54 query labels. No recordings are concatenated or repeated to simulate longer acquisitions.

## Fixed geometry analysis

L2-normalize each embedding. Within B, rank all other B recordings by cosine similarity, exclude self, and use stable input order to resolve exact ties. Report same-condition and same-maneuver precision at 1, 5 and 10, full-ranking mean average precision, and pairwise cosine-similarity ROC-AUC. The random-neighbor match rates are 5/53 for condition and 8/53 for maneuver. There is no hypothesis test because recordings and pairwise comparisons are dependent.

Fit HDBSCAN to normalized B embeddings with Euclidean distance, min_cluster_size=5, min_samples=3 and allow_single_cluster=False. Do not prescribe nine clusters or tune parameters using labels. Report cluster sizes, unassigned recordings, pair precision and recall excluding unassigned pairs, plus ARI/AMI with noise treated as one label (explicitly named). A cluster is not a gold diagnosis. Density membership is not calibrated diagnostic confidence.

For each B recording also rank the combined A/B collection excluding self, and report the fraction of B neighbors. Report the 53/62 random baseline because A/B is strongly imbalanced. Device and drone model are confounded. This statistic cannot identify a causal machine effect independently of other acquisition differences.

Write all neighbor rankings and cluster assignments to ignored immutable artifacts before loading the sealed labels. Hash-bind source attempts, embedding files, identities, manifests, decisions and evaluator source. Store aggregate results without source paths or sample IDs in the repository. Preserve failed attempts.

## Baseline execution

The first execution used the saved FISHER-small, ECHO-small and EAT-base30 embeddings. Fixed parameters were implemented and synthetic positive, permuted-label negative and self-neighbor checks passed before evaluating these embeddings. Artifacts: `artifacts/geometry-base-v1`. These results were observed before selecting the larger model families; they were not used to tune their preprocessing or clustering.

## Larger candidate registration

1. EAT-large epoch20 pretrain: `worstchan/EAT-large_epoch20_pretrain`, revision `1109aaae544915a2b82182c643c1894b1b4d9f27`, MIT. Hugging Face reports 308,867,072 stored parameters. Reuse the existing EAT adapter: 16 kHz, DC removal, published 128-bin Kaldi features, 1024-frame padding/truncation and normalization, last-layer non-CLS mean pooling. This controls the adapter but not the training duration (base30 versus large20), so it is not a pure parameter-count experiment.
2. Dasheng-1.2B: `mispeech/dasheng-1.2B`, revision `e830b3b0014affc8447a9c15d18bb196a747137f`, Apache-2.0. Hugging Face reports 1,134,047,488 stored parameters. Published pretraining: 272,356 hours of general audio including AudioSet, VGGSound, MTG-Jamendo and ACAV100M. Use its own 16 kHz feature extractor, DC removal, natural half-second length and last-layer temporal mean. Use raw hidden states, not the HF wrapper's sigmoid-transformed logits. This compares a different model and corpus, not size alone.

Use existing x64 CPU runtime, float32, four PyTorch threads and seed 17. Download only pinned safetensors, configuration and source; inspect custom code before execution. Validate exact weight loading and finite nonzero embeddings. Run the same half-second synthetic probe twice and require identical vectors before any real-audio extraction. A process gets 600 seconds; timeouts and incompatibilities are retained rather than silently changing precision, duration, pooling or sample selection. Downloads, probes and extraction are separately recorded. No cloud resources or paid API calls are required.

## Source discovery record

The initial guessed URLs `worstchan/EAT-large_epoch10_pretrain` and `m-a-p/Dasheng1.2B` returned HTTP 401; these were incorrect repository addresses, not failures of the selected models. The official EAT repository and Hugging Face author inventory resolved epoch20, and the official Dasheng repository resolved `mispeech/dasheng-1.2B`. Correct metadata endpoints succeeded before downloading. No checkpoint from a guessed address was executed.

Sources: [EAT official repository](https://github.com/cwx-worst-one/EAT), [EAT-large model card](https://huggingface.co/worstchan/EAT-large_epoch20_pretrain), [Dasheng official repository](https://github.com/XiaoMi/dasheng), [Dasheng model card](https://huggingface.co/mispeech/dasheng-1.2B), [HDBSCAN](https://hdbscan.readthedocs.io/en/latest/how_hdbscan_works.html).
