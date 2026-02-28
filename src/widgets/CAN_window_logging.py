import csv
from datetime import datetime
import os
import time
from utils import data_objs


# Logging functions
class CANWindowLoggingMixin:
    def _init_logging(self):
        """Initialize CSV logging files with timestamped names"""
        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")

        # Create timestamped filenames
        # Values log file (CAN dump logging is now handled by separate process)
        self.values_log_file = os.path.join("logs", f"values_{self.timestamp}.csv")
        self.values_csv_file = open(self.values_log_file, "w", newline="")
        self.values_writer = csv.writer(self.values_csv_file)

        # Header names
        values_header = ["Timestamp", "Elapsed_Time_s"]
        for obj in data_objs:
            values_header.append(obj.name)

        self.values_writer.writerow(values_header)
        self.values_csv_file.flush()  # Ensure header is written immediately

        print(f"Values logging initialized: {self.values_log_file}")

    # Makes given history the same length as time_history so it is plottable (note: this function works because lists are mutable and can be referenced through formal param)
    def update_history(self, history: list):
        while len(history) > len(self.time_history):
            history.pop(0)
        while len(history) < len(self.time_history):
            last_val = history[-1] if history else 0
            history.append(last_val)

    def _log_values(self):
        """Log current values to CSV file"""
        try:
            timestamp = datetime.now().isoformat()
            elapsed_time = time.time() - self.time_start
            values = [timestamp, f"{elapsed_time:.3f}"]
            for obj in data_objs:
                val = obj.get_current()[1]
                if val is not None:
                    values.append(str(val))
                else:
                    values.append("None")
            self.values_writer.writerow(values)
            self.values_csv_file.flush()  # Flush immediately to prevent data loss
        except Exception as e:
            print(f"Error logging values: {e}")
