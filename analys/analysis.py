import csv
import glob
import math
import os
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


def shannon_entropy(bits):
    n = len(bits)
    if n == 0:
        return 0.0
    ones = sum(bits)
    zeros = n - ones
    p0 = zeros / n
    p1 = ones / n
    ent = 0.0
    if p0 > 0:
        ent -= p0 * math.log2(p0)
    if p1 > 0:
        ent -= p1 * math.log2(p1)
    return ent


def autocorrelation(bits, lag=1):
    n = len(bits) - lag
    if n <= 0:
        return 0.0
    mean = sum(bits) / len(bits)
    den = sum((b - mean) ** 2 for b in bits)
    if den == 0:
        return 0.0
    num = sum((bits[i] - mean) * (bits[i + lag] - mean) for i in range(n))
    return num / den


def von_neumann_extract(bits):
    extracted = []
    for i in range(0, len(bits) - 1, 2):
        b1, b2 = bits[i], bits[i + 1]
        if b1 == 0 and b2 == 1:
            extracted.append(0)
        elif b1 == 1 and b2 == 0:
            extracted.append(1)
    return extracted


def main():
    # Обираємо найбільший CSV-файл у поточній директорії (ігноруємо пусті)
    csv_files = [f for f in glob.glob("trng_data_*.csv") if os.path.getsize(f) > 1000]
    if not csv_files:
        print("Помилка: не знайдено жодного заповненого файлу trng_data_*.csv (> 1 КБ)!")
        return

    latest_file = max(csv_files, key=os.path.getsize)
    print(f"Аналіз файлу: {latest_file} ({os.path.getsize(latest_file) / (1024 * 1024):.2f} МБ)...\n")

    xor_bits = []
    channels = [[], [], [], []]

    with open(latest_file, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        print(f"Заголовок CSV: {header}")

        for row in reader:
            try:
                if len(row) >= 7:
                    # Формат: timestamp, current_bit, ch1, ch2, ch3, ch4, xor_bit
                    c1, c2, c3, c4 = int(row[2]), int(row[3]), int(row[4]), int(row[5])
                    xbit = int(row[6])
                elif len(row) == 6:
                    # Формат: timestamp, ch1, ch2, ch3, ch4, xor_bit
                    c1, c2, c3, c4 = int(row[1]), int(row[2]), int(row[3]), int(row[4])
                    xbit = int(row[5])
                else:
                    continue

                channels[0].append(c1)
                channels[1].append(c2)
                channels[2].append(c3)
                channels[3].append(c4)
                xor_bits.append(xbit)
            except ValueError:
                continue

    total = len(xor_bits)
    if total == 0:
        print("Помилка: у файлі не вдалося розпізнати жодного рядка з числами.")
        return

    ones = sum(xor_bits)
    zeros = total - ones

    print(f"\n=== ЗАГАЛЬНА СТАТИСТИКА ({total} семплів) ===")
    print(f"Нулів (0):   {zeros} ({zeros / total * 100:.4f}%)")
    print(f"Одиниць (1): {ones} ({ones / total * 100:.4f}%)")
    print(f"Ентропія Шеннона (макс. 1.000000): {shannon_entropy(xor_bits):.6f}")

    lags = list(range(1, 21))
    acf_raw = [autocorrelation(xor_bits, lag) for lag in lags]
    print("\n=== АВТОКОРЕЛЯЦІЯ СИРОГО XOR (лаги 1..10) ===")
    for lag in range(1, 11):
        print(f"Lag {lag:2d}: {acf_raw[lag - 1]:+.6f}")

    vn_bits = von_neumann_extract(xor_bits)
    vn_total = len(vn_bits)
    vn_ones = sum(vn_bits)
    acf_vn = [autocorrelation(vn_bits, lag) for lag in lags]

    print(f"\n=== ПІСЛЯ ОЧИЩЕННЯ ФОН НЕЙМАНА ({vn_total} чистих бітів) ===")
    print(f"Баланс 0 / 1: {(vn_total - vn_ones) / vn_total * 100:.4f}% / {vn_ones / vn_total * 100:.4f}%")
    print(f"Ентропія Шеннона: {shannon_entropy(vn_bits):.6f}")
    print(f"Автокореляція (lag=1): {acf_vn[0]:+.6f} | (lag=2): {acf_vn[1]:+.6f}")

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Аналіз апаратного TRNG ({total} семплів)", fontsize=14, fontweight="bold")

    conf_bound = 1.96 / math.sqrt(total)
    axs[0, 0].bar([l - 0.15 for l in lags], acf_raw, width=0.3, label="Сирий XOR", color="#1f77b4")
    axs[0, 0].bar([l + 0.15 for l in lags], acf_vn, width=0.3, label="Після фон Неймана", color="#2ca02c")
    axs[0, 0].axhline(conf_bound, color="red", linestyle="--", linewidth=1, label="95% межа білого шуму")
    axs[0, 0].axhline(-conf_bound, color="red", linestyle="--", linewidth=1)
    axs[0, 0].axhline(0, color="black", linewidth=0.8)
    axs[0, 0].set_title("Автокореляція бітів (Lag 1–20)")
    axs[0, 0].set_xlabel("Зсув (Lag)")
    axs[0, 0].set_ylabel("Коефіцієнт кореляції")
    axs[0, 0].legend()
    axs[0, 0].grid(True, alpha=0.3)

    window = max(1000, total // 100)
    rolling_means = [sum(xor_bits[i:i + window]) / window for i in range(0, total - window, window)]
    axs[0, 1].plot(range(len(rolling_means)), rolling_means, color="#ff7f0e", linewidth=1.2)
    axs[0, 1].axhline(0.5, color="black", linestyle="--", linewidth=1)
    axs[0, 1].set_ylim(0.45, 0.55)
    axs[0, 1].set_title(f"Стабільність балансу 0/1 у часі (вікно {window} семплів)")
    axs[0, 1].set_xlabel("Номер блоку")
    axs[0, 1].set_ylabel("Частка одиниць")
    axs[0, 1].grid(True, alpha=0.3)

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    for idx, ch in enumerate(channels):
        axs[1, 0].hist(ch, bins=80, alpha=0.55, label=f"Канал {idx + 1}", color=colors[idx], density=True)
    axs[1, 0].set_title("Щільність розподілу сигналів АЦП (4 канали)")
    axs[1, 0].set_xlabel("Значення диференціального АЦП")
    axs[1, 0].set_ylabel("Щільність ймовірності")
    axs[1, 0].legend()
    axs[1, 0].grid(True, alpha=0.3)

    floats = []
    for i in range(0, len(vn_bits) - 31, 32):
        val = 0
        for b in vn_bits[i:i + 32]:
            val = (val << 1) | b
        floats.append(val / (2 ** 32))

    pairs = len(floats) // 2
    inside = 0
    pi_history = []
    step_points = []
    for p in range(1, pairs + 1):
        x, y = floats[2 * p - 2], floats[2 * p - 1]
        if x * x + y * y <= 1.0:
            inside += 1
        if p % 50 == 0 or p == pairs:
            pi_history.append(4.0 * inside / p)
            step_points.append(p)

    axs[1, 1].plot(step_points, pi_history, color="#9467bd", linewidth=1.5, label="Оцінка π на даних TRNG")
    axs[1, 1].axhline(math.pi, color="black", linestyle="--", linewidth=1, label="Еталон π (3.14159...)")
    axs[1, 1].set_title(f"Збіжність Монте-Карло (фінальне π = {pi_history[-1]:.5f})")
    axs[1, 1].set_xlabel("Кількість випадкових точок")
    axs[1, 1].set_ylabel("Оцінка π")
    axs[1, 1].legend()
    axs[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    output_img = "trng_analysis.png"
    plt.savefig(output_img, dpi=150)
    print(f"\nГрафік успішно збережено у файл: {output_img}")


if __name__ == "__main__":
    main()