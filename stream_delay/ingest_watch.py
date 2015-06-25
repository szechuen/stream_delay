import os
import sys
import time
import logging
import yaml

import signal
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Loading config file " + sys.argv[1] + "...")

with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)


class StreamChunkHandler(PatternMatchingEventHandler):
    patterns = [ ("*." + config['audio_ext']) ]

    def on_created(self, event):
        timestamp = time.time()
        file_timestamp = str(int(timestamp / config['segment_time']))

        file_path, file_name = os.path.split(event.src_path)
        file_label, file_ext = os.path.splitext(file_name)
        stream_name = file_label.split("_")[0]

        logger.info("Discovered stream chunk " + file_name + ".")

        file_name_new = stream_name + "_" + file_timestamp + file_ext
        dest_path = os.path.join(file_path, file_name_new)

        os.rename(event.src_path, dest_path)
        logger.info("Renamed stream chunk " + file_name + " to " + file_name_new + ".")


if __name__ == "__main__":
    event_handler = StreamChunkHandler()
    observer = Observer()
    observer.schedule(event_handler, config['chunk_path'], recursive=True)
    observer.start()

    logger.info("Monitoring directory " + config['chunk_path'] + "...")

    def exit(*args):
        logger.info("Exiting, stop monitoring directory...")
        observer.stop()
        observer.join()
        sys.exit(0)

    signal.signal(signal.SIGTERM, exit)

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interupt detected, exiting...")
        exit()
