import argparse
import logging
import sys

from flask import Flask, request, jsonify
from jsonschema import validate, exceptions
from sls_detector import Eiger

from std_daq_service.broker.client import BrokerClient
from std_daq_service.broker.common import TEST_BROKER_URL
from std_daq_service.broker.status_aggregator import StatusAggregator
from std_daq_service.rest.request_factory import build_write_request, build_broker_response
from std_daq_service.rest.eiger_schema import eiger_schema

_logger = logging.getLogger("RestProxyService")

def is_valid_detector_config(config):
    try:
        validate(instance=config, schema=eiger_schema)
    except exceptions.ValidationError as err:
        return False
    return True

def validate_det_param(param):
    list_of_eiger_params = ["n_cycles", "triggers", 
        "timing","n_frames", "period", "exposure_time",
        "dynamic_range"]
    if param not in list_of_eiger_params:
        return False
    return True

def extract_write_request(request_data, run_id):

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

    return build_write_request(output_file=output_file, n_images=n_images, sources=sources, run_id=run_id)


def start_rest_api(service_name, broker_url, tag):

    app = Flask(service_name)
    status_aggregator = StatusAggregator()
    broker_client = BrokerClient(broker_url, tag,
                                 status_callback=status_aggregator.on_status_message)

    @app.route("/write_sync", methods=['POST'])
    def write_sync_request():
        run_id = 0
        header, message = extract_write_request(request.json, run_id)
        request_id = broker_client.send_request(message, header)
        broker_response = status_aggregator.wait_for_complete(request_id)
        response = {"request_id": request_id,
                    'response': build_broker_response(response=broker_response)}
        return jsonify(response)

    @app.route('/write_async', methods=['POST'])
    def write_async_request():
        run_id = 0
        header, message = extract_write_request(request.json, run_id)

        request_id = broker_client.send_request(message, header)
        response = {"request_id": request_id}

        return jsonify(response)

    @app.route('/write_kill', methods=['POST'])
    def write_kill():
        kill_request = request.json

        if 'request_id' not in kill_request:
            raise RuntimeError('Mandatory field "request_id" missing.')
        request_id = kill_request['request_id']

        broker_client.kill_request(request_id)
        broker_response = status_aggregator.wait_for_response(request_id)

        response = {"request_id": request_id,
                    'response': build_broker_response(response=broker_response)}

        return jsonify(response)

    @app.route('/detector', methods=['GET', 'POST'])
    def detector_config():
        if request.method == 'GET':
            # //TODO fetch configurations from the detector
            response = {'response': 'to be implemented...'}
            return jsonify(response)
        if request.method == 'POST':
            config = request.json
            response={'response':'Detector configuration set.'}
            # verify if it's a valid config
            if not is_valid_detector_config(config):
                response = {'response': 'Detector configuration not valid.'}
            if config['det_name'].upper() == "EIGER":
                try:
                    d = Eiger()
                except RuntimeError as e:
                    response['response']= 'Problem connecting to the detector.'
                else:
                    for param in config['config']:
                        if not validate_det_param(param):
                            response={'response': 
                                'Detector parameter not valid (%s).' % param}
                            break
                        if param == "n_cycles":
                            d.n_cycles = config[param]
                        if param == "triggers":
                            d.triggers = config[param]
                        if param == "timing":
                            d.timing = config[param]
                        if param == "n_frames":
                            d.n_frames = config[param]
                        if param == "period":
                            d.period = config[param]
                        if param == "exposure_time":
                            d.exposure_time = config[param]
                        if param == "dynamic_range":
                            d.dynamic_range = config[param]
            return jsonify(response)
    
    app.run(host='127.0.0.1', port=5000)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Rest Proxy Service')

    parser.add_argument("service_name", type=str, help="Name of the service")
    parser.add_argument("tag", type=str, help="Tag on which the proxy listens to statuses and sends requests.")

    parser.add_argument("--broker_url", default=TEST_BROKER_URL,
                        help="Address of the broker to connect to.")
    parser.add_argument("--log_level", default="INFO",
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
                        help="Log level to use.")

    args = parser.parse_args()

    _logger.setLevel(args.log_level)
    logging.getLogger("pika").setLevel(logging.WARNING)

    _logger.info(f'Service {args.service_name} connecting to {args.broker_url}.')
    print(f'Service {args.service_name} connecting to {args.broker_url}.')

    start_rest_api(service_name=args.service_name,
                   broker_url=args.broker_url,
                   tag=args.tag)

    _logger.info(f'Service {args.service_name} stopping.')
