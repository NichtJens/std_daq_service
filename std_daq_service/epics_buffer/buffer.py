import logging
import signal
from time import sleep

from redis import Redis

from std_daq_service.epics_buffer.receiver import EpicsReceiver

# Redis buffer for 1 day.
# max 10/second updates for regular channels.
from std_daq_service.epics_buffer.stats import EpicsBufferStats

REDIS_MAX_STREAM_LEN = 3600*24*10
# 100/second updates for pulse_id channel.
REDIS_PULSE_ID_MAX_STREAM_LEN = 3600*24*100
# Interval for printing out statistics.
STATS_INTERVAL = 10

_logger = logging.getLogger("EpicsBuffer")


def start_epics_buffer(service_name, redis_host, pv_names, pulse_id_pv=None):
    _logger.debug(f'Connecting to PVs: {pv_names}')

    redis = Redis(host=redis_host)
    stats = EpicsBufferStats(service_name=service_name)

    def on_pv_change(pv_name, value):
        redis.xadd(pv_name, value, maxlen=REDIS_MAX_STREAM_LEN)
    EpicsReceiver(pv_names=pv_names, change_callback=on_pv_change)

    if pulse_id_pv:
        _logger.info(f"Adding pulse_id_pv {pulse_id_pv} to buffer.")

        def on_pulse_id_change(_, value):
            redis.xadd("pulse_id", value, maxlen=REDIS_PULSE_ID_MAX_STREAM_LEN)
        EpicsReceiver(pv_names=[pulse_id_pv], change_callback=on_pulse_id_change)

    try:
        sleep(STATS_INTERVAL)


    except KeyboardInterrupt:
        _logger.info("Received interrupt signal. Exiting.")

    except Exception:
        _logger.error("Epics buffer error.")
