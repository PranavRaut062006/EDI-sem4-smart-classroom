import random

class SensorSimulator:
    def __init__(self):
        # Initial baseline values
        self.temperature = 22.0  # Celsius
        self.humidity = 40.0     # Percent
        self.aqi = 35.0          # Air Quality Index
        self.light = 600.0       # Ambient Light (Lux)

    def read_sensors(self):
        # Add slight random walks to simulate real sensors
        self.temperature += random.uniform(-0.2, 0.2)
        self.humidity += random.uniform(-0.5, 0.5)
        self.aqi += random.uniform(-1.0, 1.5)
        self.light += random.uniform(-10.0, 10.0)

        # Keep values within reasonable classroom bounds
        self.temperature = max(16.0, min(35.0, self.temperature))
        self.humidity = max(20.0, min(80.0, self.humidity))
        self.aqi = max(10.0, min(150.0, self.aqi))
        self.light = max(100.0, min(1000.0, self.light))

        return {
            "temperature": round(self.temperature, 1),
            "humidity": round(self.humidity, 1),
            "aqi": round(self.aqi, 0),
            "light": round(self.light, 0),
            "status": "Warning" if self.aqi > 100 or self.temperature > 30 else "Optimal"
        }
