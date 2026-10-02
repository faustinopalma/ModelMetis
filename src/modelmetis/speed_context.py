"""Speed context for DSP comparisons: order-axis spectra and speed-matched recordings."""

import io
from fractions import Fraction

import matplotlib
import numpy as np
from PIL import Image
from scipy import signal

matplotlib.use("Agg")

SPEED_GUIDANCE = (
    "Operating context: the supplied context states the shaft rotation frequency of every "
    "report, and speeds differ between reports. Components locked to rotation, such as shaft "
    "harmonics, imbalance, misalignment and bearing defect frequencies, scale in proportion to "
    "shaft speed: compare them in orders, frequency divided by shaft frequency, using each "
    "report's order-axis figure. Components fixed in hertz, such as structural resonances, "
    "electrical lines and the microphone response, stay at the same frequency when speed "
    "changes. Overall level and broadband shape can also change with speed."
)
MATCHED_GUIDANCE = (
    "Speed matching: every reference recording was resampled before analysis so that its shaft "
    "frequency equals the unknown recording's shaft frequency. In the reference reports, "
    "components locked to rotation therefore appear at the frequencies they would have at the "
    "unknown recording's speed and can be compared directly in hertz. Components fixed in hertz "
    "in the original reference, such as resonances and electrical lines, are displaced by the "
    "same factor, and durations change by its inverse. The operating context lists each "
    "reference's original and matched shaft frequency."
)


def match_speed(samples, rate, source_hz, target_hz, max_denominator=2000):
    """Resample so rotation-locked frequencies move from source_hz to target_hz at the same rate."""
    if source_hz <= 0 or target_hz <= 0:
        raise ValueError("Shaft frequencies must be positive.")
    factor = Fraction(source_hz / target_hz).limit_denominator(max_denominator)
    matched = signal.resample_poly(np.asarray(samples, dtype=float), factor.numerator,
                                   factor.denominator)
    return matched, factor.denominator / factor.numerator


def welch_db(samples, rate, nperseg):
    samples = np.asarray(samples, dtype=float)
    frequencies, power = signal.welch(samples - samples.mean(), rate, nperseg=nperseg)
    return frequencies, 10 * np.log10(np.maximum(power, power.max() * 1e-12))


def png(figure):
    import matplotlib.pyplot as plt

    stream = io.BytesIO()
    figure.savefig(stream, format="png", dpi=100)
    plt.close(figure)
    with Image.open(io.BytesIO(stream.getvalue())) as image:
        clean = io.BytesIO()
        image.convert("RGB").save(clean, format="PNG")
    return clean.getvalue()


def order_figure(samples, rate, shaft_hz, nperseg=32768):
    import matplotlib.pyplot as plt

    frequencies, level = welch_db(samples, rate, nperseg)
    orders = frequencies / shaft_hz
    figure, axes = plt.subplots(2, 1, figsize=(12, 7))
    near = orders <= 20
    axes[0].plot(orders[near], level[near], lw=0.8, color="#0078d4")
    axes[0].set(xlim=(0, 20), xlabel="Order (frequency / shaft frequency)", ylabel="dB",
                title=f"Welch spectrum on an order axis, shaft {shaft_hz:.3f} Hz")
    axes[0].set_xticks(range(0, 21))
    axes[0].grid(alpha=0.3)
    wide = (orders >= 0.5) & (orders <= 300)
    axes[1].semilogx(orders[wide], level[wide], lw=0.6, color="#0078d4")
    axes[1].set(xlim=(0.5, 300), xlabel="Order, logarithmic", ylabel="dB")
    axes[1].grid(alpha=0.3, which="both")
    figure.tight_layout()
    return png(figure)


def add_speed_context(messages, reports, shaft_hz, samples, rate, canonical):
    """Extend a simple-method request with shaft speeds, order figures and their guidance.

    `reports` maps transmitted report IDs (R01, Q01, ...) to packed reports whose evidence lists
    gain the order-figure IDs; `shaft_hz` and `samples` use the same keys.
    """
    import base64

    messages[0]["content"] += " " + SPEED_GUIDANCE
    parts, context = [], {}
    for identifier, report in reports.items():
        figure_id = f"{identifier}.O001"
        report["evidence_ids"].append(figure_id)
        context[identifier] = {"shaft_hz": round(shaft_hz[identifier], 3),
                               "rpm": round(60 * shaft_hz[identifier], 1)}
        payload = order_figure(samples[identifier], rate, shaft_hz[identifier])
        parts.extend([
            {"type": "text", "text": f"{figure_id}: Welch spectrum on an order axis"},
            {"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(payload).decode(),
                "detail": "high"}}])
    content = messages[1]["content"]
    content.append({"type": "text", "text": canonical(
        {"operating_context": context,
         "order_figures": [f"{identifier}.O001" for identifier in reports]}).decode()})
    content.extend(parts)
    return messages
