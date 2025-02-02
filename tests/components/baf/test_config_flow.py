"""Test the baf config flow."""
import asyncio
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.components.baf.const import DOMAIN
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)

from tests.common import MockConfigEntry


async def test_form_user(hass):
    """Test we get the user form."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch("homeassistant.components.baf.config_flow.Device.async_run",), patch(
        "homeassistant.components.baf.config_flow.Device.async_wait_available",
    ), patch(
        "homeassistant.components.baf.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_IP_ADDRESS: "127.0.0.1"},
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "127.0.0.1"
    assert result2["data"] == {CONF_IP_ADDRESS: "127.0.0.1"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("homeassistant.components.baf.config_flow.Device.async_run",), patch(
        "homeassistant.components.baf.config_flow.Device.async_wait_available",
        side_effect=asyncio.TimeoutError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_IP_ADDRESS: "127.0.0.1"},
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {CONF_IP_ADDRESS: "cannot_connect"}


async def test_form_unknown_exception(hass):
    """Test we handle unknown exceptions."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("homeassistant.components.baf.config_flow.Device.async_run",), patch(
        "homeassistant.components.baf.config_flow.Device.async_wait_available",
        side_effect=Exception,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_IP_ADDRESS: "127.0.0.1"},
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_zeroconf_discovery(hass):
    """Test we can setup from zeroconf discovery."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=zeroconf.ZeroconfServiceInfo(
            host="127.0.0.1",
            addresses=["127.0.0.1"],
            hostname="mock_hostname",
            name="testfan",
            port=None,
            properties={"name": "My Fan", "model": "Haiku", "uuid": "1234"},
            type="mock_type",
        ),
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.baf.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "My Fan"
    assert result2["data"] == {CONF_IP_ADDRESS: "127.0.0.1"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_zeroconf_updates_existing_ip(hass):
    """Test we can setup from zeroconf discovery."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_IP_ADDRESS: "127.0.0.2"}, unique_id="1234"
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=zeroconf.ZeroconfServiceInfo(
            host="127.0.0.1",
            addresses=["127.0.0.1"],
            hostname="mock_hostname",
            name="testfan",
            port=None,
            properties={"name": "My Fan", "model": "Haiku", "uuid": "1234"},
            type="mock_type",
        ),
    )
    assert result["type"] == RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_IP_ADDRESS] == "127.0.0.1"


async def test_zeroconf_rejects_ipv6(hass):
    """Test zeroconf discovery rejects ipv6."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=zeroconf.ZeroconfServiceInfo(
            host="fd00::b27c:63bb:cc85:4ea0",
            addresses=["fd00::b27c:63bb:cc85:4ea0"],
            hostname="mock_hostname",
            name="testfan",
            port=None,
            properties={"name": "My Fan", "model": "Haiku", "uuid": "1234"},
            type="mock_type",
        ),
    )
    assert result["type"] == RESULT_TYPE_ABORT
    assert result["reason"] == "ipv6_not_supported"
