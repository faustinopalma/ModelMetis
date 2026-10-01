# Human Audio Comparison

**Open [the simple-method comparison](../examples/audio-comparison/index.html) to listen to every recorded decision of the central method beside its references.** It holds 48 decisions in three separately reported collections, all eight model-facing figures per recording, original audio, publisher labels, the recorded explanation, the exact model input and deep links such as `index.html#jin-distances-excluded-T04`. [Its guide](../examples/audio-comparison/README.md) explains the controls; the generator is [publish_simple_method.py](../scripts/publish_simple_method.py).

The pages below are earlier local workbenches and the archived pruning review. Open [the archived v15 essential comparison](../examples/archive/pruning-candidate/index.html) for the latest tested triple-pruned candidate. It shows four retained diagrams, original audio, publisher truth, recorded model choice and direct correct/model reference buttons. All eight primary decisions and both repeats are preserved, including the unsafe D03 repeat and an explicit disagreement warning. The candidate removed bands, autocorrelation and dominant-frequency tracking from inference, but remains unapproved. The model received 23 diagram types; the four-diagram display does not change that pipeline. [Benchmark status](DSP_BENCHMARK_STATUS.md) explains why this truth-visible review is not a blind human test and why state-of-the-art or human parity is unestablished.

Open the v14 comparison (local source: `outputs/audio-comparison-v14/index.html`) for simplified review of the recorded AI decisions. All 14 errors appear by default: 12 unacceptable class assignments and two false rejections that would route to human review. The remaining 10 of 24 decisions are correct. Human intervention was not executed. Each case has exactly one AI response; Set, Trial and numerical-control selectors are absent.

The right pane has Correct reference and Model choice buttons with explicit class labels. Model choice initially selects the assigned class. When the response is Other, its button is disabled and the adjacent explanation states that the model selected no reference; the pane shows the correct publisher-class reference instead. Correct reference and both reference arrows remain available. Changing references preserves the input, its result and active playback position. The chosen mode follows subsequent cases where possible, and both diagrams remain aligned.

Collection selects Jin, Ottawa or both. Show selects All errors, Wrong assignments, Other / review errors or All decisions; previous/next case respects these filters. Counts distinguish shown decisions from the collection denominator. Both known-class and excluded-class decisions appear directly in the comparison: twelve input recordings each have two decisions. In excluded-class cases the correct publisher-class reference was withheld from the model and the expected response is Other. That reference remains available for human inspection and is explicitly marked as withheld; browsing it does not imply the model saw it. Correct Other responses remain correct decisions, not errors.

Detailed AI results (local source: `outputs/audio-comparison-v14/results.html`) provide explanations and exact request/response links; the model prompt (local source: `outputs/audio-comparison-v14/prompt.txt`) is the actual transmitted system prompt. The [extension report](DSP_EXTENSIONS.md) records measurements and limitations. All 26 diagrams remain available in one selector: four core views followed by the additional analyses. Play input, Play reference, shared audio controls, Loop, A/B and enlargement remain available. V14 contains twelve query recordings and twelve references, embeds the original WAV/PNG bytes, requires no server and makes no model calls. It does not write review notes or alter notes saved in earlier versions.

Generate a new simplified output with:

```powershell
.\.venv\Scripts\python.exe -m scripts.dsp_extended_review --source outputs/dsp-extended-v1 --ai-source outputs/dsp-extended-ai-v4 --output outputs/audio-comparison-new --simple
.\.venv\Scripts\python.exe -m pytest -q tests/test_audio_comparison.py tests/test_dsp_extensions.py
```

## Extended Review Remains Available

The v13 workbench retains Set, Trial, numerical controls and review notes for the broader 36-query collection. Its side-by-side view contains known-class AI decisions only; excluded-class results remain in its results page. The following workflow describes the extended v8-v13 pages, which remain unchanged.

Open `outputs/audio-comparison-v8/index.html` to check each input against the reference for its correct publisher class. The class is always visible above the input, and selecting a sample automatically selects its matching reference. The adjacent reference changes with its arrow buttons or the keyboard's left/right arrow keys. Its status shows whether it matches the correct class; the checkmark button returns directly to that reference. A playing reference keeps its playback position when changed. Input navigation has separate controls.

The page includes 20 Jin query windows, four Jin references, 16 Ottawa query acquisitions and eight Ottawa references from the labeled DSP experiments. Jin initially shows the twelve reserved-direction windows; the set selector also exposes development and all evaluated inputs. Query order is deterministically shuffled independently of labels, and anonymous sample numbers remain stable across filters.

## Compare And Review

Wrong class and false rejection remain distinct measured errors. A wrong known assignment or an acceptance when its class is excluded is operationally unacceptable. A false rejection is diagnostically incorrect but acceptable in direction under the proposed `different`-to-human policy. Technical failures and unavailable analyses are neither successful escalation nor classification. The Trial selector limits results to one trial; All trials can contain several decisions per sample, and a sample may match both error-type filters when different trials disagree. Per-decision counts and unique-sample filter counts have separate denominators. The correct publisher class and matching reference remain visible.

Use Play input and Play reference for single-source audition. The shared timeline, interval bounds, loop, speed and volume apply to both. A/B automatically alternates the chosen interval between the input and current reference. All audio uses the exact registered WAV bytes. FFT, Welch PSD, spectrogram, bands, envelope and autocorrelation views use the original verified figures, displayed side by side; the expand buttons open a larger view.

The class and matching reference are available immediately. Observations and the Reviewed checkbox are optional and remain editable. Model decisions from trials with the full reference set are available in a collapsible section. Review notes summarizes saved observations and reviewed samples; Export produces a JSON file with publisher labels, audio hashes and review notes. Browser storage restrictions are reported explicitly, and export remains available. Review storage is separate from previous classification-exercise answers, which remain intact in the earlier page.

Keyboard arrows leave text, number, range and selection controls to their native behavior while those controls have focus. Page Up and Page Down navigate input samples outside editable controls. Figure dialogs and review dialogs suspend comparison shortcuts.

## Scope And Integrity

Every WAV, figure, report provenance and experiment registration is hash-checked during generation. The page is self-contained and makes zero model calls. Original audio is peak-normalized as documented by the dataset importers. Labels come from the registered publisher annotations. Repeated windows from the same acquisition remain dependent. This is a labeled comparison aid for checking whether a sample resembles its assigned reference.

The HTML includes all audio and original figures and is approximately 140 MB. Keep the complete file available when opening it locally. The generator reuses the installed React, React DOM and Lucide React packages in the console workspace to embed icons; the generated page has no runtime dependency on those packages or a server.

```powershell
.\.venv\Scripts\python.exe -m scripts.audio_comparison --output outputs/audio-comparison-new
.\.venv\Scripts\python.exe -m pytest -q tests/test_audio_comparison.py
```

Use a new output directory to preserve previous generated pages. The complete local collection and browser-test artifacts remain ignored. Only the explicitly curated consumed examples, labels and recorded decisions are released under the [publication policy](PUBLICATION.md).
