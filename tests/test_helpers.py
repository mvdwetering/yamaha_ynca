from custom_components.yamaha_ynca.helpers import serial_url_from_user_input


def test_serial_url_from_user_input_ip_address_ok(hass):
    assert serial_url_from_user_input("1.2.3.4") == "socket://1.2.3.4:50000"
    assert serial_url_from_user_input("1.2.3.4:5") == "socket://1.2.3.4:5"


def test_serial_url_from_user_input_not_an_ip_address(hass):
    assert serial_url_from_user_input("not an ip address") == "not an ip address"
    assert serial_url_from_user_input("1.2.3.999") == "1.2.3.999"
    assert serial_url_from_user_input("1.2.3.4:abcd") == "1.2.3.4:abcd"
    assert serial_url_from_user_input("1.2.3.4:5:6") == "1.2.3.4:5:6"
