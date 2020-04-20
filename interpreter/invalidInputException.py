class InvalidInputException(Exception):
    def __init__(self, msg: str):
        self.msg: str = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return self.msg

