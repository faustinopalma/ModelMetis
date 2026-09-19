import io
import json
import math
import wave
from collections.abc import Sequence

import numpy as np
from scipy.signal import find_peaks, resample_poly, welch
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from modelmetis.audio import ModelAudioInput
from modelmetis.learning import SilverExample, TeacherDecision, TeacherRequest, training_targets


def waveform(audio: ModelAudioInput, target_rate: int = 48000) -> np.ndarray:
    with wave.open(io.BytesIO(audio.wav_bytes), "rb") as source:
        if source.getsampwidth() != 2 or source.getnchannels() != 1:
            raise ValueError("Experiment models require mono PCM16.")
        rate = source.getframerate()
        signal = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2")
    signal = signal.astype(np.float32) / 32768.0
    divisor = math.gcd(rate, target_rate)
    return resample_poly(signal, target_rate // divisor, rate // divisor).astype(np.float32)


def spectral_features(audio: ModelAudioInput) -> np.ndarray:
    signal = waveform(audio)
    frequencies, power = welch(signal, fs=48000, nperseg=min(4096, len(signal)))
    edges = np.geomspace(20, 20000, 49)
    bands = [float(power[(frequencies >= lower) & (frequencies < upper)].sum())
             for lower, upper in zip(edges[:-1], edges[1:], strict=True)]
    return np.log10(np.maximum(bands, 1e-12))


def fit_specialist(examples: Sequence[SilverExample]):
    labels = training_targets(examples)
    features = np.stack([spectral_features(example.audio) for example in examples])
    classifier = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=17))
    classifier.fit(features, labels)
    return classifier


def normalize_audio(audio: ModelAudioInput) -> tuple[ModelAudioInput, dict]:
    with wave.open(io.BytesIO(audio.wav_bytes), "rb") as recording:
        if recording.getnchannels() != 1 or recording.getsampwidth() != 2:
            raise ValueError("Normalization requires mono PCM16.")
        rate = recording.getframerate()
        signal = np.frombuffer(recording.readframes(recording.getnframes()), dtype="<i2")
    values = signal.astype(np.float64)
    centered = values - values.mean()
    peak = float(np.max(np.abs(centered)))
    gain = 0.95 * 32767 / peak if peak else 1.0
    pcm = np.rint(centered * gain).astype("<i2")
    content = io.BytesIO()
    with wave.open(content, "wb") as recording:
        recording.setparams((1, 2, rate, len(pcm), "NONE", "not compressed"))
        recording.writeframes(pcm.tobytes())
    return ModelAudioInput(audio.sample_id, content.getvalue()), {
        "method": "dc-peak-v1", "gain": gain, "source_dc_pcm": float(values.mean()),
    }


def acoustic_summary(audio: ModelAudioInput) -> dict:
    signal = waveform(audio).astype(np.float64)
    frequencies, power = welch(signal, fs=48000, nperseg=min(48000, len(signal)))
    valid = (frequencies >= 20) & (frequencies <= 20000)
    total = float(power[valid].sum())
    mean_square = float(np.mean(signal ** 2))
    peaks, _ = find_peaks(power)
    peaks = [int(index) for index in peaks if valid[index]]
    peaks = sorted(peaks, key=lambda index: power[index], reverse=True)[:8]
    maximum = max((float(power[index]) for index in peaks), default=0)
    edges = (20, 100, 300, 1000, 3000, 8000, 20000)
    bands = {f"{lower}-{upper}": round(float(power[
        (frequencies >= lower) & (frequencies < upper)
    ].sum()) / total, 6) if total else 0
             for lower, upper in zip(edges[:-1], edges[1:], strict=True)}
    return {
        "representation": "audio-statistics-v1", "duration_seconds": len(signal) / 48000,
        "frequency_resolution_hz": float(frequencies[1] - frequencies[0]),
        "amplitude_note": "Relative normalized PCM amplitudes, not calibrated sound pressure.",
        "crest_factor": round(float(np.max(np.abs(signal))) / np.sqrt(mean_square), 4)
        if mean_square else 0,
        "excess_kurtosis": round(float(np.mean(signal ** 4)) / mean_square ** 2 - 3, 4)
        if mean_square else 0,
        "spectral_centroid_hz": round(float(np.sum(frequencies[valid] * power[valid])) / total, 2)
        if total else 0,
        "spectral_flatness": round(float(np.exp(np.mean(np.log(np.maximum(power[valid], 1e-30))))
                                         / np.mean(power[valid])), 6) if total else 0,
        "energy_fraction_by_band_hz": bands,
        "strongest_local_spectral_peaks": [
            {"frequency_hz": float(frequencies[index]),
             "relative_db": round(float(10 * np.log10(power[index] / maximum)), 2)}
            for index in peaks if maximum > 0
        ],
    }


class ClapTeacher:
    model_id = "laion/clap-htsat-unfused"

    def __init__(self, revision: str):
        import torch
        from transformers import ClapModel, ClapProcessor

        valid_sha = all(character in "0123456789abcdef" for character in revision)
        if len(revision) != 40 or not valid_sha:
            raise ValueError("Pin the teacher to a full model revision SHA.")
        torch.set_num_threads(4)
        self.torch = torch
        self.processor = ClapProcessor.from_pretrained(self.model_id, revision=revision)
        self.model = ClapModel.from_pretrained(self.model_id, revision=revision).eval()
        self.teacher_id = f"{self.model_id}@{revision}"

    def __call__(self, request: TeacherRequest) -> TeacherDecision:
        descriptions = json.loads(request.prompt)
        if set(descriptions) != set(request.taxonomy):
            raise ValueError("Prompt descriptions must match the taxonomy.")
        inputs = self.processor(
            text=[descriptions[label] for label in request.taxonomy],
            audio=waveform(request.audio), sampling_rate=48000,
            return_tensors="pt", padding=True,
        )
        with self.torch.inference_mode():
            scores = self.model(**inputs).logits_per_audio.softmax(dim=-1)[0]
        index = int(scores.argmax())
        return TeacherDecision(request.taxonomy[index], float(scores[index]))
