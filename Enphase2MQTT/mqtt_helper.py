import paho.mqtt.client as mqtt
import time
import logging
from typing import Callable, Optional, Dict, Any, NamedTuple
from queue import Queue
from collections import namedtuple

# Message structure for the queue
QueuedMessage = namedtuple('QueuedMessage', ['topic', 'payload', 'qos', 'retain'])

class MQTTClient:
    """
    MQTT Client wrapper with automatic reconnection and event callbacks.
    """
    
    def __init__(self, broker: str, port: int = 1883, client_id: str = "", 
                 reconnect_interval: int = 30):
        """
        Initialize MQTT client.
        
        Args:
            broker: MQTT broker hostname or IP
            port: MQTT broker port (default: 1883)
            client_id: Unique client identifier (auto-generated if empty)
            reconnect_interval: Time in seconds between reconnection attempts (default: 30)
        """
        self.broker = broker
        self.port = port
        self.reconnect_interval = reconnect_interval
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
        
        # Internal callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # User callbacks
        self._user_on_connect: Optional[Callable] = None
        self._user_on_disconnect: Optional[Callable] = None
        self._user_on_message: Optional[Callable] = None
        
        # Subscriptions to restore after reconnect
        self._subscriptions: Dict[str, int] = {}
        
        # Connection state
        self._connected = False
        self._running = False
        self._last_reconnect_attempt = 0
        
        # Message queue for offline publishing
        self._message_queue: Queue = Queue()
        
        # Logging
        self.logger = logging.getLogger(__name__)
    
    def set_auth(self, username: str, password: str):
        """Set username and password for broker authentication."""
        self.client.username_pw_set(username, password)
    
    def on_connect(self, callback: Callable[[str, Any, Dict, int], None]):
        """
        Set callback for connection events.
        
        Callback signature: callback(client, userdata, flags, rc)
        """
        self._user_on_connect = callback
    
    def on_disconnect(self, callback: Callable[[str, Any, int], None]):
        """
        Set callback for disconnection events.
        
        Callback signature: callback(client, userdata, rc)
        """
        self._user_on_disconnect = callback
    
    def on_message(self, callback: Callable[[str, Any, Any], None]):
        """
        Set callback for received messages.
        
        Callback signature: callback(client, userdata, message)
        """
        self._user_on_message = callback
    
    def _on_connect(self, client, userdata, flags, rc):
        """Internal connect callback."""
        self._connected = (rc == 0)
        
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            # Restore subscriptions after reconnect
            for topic, qos in self._subscriptions.items():
                self.logger.info(f"Re-subscribing to {topic}")
                client.subscribe(topic, qos)
            
            # Process queued messages
            self._process_message_queue()
        else:
            self.logger.error(f"Connection failed with code {rc}")
        
        # Call user callback
        if self._user_on_connect:
            self._user_on_connect(client, userdata, flags, rc)
    
    def _on_disconnect(self, client, userdata, rc):
        """Internal disconnect callback."""
        self._connected = False
        
        if rc != 0:
            self.logger.warning(f"Unexpected disconnect (code: {rc}), will attempt reconnect")
        else:
            self.logger.info("Disconnected from MQTT broker")
        
        # Call user callback
        if self._user_on_disconnect:
            self._user_on_disconnect(client, userdata, rc)
    
    def _on_message(self, client, userdata, message):
        """Internal message callback."""
        self.logger.debug(f"Message received on {message.topic}: {message.payload.decode()}")
        
        # Call user callback
        if self._user_on_message:
            self._user_on_message(client, userdata, message)
    
    def connect(self) -> bool:
        """
        Connect to MQTT broker.
        Does not fail if connection is unsuccessful - loop() will retry.
        
        Returns:
            True if connection initiated successfully, False otherwise
        """
        try:
            self.logger.info(f"Connecting to {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, keepalive=60)
            self._running = True
            self._last_reconnect_attempt = time.time()
            return True
        except Exception as e:
            self.logger.warning(f"Initial connection failed: {e}")
            self.logger.info(f"Will retry connection every {self.reconnect_interval} seconds in loop()")
            self._running = True  # Still set running to True so loop() will retry
            self._last_reconnect_attempt = time.time()
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self._running = False
        if self._connected:
            self.logger.info("Disconnecting from MQTT broker...")
            self.client.disconnect()
    
    def subscribe(self, topic: str, qos: int = 0):
        """
        Subscribe to a topic.
        
        Args:
            topic: Topic string or pattern
            qos: Quality of Service level (0, 1, or 2)
        """
        self._subscriptions[topic] = qos
        if self._connected:
            self.logger.info(f"Subscribing to {topic}")
            self.client.subscribe(topic, qos)
    
    def unsubscribe(self, topic: str):
        """Unsubscribe from a topic."""
        if topic in self._subscriptions:
            del self._subscriptions[topic]
        if self._connected:
            self.logger.info(f"Unsubscribing from {topic}")
            self.client.unsubscribe(topic)
    
    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        """
        Publish a message to a topic.
        If not connected, the message is queued for later delivery.
        
        Args:
            topic: Topic to publish to
            payload: Message payload
            qos: Quality of Service level
            retain: Retain flag
        """
        if self._connected:
            try:
                result = self.client.publish(topic, payload, qos, retain)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.debug(f"Published to {topic}: {payload}")
                else:
                    self.logger.warning(f"Publish failed, queuing message for {topic}")
                    self._queue_message(topic, payload, qos, retain)
            except Exception as e:
                self.logger.error(f"Publish error: {e}, queuing message")
                self._queue_message(topic, payload, qos, retain)
        else:
            self.logger.debug(f"Not connected, queuing message for {topic}")
            self._queue_message(topic, payload, qos, retain)
    
    def _queue_message(self, topic: str, payload: str, qos: int, retain: bool):
        """Add a message to the queue."""
        msg = QueuedMessage(topic, payload, qos, retain)
        self._message_queue.put(msg)
        self.logger.debug(f"Message queued (queue size: {self._message_queue.qsize()})")
    
    def _process_message_queue(self):
        """Process all queued messages."""
        if self._message_queue.empty():
            return
        
        self.logger.info(f"Processing {self._message_queue.qsize()} queued messages...")
        
        while not self._message_queue.empty() and self._connected:
            try:
                msg = self._message_queue.get_nowait()
                self.client.publish(msg.topic, msg.payload, msg.qos, msg.retain)
                self.logger.debug(f"Queued message published to {msg.topic}")
            except Exception as e:
                self.logger.error(f"Error publishing queued message: {e}")
                # Put message back in queue
                self._message_queue.put(msg)
                break
    
    def _attempt_reconnect(self):
        """Attempt to reconnect to the broker."""
        current_time = time.time()
        
        # Check if enough time has passed since last attempt
        if current_time - self._last_reconnect_attempt < self.reconnect_interval:
            return
        
        self._last_reconnect_attempt = current_time
        self.logger.info(f"Attempting to reconnect to {self.broker}:{self.port}...")
        
        try:
            # Try reconnect first (for existing connection)
            self.client.reconnect()
        except Exception as reconnect_error:
            # If reconnect fails, try a fresh connect (for initial connection failure)
            try:
                self.client.connect(self.broker, self.port, keepalive=60)
            except Exception as connect_error:
                self.logger.warning(f"Connection attempt failed: {connect_error}")
    
    def loop(self, timeout: float = 1.0):
        """
        Process network events. Should be called regularly.
        Handles automatic reconnection if disconnected.
        
        Args:
            timeout: Maximum time to block in seconds
        """
        if self._running:
            # If not connected, attempt reconnection
            if not self._connected:
                self._attempt_reconnect()
            
            # Process network events
            self.client.loop(timeout)
    
    def loop_forever(self):
        """
        Run blocking loop. Handles reconnection automatically.
        """
        self.client.loop_forever()
    
    def is_connected(self) -> bool:
        """Check if currently connected to broker."""
        return self._connected
    
    def get_queue_size(self) -> int:
        """Get the number of messages in the queue."""
        return self._message_queue.qsize()
    
    def clear_queue(self):
        """Clear all queued messages."""
        while not self._message_queue.empty():
            try:
                self._message_queue.get_nowait()
            except:
                break
        self.logger.info("Message queue cleared")
