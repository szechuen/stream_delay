import os
import sys
import time
import logging
import yaml

import signal
import threading
import shout

logging.basicConfig(level=logging.INFO, format='(%(threadName)-10s) %(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Loading config file " + sys.argv[1] + "...")

with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)


def stream_start(stream_name, delay_time, sigterm, bitrate):
    stream = shout.Shout()

    stream.host = config['icecast']['host']
    stream.port = config['icecast']['port']
    stream.user = config['icecast']['user']
    stream.password = config['icecast']['password']
    stream.mount = "/" + stream_name + "_" + str(int(delay_time / 60 / 60)) + "h_" + str(int(bitrate / 1000)) + "k"
    stream.format = config['audio_ext']
    stream.protocol = 'http'
    stream.name = stream_name + " (" + str(int(delay_time / 60 / 60)) + "h delayed) - " + str(int(bitrate / 1000)) + "k"
    # stream.genre = ''
    # stream.url = ''
    stream.public = 0
    stream.audio_info = { shout.SHOUT_AI_BITRATE: str(bitrate), shout.SHOUT_AI_SAMPLERATE: str(config['icecast']['samplerate']), shout.SHOUT_AI_CHANNELS: '2' }
    #  (keys are shout.SHOUT_AI_BITRATE, shout.SHOUT_AI_SAMPLERATE,
    #   shout.SHOUT_AI_CHANNELS, shout.SHOUT_AI_QUALITY)

    stream_opened = False

    while not sigterm.isSet():
        timestamp = time.time()
        current_timestamp = int(timestamp / config['segment_time'])
        delay_timestamp = current_timestamp - int(delay_time / config['segment_time'])

        file_name = stream_name + "_" + str(delay_timestamp) + "." + config['audio_ext']
        file_pathname = os.path.join(config['chunk_path'], stream_name, file_name)

        if os.path.isfile(file_pathname):
            if not stream_opened:
                stream.open()
                stream_opened = True
                logger.info("Opened stream " + stream.name + " at " + stream.mount + "...")

            logger.info("Streaming file " + file_name + "...")

            stream_file = open(file_pathname, "rb")
#           stream.set_metadata({'song': file_name})

            nbuf = stream_file.read(4096)
            while True:
                buf = nbuf
                nbuf = stream_file.read(4096)
                if len(buf) == 0 or sigterm.isSet():
                    break
                stream.send(buf)
                stream.sync()

            stream_file.close()

        else:
            if stream_opened:
                logger.info("Closing stream " + stream.name + "...")
                stream.close()
                stream_opened = False

            logger.info("Chunk not found, sleeping for " + str(config['segment_time']) + " seconds...")
            for i in range(config['segment_time']):
                if sigterm.isSet():
                    break
                time.sleep(1)

    if stream_opened:
        logger.info("Closing stream " + stream.name + "...")
        stream.close()
        stream_opened = False


if __name__ == "__main__":
    thread_list = []
    sigterm = threading.Event()

    for stream in config['streams']:
        for delay_time in range(60*60, config['archive_period'], 60*60):
            for bitrate in config['icecast']['bitrates']:

                thread = threading.Thread(name=stream['name'] + "_" + str(int(delay_time / 60 / 60)) + "h_" + str(int(bitrate / 1000)) + "k", target=stream_start, args = (stream['name'], delay_time, sigterm, bitrate))
                thread_list.append(thread)
                thread.start()

    def exit(*args):
        logger.info("Exiting, closing streams...")
        sigterm.set()
        for thread in thread_list:
            thread.join()
        sys.exit(0)

    signal.signal(signal.SIGTERM, exit)

    try:
        while(True):
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interupt detected, exiting...")
        exit()
