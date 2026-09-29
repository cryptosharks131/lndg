import unittest
from unittest.mock import patch, MagicMock
import sys
from types import ModuleType

# Provide mock settings if lndg.settings does not exist in environment
if 'lndg.settings' not in sys.modules:
    mock_settings = ModuleType('lndg.settings')
    mock_settings.LND_MACAROON_PATH = '/tmp/fake_macaroon'
    mock_settings.LND_TLS_PATH = '/tmp/fake_tls'
    mock_settings.LND_RPC_SERVER = 'localhost:10009'
    mock_settings.LND_MAX_MESSAGE = 50
    sys.modules['lndg.settings'] = mock_settings
    import lndg
    lndg.settings = mock_settings

class TestLNDConnect(unittest.TestCase):

    def test_get_channel_options_keepalive(self):
        from gui.lnd_deps.lnd_connect import get_channel_options
        options = dict(get_channel_options())

        self.assertIn('grpc.max_send_message_length', options)
        self.assertIn('grpc.max_receive_message_length', options)
        self.assertEqual(options.get('grpc.keepalive_time_ms'), 30000)
        self.assertEqual(options.get('grpc.keepalive_timeout_ms'), 10000)
        self.assertEqual(options.get('grpc.keepalive_permit_without_calls'), 1)
        self.assertEqual(options.get('grpc.http2.max_pings_without_data'), 0)
        self.assertEqual(options.get('grpc.http2.min_time_between_pings_ms'), 10000)
        self.assertEqual(options.get('grpc.http2.min_ping_interval_without_data_ms'), 10000)

    @patch('gui.lnd_deps.lnd_connect.grpc.secure_channel')
    @patch('gui.lnd_deps.lnd_connect.get_creds')
    def test_lnd_connect_uses_channel_options(self, mock_get_creds, mock_secure_channel):
        from gui.lnd_deps import lnd_connect
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds
        lnd_connect.creds = mock_creds

        lnd_connect.lnd_connect()
        mock_secure_channel.assert_called_once()
        _, kwargs = mock_secure_channel.call_args
        options = dict(kwargs.get('options'))
        self.assertEqual(options.get('grpc.keepalive_time_ms'), 30000)
        self.assertEqual(options.get('grpc.keepalive_timeout_ms'), 10000)

    @patch('gui.lnd_deps.lnd_connect.grpc.aio.secure_channel')
    @patch('gui.lnd_deps.lnd_connect.get_creds')
    def test_async_lnd_connect_uses_channel_options(self, mock_get_creds, mock_aio_secure_channel):
        from gui.lnd_deps import lnd_connect
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds
        lnd_connect.creds = mock_creds

        lnd_connect.async_lnd_connect()
        mock_aio_secure_channel.assert_called_once()
        _, kwargs = mock_aio_secure_channel.call_args
        options = dict(kwargs.get('options'))
        self.assertEqual(options.get('grpc.keepalive_time_ms'), 30000)
        self.assertEqual(options.get('grpc.keepalive_timeout_ms'), 10000)

if __name__ == '__main__':
    unittest.main()
