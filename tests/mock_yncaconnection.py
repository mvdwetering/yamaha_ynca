from typing import Any
from unittest import mock

from ynca import YncaProtocolStatus


class YncaConnectionMock(mock.MagicMock):
    def __init__(self, *args: Any, **kwargs: dict[str, Any]) -> None:
        # Would like to have a MagicMock with `spec=YncaConnection`, but then
        # I can not add the response logic to the mock :/
        super().__init__(*args, **kwargs)
        self._num_commands_sent = 10
        self.get_response_list: list[
            tuple[tuple[str, str], list[tuple[str, str, str]]]
        ] = []

    @property
    def num_commands_sent(self) -> int:
        return self._num_commands_sent

    def setup_responses(
        self, response_list: list[tuple[tuple[str, str], list[tuple[str, str, str]]]]
    ) -> None:
        # Need to separate from __init__ otherwise it would run into infinite
        # recursion when executing `self.get.side_effect = xyz`
        self.get.side_effect = self._get_response
        self._get_response_list_offset = 0
        self.get_response_list = response_list

    # ruff: noqa: T201
    def _get_response(self, subunit: str, function: str) -> None:
        self._num_commands_sent += 1

        print(f"mock: get_response({subunit}, {function})")
        try:
            (next_request, responses) = self.get_response_list[
                self._get_response_list_offset
            ]
            print(f"mock:   next_request={next_request}, responses={responses}")
            if not (next_request[0] == subunit and next_request[1] == function):
                print("mock:   no match return @UNDEFINED")
                self.send_protocol_error("@UNDEFINED")
                return

            self._get_response_list_offset += 1
            for response in responses:
                if response[0].startswith("@"):
                    self.send_protocol_error(response[0])
                else:
                    self.send_protocol_message(response[0], response[1], response[2])

        except Exception as e:  # noqa: BLE001
            print(f"Skipping: {subunit}, {function} because of {e}")

    def send_protocol_message(
        self, subunit: str, function: str, value: str | None = None
    ) -> None:
        for callback in self.register_message_callback.call_args.args:
            callback(YncaProtocolStatus.OK, subunit, function, value)

    def send_protocol_error(self, error: str) -> None:
        for callback in self.register_message_callback.call_args.args:
            callback(YncaProtocolStatus[error[1:]], None, None, None)
