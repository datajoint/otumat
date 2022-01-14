import subprocess
import time
import os
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from pathlib import Path

my_list = ['1']

class OnMyWatch:
  
    def __init__(self, watch_file, watch_script, watch_args):
        self.observer = PollingObserver(timeout=0)
        self.watchDirectory = watch_file
        self.watch_script = watch_script
        self.watch_args = watch_args

    def run(self):
        event_handler = Handler(self.watchDirectory, self.watch_script, self.watch_args)
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
    
    def __init__(self, watch_file, watch_script, watch_args):
        self.watch_file = watch_file
        self.watch_script = watch_script
        self.watch_args = watch_args

    def on_any_event(self, event):
        global my_list
        if event.is_directory:
            return None

        elif event.event_type == 'modified':
            # Event is modified, you can process it now
            print("Watchdog received modified event - % s." % event.src_path)
            file_extension = os.path.splitext(self.watch_script)[1]
            if file_extension == '.sh':
                my_list = subprocess.Popen(['sh', self.watch_script, *my_list], 
                                            stdout=subprocess.PIPE ).communicate(
                                            )[0].decode('utf-8').split('\n')[:-1]
            print(my_list)
            # elif file_extension == '.bat':