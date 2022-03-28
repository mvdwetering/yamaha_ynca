from unittest import mock


class MockReceiver(mock.MagicMock):
    def __init__(self, *args, **kwargs) -> None:
        # Would like to have a mock with `spec=ynca.Receiver`, but then
        # I can not add the response logic to the mock :/
        super().__init__(*args, **kwargs)
