# Human Audio Comparison

Open `outputs/audio-comparison-v8/index.html` to check each input against the reference for its correct publisher class. The class is always visible above the input, and selecting a sample automatically selects its matching reference. The adjacent reference changes with its arrow buttons or the keyboard's left/right arrow keys. Its status shows whether it matches the correct class; the checkmark button returns directly to that reference. A playing reference keeps its playback position when changed. Input navigation has separate controls.

The page includes 20 Jin query windows, four Jin references, 16 Ottawa query acquisitions and eight Ottawa references from the labeled DSP experiments. Jin initially shows the twelve reserved-direction windows; the set selector also exposes development and all evaluated inputs. Query order is deterministically shuffled independently of labels, and anonymous sample numbers remain stable across filters.

## Compare And Review

Model errors are highlighted above the input and in the automatically expanded model-decision details, with expected and observed classes for each trial. Wrong class and False rejection count as classification errors; Technical failure is shown separately. The Trial selector limits the comparison to a specific round and phase, while All trials highlights a sample if any included trial is wrong. Counts use unique samples evaluated by the selected trials. Model errors only filters the sample list, and Next model error jumps directly to the next affected sample. A trial with zero classification errors shows an explicit empty state when filtering is enabled. The correct class and matching reference remain visible throughout review.

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

Use a new output directory to preserve previous generated pages. Audio, embedded truth, exported judgments and browser-test artifacts stay outside the public repository.