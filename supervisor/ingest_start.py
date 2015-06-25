import os
import sys
import time
import logging
import yaml

import stat
import xmlrpclib
from supervisor.xmlrpc import SupervisorTransport

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Loading config file " + sys.argv[1] + "...")

with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)


if __name__ == "__main__":
    s = xmlrpclib.ServerProxy('http://localhost',
        SupervisorTransport('', '', 'unix:///var/run/supervisor.sock'))

    for stream in config['streams']:
        logger.info("Ingesting stream " + stream['name'] + "...")

        stream_path = os.path.join(config['chunk_path'], stream['name'])

        if not os.path.exists(stream_path):
            os.makedirs(stream_path)

            mode = os.stat(stream_path).st_mode
            os.chmod(stream_path, mode | stat.S_IWGRP)

        cmd = [
            "ffmpeg", 
            "-c:a", config['audio_codec_input'],
            "-i", stream['url'],
            "-c:a", config['audio_codec'],
#           "-q", str(config['audio_quality']),
            "-b:a", config['audio_bitrate'],
            "-map", "0",
            "-map", "-0:d",
            "-f", "segment",
            "-segment_time", str(config['segment_time']),
            "-reset_timestamps", "1",
            "-loglevel", "warning",
            os.path.join(stream_path, stream['name'] + "_tmp%%08d." + config['audio_ext'])
        ]
        cmd_concat = " ".join(cmd)
        program_name = "stream_delay-ingest_" + stream['name']

        try:
            s.twiddler.removeProcessFromGroup("stream_delay-ingest", program_name)
            logger.info("Stopped existing process " + program_name + ".")
        except:
            pass

        s.twiddler.addProgramToGroup("stream_delay-ingest", program_name, {
            'command': cmd_concat,
            'directory': config['base_path'],
            'user': config['run_as'],
            'autostart': 'true',
            'autorestart': 'true',
            'stdout_logfile': os.path.join(config['log_path'], program_name + ".log"),
            'stderr_logfile': os.path.join(config['log_path'], program_name + ".err.log"),
            'startretries': '300'
        })

        logger.info("Started new process " + program_name + ".")

    logger.info("All streams started, exiting...")
