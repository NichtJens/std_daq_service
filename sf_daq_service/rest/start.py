import argparse
import logging

from flask import Flask, request, jsonify

from sf_daq_service.common import broker_config
from sf_daq_service.common.broker_client import BrokerClient
from sf_daq_service.rest.request_factory import build_write_request
from sf_daq_service.rest.status_aggregator import StatusAggregator

_logger = logging.getLogger("RestProxyService")


def on_status_message():
    pass


def start_rest_api(service_name, broker_url, tag):

    app = Flask(service_name)
    status_aggregator = StatusAggregator()
    broker_client = BrokerClient(broker_url, tag,
                                 on_status_message_function=status_aggregator.on_broker_message)

    @app.route("/write", methods=['POST'])
    def write_request():
        request_data = request.json

        if 'output_file' not in request_data:
            raise RuntimeError('Mandatory field "output_file" missing.')
        output_file = request_data['output_file']

        if 'n_images' not in request_data:
            raise RuntimeError('Mandatory field "n_images" missing.')
        n_images = request_data['n_images']

        if 'sources' not in request_data:
            raise RuntimeError('Mandatory field "sources" missing.')
        sources = request_data['sources']
        if isinstance(request_data['sources'], list):
            raise RuntimeError('Field "sources" must be a list.')

        header, body = build_write_request(output_file=output_file, n_images=n_images, sources=sources)

        request_id = broker_client.send_request(tag, body)
        broker_response = status_aggregator.wait_for_response(request_id)

        # TODO: Convert broker_response to client response.
        response = {"broker": broker_response}

        return jsonify(response)


if __file__ == "__main__":
    parser = argparse.ArgumentParser(description='Rest Proxy Service')

    parser.add_argument("service_name", type=str, help="Name of the service")
    parser.add_argument("tag", type=str, help="Tag on which the proxy listens to statuses and sends requests.")

    parser.add_argument("--broker_url", default=broker_config.TEST_BROKER_URL,
                        help="Address of the broker to connect to.")
    parser.add_argument("--log_level", default="INFO",
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
                        help="Log level to use.")

    args = parser.parse_args()

    _logger.setLevel(args.log_level)
    logging.getLogger("pika").setLevel(logging.WARNING)

    _logger.info(f'Service {args.service_name} connecting to {args.broker_url}.')

    start_rest_api(service_name=args.service_name,
                   broker_url=args.broker_url,
                   tag=args.tag)

    _logger.info(f'Service {args.service_name} stopping.')
