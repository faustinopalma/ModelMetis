# Human Audio Comparison

Open `outputs/audio-comparison-v4/index.html` to compare each evaluated input with its dataset references before revealing the publisher label or model decisions. The query stays on the left. The adjacent reference changes with its arrow buttons or the keyboard's left/right arrow keys. A playing reference keeps its playback position when changed. Input navigation has separate controls.

The page includes 20 Jin query windows, four Jin references, 16 Ottawa query acquisitions and eight Ottawa references from the labeled DSP experiments. Jin initially shows the twelve reserved-direction windows; the set selector also exposes development and all evaluated inputs. Query order is deterministically shuffled independently of labels, and anonymous sample numbers remain stable across filters.

## Compare And Record

Use Play input and Play reference for single-source audition. The shared timeline, interval bounds, loop, speed and volume apply to both. A/B automatically alternates the chosen interval between the input and current reference. All audio uses the exact registered WAV bytes. FFT, Welch PSD, spectrogram, bands, envelope and autocorrelation views use the original verified figures, displayed side by side; the expand buttons open a larger view.

Choose a reference condition, Different from all, or Unsure. Record choice locks the first answer and observations for that input. Reveal result then shows the publisher label and stored model decisions from trials with the full reference set. Answers, observations, evidence views and audition counts are stored locally in the browser. Results summarizes recorded and revealed cases separately; Export produces a JSON file with audio hashes and the recorded decisions. Unrevealed truth remains null in the export. Browser storage restrictions are reported explicitly, and export remains available.

Keyboard arrows leave text, number, range and selection controls to their native behavior while those controls have focus. Page Up and Page Down navigate input samples outside editable controls. Figure dialogs and result dialogs suspend comparison shortcuts.

## Scope And Integrity

Every WAV, figure, report provenance and experiment registration is hash-checked during generation. The page is self-contained and makes zero model calls. Original audio is peak-normalized as documented by the dataset importers. Human performance here concerns previously used query windows and their supplied references; repeated windows from the same acquisition remain dependent. Label hiding operates in the interface: the local HTML source includes the answer data. This is a personal comparison aid with recorded choices.

The HTML includes all audio and original figures and is approximately 140 MB. Keep the complete file available when opening it locally. The generator reuses the installed React, React DOM and Lucide React packages in the console workspace to embed icons; the generated page has no runtime dependency on those packages or a server.

```powershell
.\.venv\Scripts\python.exe -m scripts.audio_comparison --output outputs/audio-comparison-new
.\.venv\Scripts\python.exe -m pytest -q tests/test_audio_comparison.py
```

Use a new output directory to preserve previous generated pages. Audio, embedded truth, exported judgments and browser-test artifacts stay outside the public repository.