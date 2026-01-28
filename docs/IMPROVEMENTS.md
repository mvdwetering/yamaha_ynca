# Improvements

This document lists some possible improvements that have been on my list, but I never got around to look into further.

Not all are straight forward.

## Improve the configuration UX

The integration configuration currently consists of multiple pages. One general page and then a page per zone.

This split was done because having all the settings on one page was messy because there is no way to insert headings or something. However it has the downside that sometimes people can not find the settings because they don't realize there are multiple pages.

A while back a "section" was introduced for config flow. A section groups multiple controls, has a title and can be collapsed by default (or not for this usecase). See developer documentation <https://developers.home-assistant.io/docs/data_entry_flow_index/?_highlight=section&_highlight=section#show-form>

Having all settings in one page with sections for the current pages would probably more clear than the current situation.

## Simplify autodetection

Initially all known receivers allowed to figure out the inputs and scenes supported. Over time it has become clear that it is not possible for all models and code has been added to work around that.

Currently there is code in multiple places that always tries to autodetect. E.g. amount of scenes or which inputs are supported. This code is complicated because it also needs to take into account user settings if the user ever changed them and it takes modelinfo details into account if known.

To simplify the code we could run autodetect only once when the integration is added and store the results in the configentry where the user can change settings if needed.

This would avoid the need for the "Auto" setting for scene detection and in general would allow to always use the settings as configured in the config entry.

If all autodetection is limited to initial setup it should also be possible to open the integration options screen without an active connection to the receiver.

Challenges:

* Need to migrate existing configentries on first run after this feature has been added. I think "old" config entries will have empty lists for inputs/scenes if the user never touched the integration options. Probably best to migrate the autodetected settings one-by-one. E.g. first scenes, then inputs
* Auto detection needs more info than the current `ynca.connection_check()` provides. This quick check was added because the full `ynca.initialize()` takes a very long time. Maybe extend the `connection_check()` with INPNAMES and SCENENAMES?

## Add discovery

The YNCA protocol itself does not provide a discovery mechanism. But the receivers do support UPnP/DLNA, so SSDP could be used to discover Yamaha receivers.

After discovering a Yamaha receiver a check would be needed to see if the receiver supports the YNCA protocol.

Challenges:

* Avoiding duplicate / false discoveries. The YNCA protocol does not offer a unique identifier to identify duplicates. Maybe checks can be done on IP address, but there are users who use hostname to connect to the receiver, not sure how that should be handled.
* Only 1 YNCA connection can be made to a receiver at the time. The is-ynca-supported check during discovery could interfere with the normal integration setup if it gets discovered early.

## Better out-of-the-box experience

It would be nice if not every user needed to configure the soundmodes and inputs per zone (and potentially amount of scenes).
For some models the soundmodes are known in `ynca` package in the modelinfo. This could be extended with more info about the available inputs, surround decoders etc...

It would require data to be obtained from somewhere. Could be users that send it in or collect it by reading the manuals.

It would probably still be needed to keep some things configurable. I know there are users which hide the input that they don't use to keep the list easy to use. That is a nice usecase I would like to keep. But there is no reason to show the COAXIAL1 input if your receiver does not have it at all. Similar for the other settings.

## Improve initialization time

The Yamaha (YNCA) integration is one of the slower integrations to startup (15 seconds for my RX-A810, but more zones is more startup time). There have never been complaints about it, but it would be nice to improve it.

It takes a long time because on all zones/subunits all known features are attempted to be initialized to see if they are supported on the specific model. But after the first time there is really no reason to keep doing that because the feature set of the receiver will not change (unless we add new features).

It would be nice if there was a way to capture the current supported features and provide that as a list of things to initialize on next startup.

This would probably be a lot of work and not sure if it is worth the time investment.

I suspect most time is spent in the Zone initialization because they have the most attributes. Maybe it is enough to reduce the amount of attributes on the zones, e.g. Zone 4 supports a lot less than Main zone. The other subunits have less attributes and if the subunit is there then probably most attributes will be supported, so not a lot of waste.
