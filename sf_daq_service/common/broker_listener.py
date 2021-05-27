
class BrokerListener(object):
    def __init__(self, broker_url, tag, on_message_function):
        self.broker_url = broker_url
        self.tag = tag
        self.on_message = on_message_function

    def start(self):
        try:
            pass
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        pass
