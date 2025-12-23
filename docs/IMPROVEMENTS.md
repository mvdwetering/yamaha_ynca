# Improvements

This document lists some possible improvements.

Most of them are not straight forward.

## Simplify autodetection

Initially all known receivers allowed to figure out the inputs and scenes supported. Over time it has become clear that it is not possible for all models and code has been added to work around that.

Currently there is code in multiple places that always tries to autodetect. E.g. amount of scenes or which inputs are supported. This code is complicated because it also needs to take into account user settings if the user ever changed them and it takes modelinfo details into account if known.

To simplify the code we could run autodetect only once when the integration is added and store the results in the configentry where the user can change settings if needed.

This would avoid the need for the "Auto" setting for scene detection and in general would allow to always use the settings as configured in the config entry.

If all autodetection is limited to initial setup it should also be possible to open the integration options screen without an active connection to the receiver.

Challenges:

* Need to migrate existing configentries on first run after this feature has been added. I think "old" config entries will have empty lists for inputs/scenes if the user never touched the integration opitions. Probably best to migrate the autodetected settings one-by-one. E.g. first scenes, then inputs
* Auto detection needs more info than the current `ynca.connection_check()` provides. This quick check was added because the full `ynca.initialize()` takes a very long time. Maybe extend the `connection_check()` with INPNAMES and SCENENAMES?

## Add discovery

The YNCA protocol itself does not provide a discovery mechanism. But the receivers do support UPnP/DLNA, so SSDP could be used to discover Yamaha receivers.

After discovering a Yamaha receiver a check would be needed to see if the receiver supports the YNCA protocol.

Challenges:

* Avoiding duplicate / false discoveries. The YNCA protocol does not offer a unique identifier to identify duplicates. Maybe checks can be done on IP address, but there are users who use hostname to connect to the receiver, not sure how that should be handled.
* Only 1 YNCA connection can be made to a receiver at the time. The is-ynca-supported check during discovery could interfere with the normal integration setup if it gets discovered early.
