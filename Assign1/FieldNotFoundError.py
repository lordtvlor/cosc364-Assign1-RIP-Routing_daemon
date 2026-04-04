class FieldNotFoundError(Exception):
    """Raised when the routing daemon doesn't encounter the field it should when it should."""

    def __init__(self, expected_field):
        self.message = "The field: " + str(expected_field) + " was expected but not found."
        super().__init__(self.message)

    def __str__(self):
        return f"FieldNotFoundError: {self.message}"