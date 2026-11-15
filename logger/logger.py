import serial
import serial.tools.list_ports
import csv
import time
from datetime import datetime, timezone

# Налаштування порту (заміни на свій, наприклад '/dev/ttyUSB0' або '/dev/ttyACM0')
BAUD_RATE = 115200
OUTPUT_FILE = f"trng_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "USB" in port.device or "ACM" in port.device:
            return port.device
    return None


def main():
    port_name = find_arduino_port()
    if not port_name:
        print("Помилка: Arduino не знайдено! Перевір підключення кабелю.")
        return

    print(f"Підключення до {port_name} на швидкості {BAUD_RATE}...")

    try:
        ser = serial.Serial(port_name, BAUD_RATE, timeout=2)
        time.sleep(2)  # Пауза для перезавантаження Arduino після відкриття порту
        ser.reset_input_buffer()

        print(f"Запис розпочато у файл: {OUTPUT_FILE}")
        print("Натисни Ctrl+C для безпечної зупинки.\n")

        with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Заголовок таблиці
            writer.writerow(["timestamp_utc", "ch1", "ch2", "ch3", "ch4", "xor_bit"])

            count = 0
            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                # Очікуємо формат рядка від Arduino: "512,498,530,505"
                parts = line.split(",")
                if len(parts) != 5:
                    continue

                try:
                    xor_bit, c1, c2, c3, c4 = map(int, parts)
                except ValueError:
                    continue

                ts = datetime.now(timezone.utc).isoformat()
                writer.writerow([ts, c1, c2, c3, c4, xor_bit])

                count += 1
                if count % 1000 == 0:
                    f.flush()  # Скидаємо буфер на диск кожні 1000 рядків
                    print(f"Записано семплів: {count} | Останні: [{c1}, {c2}, {c3}, {c4}] -> XOR: {xor_bit}")

    except KeyboardInterrupt:
        print(f"\nЗупинено користувачем. Усього збережено рядків: {count}")
    except Exception as e:
        print(f"\nПомилка з'єднання: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()


if __name__ == "__main__":
    main()