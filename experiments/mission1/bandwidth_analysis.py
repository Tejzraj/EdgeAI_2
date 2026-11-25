from pathlib import Path
import csv
import math

import matplotlib.pyplot as plt

OUT = Path("results/graphs")
REPORT = Path("results/reports")
OUT.mkdir(parents=True, exist_ok=True)
REPORT.mkdir(parents=True, exist_ok=True)

SAMPLE_RATES = [16000, 8000]
FORMATS = {
    "float32": 4,
    "int16": 2,
    "int8": 1,
}
BAUD_RATES = [115200, 921600, 2000000]
PACKET_SIZES = [8, 64, 320, 1024]

# Audio bandwidth calculations
audio_rows = []

for fs in SAMPLE_RATES:
    for fmt, bytes_per_sample in FORMATS.items():
        if fs == 8000 and fmt == "float32":
            continue

        rate = fs * bytes_per_sample
        audio_rows.append({
            "sample_rate_hz": fs,
            "format": fmt,
            "bytes_per_sample": bytes_per_sample,
            "payload_bytes_per_second": rate,
        })

# UART theoretical capacity
uart_rows = []

for baud in BAUD_RATES:
    capacity = baud / 10

    for row in audio_rows:
        total = row["payload_bytes_per_second"]
        uart_rows.append({
            "baud": baud,
            "capacity_bytes_per_second": capacity,
            "sample_rate_hz": row["sample_rate_hz"],
            "format": row["format"],
            "required_bytes_per_second": total,
            "fits_theoretically": total <= capacity,
        })

# Packet overhead: 16 kHz int16, one second
packet_rows = []
fs = 16000
bytes_per_sample = 2
samples_total = fs
payload_total = samples_total * bytes_per_sample

for samples_per_packet in PACKET_SIZES:
    packet_count = math.ceil(samples_total / samples_per_packet)
    overhead = packet_count * 13
    total = payload_total + overhead

    packet_rows.append({
        "samples_per_packet": samples_per_packet,
        "packets_per_second": packet_count,
        "audio_payload_bytes": payload_total,
        "protocol_overhead_bytes": overhead,
        "total_bytes_per_second": total,
        "overhead_percent": 100 * overhead / total,
    })

# Feature return: 16 kHz, hop=320, 40 float32 features
feature_rows = []

for mels in [40, 13]:
    for hop in [320, 160]:
        frames_per_second = 16000 / hop
        feature_payload = 8 + 4 * mels
        total_frame_bytes = 13 + feature_payload

        feature_rows.append({
            "mels_or_mfcc": mels,
            "hop_samples": hop,
            "frames_per_second": frames_per_second,
            "bytes_per_frame": total_frame_bytes,
            "bytes_per_second": frames_per_second * total_frame_bytes,
        })

# CSV writer
def write_csv(filename, rows):
    path = REPORT / filename
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {path}")

write_csv("audio_bandwidth.csv", audio_rows)
write_csv("uart_feasibility.csv", uart_rows)
write_csv("packet_overhead.csv", packet_rows)
write_csv("feature_return_bandwidth.csv", feature_rows)

# Graph 1: audio data rates
plt.figure(figsize=(9, 5))
labels = [f"{r['sample_rate_hz']//1000} kHz\n{r['format']}" for r in audio_rows]
values = [r["payload_bytes_per_second"] / 1000 for r in audio_rows]
plt.bar(labels, values)
plt.ylabel("Bandwidth (kB/s)")
plt.title("Audio Format vs Required Bandwidth")
plt.tight_layout()
plt.savefig(OUT / "audio_bandwidth.png", dpi=180)
plt.close()

# Graph 2: UART capacity and audio requirements
plt.figure(figsize=(9, 5))
x = range(len(BAUD_RATES))
width = 0.2

for i, row in enumerate(audio_rows):
    plt.bar(
        [v + i * width for v in x],
        [row["payload_bytes_per_second"] / 1000] * len(x),
        width,
        label=f"{row['sample_rate_hz']//1000} kHz {row['format']}"
    )

plt.plot(
    [v + width * 2 for v in x],
    [b / 10000 for b in BAUD_RATES],
    marker="o",
    label="UART capacity"
)
plt.xticks([v + width for v in x], [str(b) for b in BAUD_RATES])
plt.xlabel("UART baud rate")
plt.ylabel("Bandwidth (kB/s)")
plt.title("Audio Requirements vs UART Capacity")
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "uart_feasibility.png", dpi=180)
plt.close()

# Graph 3: packet overhead
plt.figure(figsize=(8, 5))
plt.plot(
    [r["samples_per_packet"] for r in packet_rows],
    [r["total_bytes_per_second"] for r in packet_rows],
    marker="o"
)
plt.xlabel("Samples per packet")
plt.ylabel("Total bytes per second")
plt.title("Packet Size vs Transmission Bandwidth")
plt.grid(True)
plt.tight_layout()
plt.savefig(OUT / "packet_overhead.png", dpi=180)
plt.close()

print("\n========== AUDIO BANDWIDTH ==========")
for row in audio_rows:
    print(row)

print("\n========== UART CAPACITY ==========")
for baud in BAUD_RATES:
    print(f"{baud:>8} baud = {baud/10:,.0f} B/s theoretical")

print("\n========== PACKET OVERHEAD ==========")
for row in packet_rows:
    print(row)

print("\n========== FEATURE RETURN ==========")
for row in feature_rows:
    print(row)

print("\nAll theoretical experiments completed.")
