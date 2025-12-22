# Developing

This document describes some useful info when developing for the `yamaha_ynca` integration.

## Add a command

Adding a command is usually easy when it follows the common patterns.

As an example lets add the ExtraBass switch.

First the `ynca` needs to support the command. For info on how to add it there see <https://github.com/mvdwetering/ynca/tree/master/docs>. Next make sure to update the `ynca` version used by the integration contains that command. Use the `bump_ynca_version.sh` script to update the version in all the required places (during development you can also install the ynca package in the venv).

Next the related entity platform should be extended. In this case we will be adding a switch, so `switch.py` is the file to edit. Other entity platforms can be updated similarly.

To add the new command switch it is enough to just add a new [entity description](https://developers.home-assistant.io/docs/core/entity/#entity-description) entry to the ZONE_ENTITY_DESCRIPTIONS list like below.

```python
    YncaSwitchEntityDescription(
        key="exbass",
        entity_category=EntityCategory.CONFIG,
        on=ynca.ExBass.AUTO,
        off=ynca.ExBass.OFF,
    ),
```

The `key` field is the attribute name in the ynca package, it is also used as translation key.
More info about `entity_category` can be found [here in the Home Assistant developer documentation](https://developers.home-assistant.io/docs/core/entity/).
The `on`and `off` fields are the values to be used when turning the switch on/off.

Check out the documentation of `YncaSwitchEntityDescription` for more details.

That is the code part done. With this info the entity platform implementation will take care of handling incoming commands to update the switch and call the `ynca` package with the correct data when the switch changes in Home Assistant.

Now update the translations by adding a section matching the `key` under `entities/switch` similar to the others. This will make sure the switch gets a proper name.

```json
      "exbass": {
        "name": "Extra Bass"
      },
```

Only thing left to do now is add/extend tests. Since this command is very straight forward, just fix the test by updating the amount of switch entities that is created during setup.

And thats is all that is needed.
(I would still recommend to do a quick manual test against a real receiver or the `debug_server`)
