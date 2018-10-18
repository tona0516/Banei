class APIClientException(Exception):
    def __init__(self, message):
        self.message = message