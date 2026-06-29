"""MQTT listener for AGV status updates."""

import json
import logging
from typing import Callable, Optional
import paho.mqtt.client as mqtt

from .models import AGVStatus

logger = logging.getLogger(__name__)


class MQTTListener:
    """Listen to MQTT for AGV status updates."""
    
    def __init__(
        self,
        broker: str,
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        status_topic: str = "CM/any/rep/agv/status",
        keepalive: int = 60,
    ):
        self.broker = broker
        self.port = port
        self.status_topic = status_topic
        self.keepalive = keepalive
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.client.username_pw_set(username, password) if username else None
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        self._on_status_callback: Optional[Callable[[AGVStatus], None]] = None
        self._running = False
    
    def set_status_callback(self, callback: Callable[[AGVStatus], None]):
        """Set callback for status updates."""
        self._on_status_callback = callback
    
    def connect(self):
        """Connect to MQTT broker."""
        try:
            self.client.connect(self.broker, self.port, self.keepalive)
            self._running = True
            logger.info(f"🔗 Connecting to MQTT: {self.broker}:{self.port}")
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.client.disconnect()
        self._running = False
    
    def start_loop_background(self):
        """Start MQTT event loop in background thread."""
        self.client.loop_start()
    
    def stop_loop_background(self):
        """Stop background MQTT event loop."""
        self.client.loop_stop()
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("✅ Connected to MQTT broker")
            client.subscribe(self.status_topic)
            logger.info(f"📨 Subscribed to: {self.status_topic}")
        else:
            logger.error(f"❌ Connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        if rc == 0:
            logger.info("Disconnected from MQTT broker")
        else:
            logger.error(f"❌ Unexpected disconnection (code {rc})")
    
    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            
            if 'data' in payload and 'message' in payload['data']:
                message = payload['data']['message']
                status_list = message.get('status_list', [])
                
                for status_dict in status_list:
                    status = self._parse_agv_status(status_dict)
                    if status and self._on_status_callback:
                        self._on_status_callback(status)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode MQTT message: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    @staticmethod
    def _parse_agv_status(status_dict: dict) -> Optional[AGVStatus]:
        try:
            return AGVStatus(
                agv_id=status_dict.get('agv_id'),
                auto=status_dict.get('auto', True),
                error=status_dict.get('error', False),
                event_fault=status_dict.get('event_fault', []),
                agv_state=status_dict.get('agv_state', ''),
                raw_data=status_dict
            )
        except Exception as e:
            logger.error(f"Failed to parse AGV status: {e}")
            return None
