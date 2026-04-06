class FieldNotFoundError(Exception):
    """Raised when the routing daemon doesn't encounter the field it should when it should."""

    def __init__(self, expected_field):
        super().__init__("The field: " + str(expected_field) + " was expected but not found.")

    def __str__(self):
        return f"FieldNotFoundError: {self.message}"