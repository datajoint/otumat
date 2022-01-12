import subprocess
import time
import os
import sys
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from pathlib import Path

my_list = ['1','2']

class OnMyWatch:
    # Set the directory on watch
    watchDirectory = sys.argv[1]
  
    def __init__(self):
        self.observer = PollingObserver(timeout=0)

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.watchDirectory, recursive = True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            self.observer.stop()
            print("\nObserver Stopped")

        self.observer.join()
  
  
class Handler(FileSystemEventHandler):
  
    @staticmethod
    def on_any_event(event):
        global my_list
        if event.is_directory:
            return None
  
        elif event.event_type == 'modified':
            # Event is modified, you can process it now
            print("Watchdog received modified event - % s." % event.src_path)
            file_extension = os.path.splitext(sys.argv[2])[1]
            if file_extension == '.sh':
                my_list = subprocess.Popen(['sh', sys.argv[2], *my_list], 
                                            stdout=subprocess.PIPE ).communicate(
                                            )[0].decode('utf-8').split('\n')[:-1]
            print(my_list)
            # elif file_extension == '.bat':
                
if __name__ == '__main__':
    watch = OnMyWatch()
    watch.run()