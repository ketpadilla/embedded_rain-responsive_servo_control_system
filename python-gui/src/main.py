# AI-GENERATED AND EDITED

import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import time
from collections import deque

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


BAUD = 9600
MAX_POINTS = 200   # points shown in plot


def auto_find_arduino_port_mac() -> str | None:
    """
    Try to auto-detect Arduino-style ports on macOS.
    Prefers /dev/cu.usbmodem* or /dev/cu.usbserial*.
    """
    ports = list(serial.tools.list_ports.comports())
    candidates = []

    for p in ports:
        dev = p.device.lower()
        if "usbmodem" in dev or "usbserial" in dev:
            candidates.append(p.device)

    if candidates:
        return candidates[0]

    # fallback: any /dev/cu.* port
    for p in ports:
        if p.device.startswith("/dev/cu."):
            return p.device

    return None


class ERRSCSGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ERRSCS GUI")
        self.root.geometry("1000x550")

        # Serial
        self.ser = None
        self.serial_buffer = ""

        # Plot data
        self.rain_vals = deque([0] * MAX_POINTS, maxlen=MAX_POINTS)
        self.x_vals = list(range(MAX_POINTS))

        # Layout
        self._build_ui()

        # Auto-connect
        self._connect_serial(auto=True)

        # Start update loop
        self._schedule_update()

    def _build_ui(self):
        # Top bar
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        self.port_var = tk.StringVar(value="(not connected)")
        ttk.Label(top, text="Serial Port:").pack(side="left")
        ttk.Label(top, textvariable=self.port_var).pack(side="left", padx=8)

        ttk.Button(top, text="Reconnect", command=self._reconnect_clicked).pack(side="left", padx=8)
        ttk.Button(top, text="Reset (send 'R')", command=self._send_reset).pack(side="left", padx=8)
        ttk.Button(top, text="Close", command=self.root.destroy).pack(side="right")

        # Main content
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="y", padx=(0, 10))

        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        # Status labels
        self.lbl_rain_value = ttk.Label(left, text="RainValue (AO): ---", font=("Segoe UI", 14))
        self.lbl_rain_detected = ttk.Label(left, text="RainDetected: ---", font=("Segoe UI", 14))
        self.lbl_switch = ttk.Label(left, text="Switch: ---", font=("Segoe UI", 14))
        self.lbl_servo = ttk.Label(left, text="ServoPos: ---", font=("Segoe UI", 14))
        self.lbl_buzzer = ttk.Label(left, text="BuzzerVol: ---", font=("Segoe UI", 14))
        self.lbl_status = ttk.Label(left, text="Status: ---", font=("Segoe UI", 12))

        self.lbl_rain_value.pack(anchor="w", pady=6)
        self.lbl_rain_detected.pack(anchor="w", pady=6)
        self.lbl_switch.pack(anchor="w", pady=6)
        self.lbl_servo.pack(anchor="w", pady=6)
        self.lbl_buzzer.pack(anchor="w", pady=6)
        self.lbl_status.pack(anchor="w", pady=16)

        # Plot (Rain AO)
        fig = Figure(figsize=(6.5, 4.5), dpi=100)
        self.ax = fig.add_subplot(111)
        self.ax.set_title("Rain Sensor Analog Value (AO)")
        self.ax.set_ylim(0, 1023)
        self.ax.set_xlim(0, MAX_POINTS - 1)
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel("AO (0–1023)")

        self.line, = self.ax.plot(self.x_vals, list(self.rain_vals))
        self.canvas = FigureCanvasTkAgg(fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _connect_serial(self, auto: bool = False):
        # Close existing connection
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.serial_buffer = ""

        port = auto_find_arduino_port_mac() if auto else self._ask_user_port()

        if not port:
            self.port_var.set("(not connected)")
            self._set_status("No port selected/found.")
            return

        try:
            self.ser = serial.Serial(port, BAUD, timeout=0.1)
            time.sleep(2)  # Arduino reset on open
            self.port_var.set(port)
            self._set_status("Connected.")
        except Exception as e:
            self.port_var.set("(not connected)")
            self._set_status(f"Failed to connect: {e}")

    def _ask_user_port(self):
        # Minimal “manual pick”: choose first /dev/cu.* if available
        ports = [p.device for p in serial.tools.list_ports.comports() if p.device.startswith("/dev/cu.")]
        if ports:
            return ports[0]
        return None

    def _reconnect_clicked(self):
        self._connect_serial(auto=True)

    def _send_reset(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b"R")
                self._set_status("Sent reset command: R")
            except Exception as e:
                self._set_status(f"Reset send failed: {e}")
        else:
            self._set_status("Not connected.")

    def _set_status(self, msg: str):
        self.lbl_status.config(text=f"Status: {msg}")

    def _schedule_update(self):
        self.root.after(50, self._update_loop)

    def _update_loop(self):
        self._read_serial_lines()
        self._schedule_update()

    def _read_serial_lines(self):
        if not (self.ser and self.ser.is_open):
            return

        try:
            data = self.ser.read(512).decode(errors="ignore")
            if not data:
                return

            self.serial_buffer += data

            while "\n" in self.serial_buffer:
                line, self.serial_buffer = self.serial_buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                # Expect CSV: rainValue,rainDetected,switchOn,servoPosition,buzzerVolume
                parts = line.split(",")
                if len(parts) != 5:
                    # ignore non-CSV debug lines
                    continue

                try:
                    rain_value = int(parts[0])
                    rain_detected = int(parts[1])
                    switch_on = int(parts[2])
                    servo_pos = int(parts[3])
                    buzzer_vol = int(parts[4])
                except ValueError:
                    continue

                # Update labels
                self.lbl_rain_value.config(text=f"RainValue (AO): {rain_value}")
                self.lbl_rain_detected.config(text=f"RainDetected: {'YES' if rain_detected else 'NO'}")
                self.lbl_switch.config(text=f"Switch: {'ON' if switch_on else 'OFF'}")
                self.lbl_servo.config(text=f"ServoPos: {servo_pos}")
                self.lbl_buzzer.config(text=f"BuzzerVol: {buzzer_vol}")

                # Update plot
                self.rain_vals.append(rain_value)
                self.line.set_ydata(list(self.rain_vals))
                self.canvas.draw_idle()

        except Exception as e:
            self._set_status(f"Serial read error: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ERRSCSGUI(root)
    root.mainloop()