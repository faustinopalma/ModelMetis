import io
import struct
import wave
from dataclasses import asdict, dataclass, field


class InvalidAudio(ValueError):
    pass


@dataclass(frozen=True)
class ModelAudioInput:
    sample_id: str
    wav_bytes: bytes = field(repr=False)


@dataclass(frozen=True)
class AudioMetadata:
    sample_rate: int
    channels: int
    bits_per_sample: int
    frames: int
    duration_seconds: float
    byte_length: int

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def inspect_wav(payload: bytes, max_bytes: int) -> AudioMetadata:
    if not payload or len(payload) > max_bytes:
        raise InvalidAudio("Audio is empty or exceeds the upload limit.")
    if len(payload) < 44 or payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
        raise InvalidAudio("Upload a RIFF/WAVE file with integer PCM audio.")
    if struct.unpack_from("<I", payload, 4)[0] != len(payload) - 8:
        raise InvalidAudio("The RIFF length does not match the uploaded bytes.")

    offset = 12
    format_values = None
    data_length = None
    chunk_count = 0
    while offset < len(payload):
        chunk_count += 1
        if chunk_count > 4096 or offset + 8 > len(payload):
            raise InvalidAudio("Invalid WAV chunk structure.")
        chunk_type = payload[offset : offset + 4]
        chunk_size = struct.unpack_from("<I", payload, offset + 4)[0]
        start = offset + 8
        end = start + chunk_size
        if end > len(payload):
            raise InvalidAudio("A WAV chunk is truncated.")
        if chunk_type == b"fmt ":
            if format_values is not None or chunk_size not in (16, 18):
                raise InvalidAudio("Only a single standard PCM format chunk is supported.")
            if chunk_size == 18 and payload[start + 16 : end] != b"\x00\x00":
                raise InvalidAudio("Extended WAV formats are not supported.")
            format_values = struct.unpack_from("<HHIIHH", payload, start)
        elif chunk_type == b"data":
            if format_values is None or data_length is not None:
                raise InvalidAudio("WAV requires one data chunk after the format chunk.")
            data_length = chunk_size
        offset = end if end == len(payload) else end + (chunk_size % 2)

    if format_values is None or data_length is None or offset != len(payload):
        raise InvalidAudio("WAV format or audio data is missing.")
    encoding, channels, sample_rate, byte_rate, block_align, bits = format_values
    if encoding != 1 or channels not in (1, 2) or bits not in (8, 16, 24, 32):
        raise InvalidAudio("Use mono or stereo integer PCM WAV at 8, 16, 24, or 32 bits.")
    if not 8000 <= sample_rate <= 192000:
        raise InvalidAudio("Sample rate must be between 8,000 and 192,000 Hz.")
    if block_align != channels * (bits // 8) or byte_rate != sample_rate * block_align:
        raise InvalidAudio("PCM block alignment or byte rate is invalid.")
    if data_length == 0 or data_length % block_align:
        raise InvalidAudio("PCM must contain complete, nonempty sample frames.")
    frames = data_length // block_align
    duration = frames / sample_rate
    if duration > 120:
        raise InvalidAudio("Recordings may be at most 120 seconds long.")
    try:
        with wave.open(io.BytesIO(payload), "rb") as audio:
            if audio.getnframes() != frames or len(audio.readframes(frames)) != data_length:
                raise InvalidAudio("The declared PCM frame count is inconsistent.")
    except (wave.Error, EOFError) as error:
        raise InvalidAudio("WAV could not be decoded as integer PCM.") from error
    return AudioMetadata(sample_rate, channels, bits, frames, duration, len(payload))


def canonical_wav(payload: bytes, max_bytes: int) -> bytes:
    metadata = inspect_wav(payload, max_bytes)
    with wave.open(io.BytesIO(payload), "rb") as source:
        frames = source.readframes(metadata.frames)
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(metadata.channels)
        target.setsampwidth(metadata.bits_per_sample // 8)
        target.setframerate(metadata.sample_rate)
        target.writeframes(frames)
    return output.getvalue()