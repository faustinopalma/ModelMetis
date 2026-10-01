# Registered Simple-Method Code

**These files are the exact code versions recorded by the simple-method experiments; do not edit or import them.** The runner and similarity validator in `scripts/` and `src/` kept evolving after registration. These copies were recovered from local editor history by matching the SHA-256 hashes recorded in the experiment registrations and request bundles, up to line endings.

| File | Recorded use | SHA-256 prefix |
| --- | --- | --- |
| [evaluate_dsp_similarity.2ac67808.py](evaluate_dsp_similarity.2ac67808.py) | Ottawa v1 registration runner; all attempts ended in technical failures | `2ac67808` |
| [evaluate_dsp_similarity.3e091303.py](evaluate_dsp_similarity.3e091303.py) | Ottawa v2 registration runner; configuration A | `3e091303` |
| [evaluate_dsp_similarity.e5279d81.py](evaluate_dsp_similarity.e5279d81.py) | Jin registration runner; configurations A, B and C | `e5279d81` |
| [dsp_similarity.fb79c3c6.py](dsp_similarity.fb79c3c6.py) | Similarity module of Ottawa v1 round 1 | `fb79c3c6` |
| [dsp_similarity.a2fc5dc4.py](dsp_similarity.a2fc5dc4.py) | Similarity module of Jin rounds 2 and 3; configurations B and C | `a2fc5dc4` |

Two recorded similarity-module versions were not recovered: `195c8f1c`, used by configuration A on Jin and Ottawa, and `9723e9f6`, used by Ottawa v1 rounds 2 and 3. Their exact transmitted requests and responses remain the evidence. The registration hash identifies the runner at registration; later rounds of the same study can have run with subsequent edits that were not separately recorded.

The committed DSP report code ([dsp.py](../../src/modelmetis/dsp.py), [dsp_report.py](../../src/modelmetis/dsp_report.py), decoder in [visual_audio.py](../../src/modelmetis/visual_audio.py)) and transport helpers ([dsp_inference.py](../../src/modelmetis/dsp_inference.py)) are byte-identical to the recorded versions. The publisher writes this binding table to [simple-method-summary.json](../../examples/results/simple-method-summary.json) and recomputes it from the local registrations each time it runs.
