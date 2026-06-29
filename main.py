"""AGV Monitor Pro V0.2 - Main application."""

import logging
import time
import sys
import os

import yaml

from src.mqtt_listener import MQTTListener
from src.alarm_engine import AlarmEngine
from src.notifier import Notifier
from src.models import AGVStatus
from src.ui.dashboard import Dashboard

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class AGVMonitorApp:
    """Main AGV Monitor Pro application."""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config = self._load_config(config_file)
        
        self.mqtt_listener = MQTTListener(
            broker=self.config['mqtt']['broker'],
            port=self.config['mqtt']['port'],
            username=self.config['mqtt'].get('username'),
            password=self.config['mqtt'].get('password'),
            status_topic=self.config['mqtt']['status_topic'],
            keepalive=self.config['mqtt']['keepalive'],
        )
        
        self.alarm_engine = AlarmEngine(
            debounce_seconds=self.config['alarm'].get('debounce_time', 2.0)
        )
        
        sound_file = self.config['alarm'].get('sound_file')
        if sound_file and not os.path.isabs(sound_file):
            sound_file = os.path.join(os.path.dirname(__file__), sound_file)
        
        self.notifier = Notifier(
            sound_file=sound_file,
            enabled=self.config['alarm'].get('enabled', True)
        )
        
        self.dashboard = Dashboard()
        self.global_alarm_enabled = self.config['alarm'].get('enabled', True)
        self.mqtt_listener.set_status_callback(self._on_agv_status)
    
    def _load_config(self, config_file: str) -> dict:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"⚙️  Config loaded: {config_file}")
            return config
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_file}")
            raise
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def _on_agv_status(self, status: AGVStatus):
        result = self.alarm_engine.process_status(status)
        
        if not self.global_alarm_enabled:
            return
        
        for agv_id, alarm_type, details in result['triggered_alarms']:
            logger.warning(f"🔔 ALARM TRIGGERED: AGV{agv_id} {alarm_type.value}")
            self.notifier.play_alarm_sound()
            title = f"AGV{agv_id}"
            message = details.get('message', 'Alarm')
            self.notifier.show_notification(title, message, agv_id, details)
        
        for agv_id, alarm_type in result['cleared_alarms']:
            logger.info(f"✅ ALARM CLEARED: AGV{agv_id} {alarm_type.value}")
    
    def run(self):
        try:
            logger.info("\n" + "="*50)
            logger.info("🚀 AGV Monitor Pro V0.2")
            logger.info("="*50 + "\n")
            
            self.mqtt_listener.connect()
            self.mqtt_listener.start_loop_background()
            
            logger.info("⏳ Listening for AGV status updates...\n")
            time.sleep(1)
            
            while True:
                agv_states = self.alarm_engine.get_all_agv_states()
                self.dashboard.render(agv_states, self.global_alarm_enabled)
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutting down...")
            self.mqtt_listener.stop_loop_background()
            self.mqtt_listener.disconnect()
            logger.info("👋 Goodbye!\n")
        
        except Exception as e:
            logger.error(f"❌ Application error: {e}", exc_info=True)
            raise
    
    def run_debug(self):
        logger.info("\n" + "="*50)
        logger.info("🐛 DEBUG MODE (Simulated Data)")
        logger.info("="*50 + "\n")
        
        test_cases = [
            AGVStatus(agv_id=1, auto=True, error=False, event_fault=[], agv_state="NONE"),
            AGVStatus(agv_id=2, auto=False, error=False, event_fault=[], agv_state="NONE"),
            AGVStatus(agv_id=3, auto=True, error=True, event_fault=[], agv_state="NONE"),
            AGVStatus(agv_id=4, auto=True, error=False, event_fault=[], agv_state="NONE"),
            AGVStatus(agv_id=5, auto=True, error=False, event_fault=["B30200"], agv_state="CHARGE_START"),
            AGVStatus(agv_id=6, auto=True, error=False, event_fault=[], agv_state="PUSH"),
            AGVStatus(agv_id=7, auto=True, error=False, event_fault=["B30402"], agv_state="STOP"),
        ]
        
        logger.info("📊 Simulating alarm events...\n")
        
        logger.info("\n--- Cycle 1: Initial State with Alarms ---")
        for status in test_cases:
            self._on_agv_status(status)
        
        agv_states = self.alarm_engine.get_all_agv_states()
        self.dashboard.render(agv_states, self.global_alarm_enabled)
        time.sleep(3)
        
        logger.info("\n--- Cycle 2: AGV2 Recovers to AUTO Mode ---")
        test_cases[1] = AGVStatus(agv_id=2, auto=True, error=False, event_fault=[], agv_state="NONE")
        for status in test_cases:
            self._on_agv_status(status)
        
        agv_states = self.alarm_engine.get_all_agv_states()
        self.dashboard.render(agv_states, self.global_alarm_enabled)
        time.sleep(3)
        
        logger.info("\n--- Cycle 3: Recovery ---")
        test_cases[2] = AGVStatus(agv_id=3, auto=True, error=False, event_fault=[], agv_state="NONE")
        test_cases[4] = AGVStatus(agv_id=5, auto=True, error=False, event_fault=[], agv_state="CHARGING")
        for status in test_cases:
            self._on_agv_status(status)
        
        agv_states = self.alarm_engine.get_all_agv_states()
        self.dashboard.render(agv_states, self.global_alarm_enabled)
        time.sleep(3)
        
        logger.info("\n✅ Debug simulation complete\n")


if __name__ == "__main__":
    app = AGVMonitorApp()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        app.run_debug()
    else:
        app.run()
