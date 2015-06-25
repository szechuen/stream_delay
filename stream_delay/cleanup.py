import os
import sys
import time
import logging
import yaml

import signal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Loading config file " + sys.argv[1] + "...")

with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)


if __name__ == "__main__":
    def exit(*args):
        logger.info("Exiting...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, exit)

    try:
        while True:
            timestamp = time.time()
            current_timestamp = int(timestamp / config['segment_time'])
            discard_timestamp = current_timestamp - int(config['archive_period'] / config['segment_time'])

            logger.info("Removing files with timestamp before " + str(discard_timestamp) + "...")

            file_list = [os.path.join(root_path, file_name) for root_path, sub_folder, files in os.walk(config['chunk_path']) for file_name in files]

            for file_pathname in file_list:
                file_path, file_name = os.path.split(file_pathname)
                file_label, file_ext = os.path.splitext(file_name)

                if file_ext == ("." + config['audio_ext']):
                    file_timestamp_str = file_label.split("_")[1]

                    if file_timestamp_str.isdigit():
                        file_timestamp = int(file_timestamp_str)

                        if file_timestamp < discard_timestamp:
                            os.remove(file_pathname)
                            logger.info("Removed file " + file_name + ".")

            logger.info("Done, sleeping for " + str(config['segment_time']) + " seconds...")
            time.sleep(config['segment_time'])

    except KeyboardInterrupt:
        logger.info("Interupt detected, exiting...")
        exit()
