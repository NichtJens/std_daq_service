import argparse
import logging

from std_daq_service.common import broker_config
from std_daq_service.common.broker_worker import BrokerWorker
from std_daq_service.writer_agent.service import RequestWriterService
from std_daq_service.writer_agent.zmq_transciever import ZmqTransciever

_logger = logging.getLogger('RequestWriteService')

if __file__ == "__main__":
    parser = argparse.ArgumentParser(description='Broker service starter.')

    parser.add_argument("service_tag", type=str, help="Where to bind the service")
    parser.add_argument("service_name", type=str, help="Name of the service")
    parser.add_argument("--broker_url", default=broker_config.TEST_BROKER_URL,
                        help="Address of the broker to connect to.")
    parser.add_argument("--log_level", default="INFO",
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
                        help="Log level to use.")

    args = parser.parse_args()

    _logger.setLevel(args.log_level)
    logging.getLogger("pika").setLevel(logging.WARNING)

    _logger.info(f'Service {args.service_name} connecting to {args.broker_url}.')

    # TODO: Bring this 2 parameters in.
    input_stream = ''
    output_stream = ''

    service = RequestWriterService()

    transceiver = ZmqTransciever(input_stream_url=input_stream,
                                 output_stream_url=output_stream,
                                 on_message_function=service.on_stream_message)

    listener = BrokerWorker(broker_url=args.broker_url,
                            request_tag=args.service_tag,
                            name=args.service_name,
                            on_request_message_function=service.on_broker_message)

    # Blocking call.
    listener.start()

    transceiver.stop()
    _logger.info(f'Service {args.service_name} stopping.')