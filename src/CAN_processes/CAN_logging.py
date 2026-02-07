import csv
import datetime
import multiprocessing
import os
import time
from DataObject import *
from utility import *

def can_logging_process(queue: multiprocessing.Queue, log_queue: multiprocessing.Queue, timestamp):
    """Dedicated process for logging CAN messages without blocking graphics"""
    try:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Create timestamped filename
        # timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        candump_log_file = os.path.join('logs', f'candump_{timestamp}.csv')
        
        with open(candump_log_file, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['Timestamp', 'Elapsed_Time_s', 'CAN_Message'])
            csv_file.flush()
            
            start_time = time.time()
            print(f"CAN Logging started: {candump_log_file}")
            
            while True:
                try:
                    # Get message from queue with timeout
                    if not log_queue.empty():
                        message = log_queue.get(timeout=1.0)
                        if message == "__EXIT__":
                            break
                        # Log the message
                        timestamp = datetime.now().isoformat()
                        elapsed_time = time.time() - start_time
                        writer.writerow([timestamp, f'{elapsed_time:.3f}', message])
                        csv_file.flush()
                # except queue.empty as empty:
                #     print(f"CAN logging queue empty")
                except Exception as e:
                    print(f"Error in CAN logging: {e}")
                    continue
                    
    except Exception as e:
        print(f"Failed to initialize CAN logging: {e}")
    
    print("CAN logging process terminated")