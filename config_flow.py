"""Config flow for Yamaha YNCA integration."""
import logging
import asyncio

import voluptuous as vol

from homeassistant import core, config_entries, exceptions

from .const import DOMAIN  # pylint:disable=unused-import

import ynca

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
DATA_SCHEMA = vol.Schema({"serial_port": str})

def setup_receiver(port):
    return ynca.YncaReceiver(port)  # Initialization takes a while

async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.
    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth
    _LOGGER.warn("validate_input")
    _LOGGER.warn(data)

    try:
        loop = asyncio.get_running_loop()
        receiver = await loop.run_in_executor(None, setup_receiver, data["serial_port"])
        # Close connection manually, going out of scope does not seem to clean it up...
        receiver._connection.disconnect()
        # Return some info we want to store in the config entry.
        return {"title": receiver.model_name}
    except Exception as e:
        _LOGGER.error(e)
        raise CannotConnect

class DomainConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yamaha YNCA."""

    VERSION = 1
    # TODO pick one of the available connection classes in homeassistant/config_entries.py
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
