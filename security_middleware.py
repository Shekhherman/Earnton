import logging
import time
from typing import Dict, Any, Optional
import asyncio
from threading import Lock
from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils.exceptions import Throttled

# Configure logging
logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseMiddleware):
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.lock = Lock()
        self.requests = {
            'global': {},  # {timestamp: count}
            'ip': {},     # {ip: {timestamp: count}}
            'user': {},    # {user_id: {timestamp: count}}
            'device': {}   # {device_id: {timestamp: count}}
        }
        self.failed_attempts = {}
        self.sessions = {}
        self.cleanup_task = None
        self.anomalies = []
        self.threats = []
        self.security_events = []
        self.scanning_results = {}
        self.blocked_ips = set()
        self.blocked_devices = set()
        self.blocked_users = set()
        self.device_fingerprints = {}
        self.location_cache = {}
        self.token_cache = {}
        self.encryption_keys = {}
        
        # Initialize security components
        self.initialize_security_components()
        
    def initialize_security_components(self):
        """Initialize all security components."""
        # Initialize encryption
        self.initialize_encryption()
        
        # Initialize tokenization
        self.initialize_tokenization()
        
        # Initialize scanning providers
        self.initialize_scanning()
        
        # Initialize monitoring
        self.initialize_monitoring()
        
        # Initialize logging
        self.initialize_logging()
        
    def initialize_encryption(self):
        """Initialize encryption system."""
        if self.config['data_protection']['encryption']['enabled']:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            
            self.cipher = Cipher(
                algorithms.AES(os.urandom(32)),
                modes.CBC(os.urandom(16)),
                backend=default_backend()
            )
            
    def initialize_tokenization(self):
        """Initialize tokenization system."""
        if self.config['data_protection']['tokenization']['enabled']:
            from jwt import encode, decode
            from time import time
            
            self.jwt_secret = os.urandom(32)
            self.hmac_secret = os.urandom(32)
            
    def initialize_scanning(self):
        """Initialize scanning providers."""
        if self.config['scanning']['enabled']:
            self.scanning_providers = {
                'vulnerability': [],
                'malware': [],
                'content': []
            }
            
            # Initialize vulnerability scanning
            if 'nvd' in self.config['scanning']['vulnerability']['providers']:
                self.scanning_providers['vulnerability'].append(NVDSecurityScanner())
            if 'cve' in self.config['scanning']['vulnerability']['providers']:
                self.scanning_providers['vulnerability'].append(CVESecurityScanner())
            
            # Initialize malware scanning
            if 'virustotal' in self.config['scanning']['malware']['providers']:
                self.scanning_providers['malware'].append(VirusTotalScanner())
            if 'clamav' in self.config['scanning']['malware']['providers']:
                self.scanning_providers['malware'].append(ClamAVScanner())
            
            # Initialize content scanning
            if 'google_safe_browsing' in self.config['scanning']['content']['providers']:
                self.scanning_providers['content'].append(GoogleSafeBrowsing())
            if 'phish_tank' in self.config['scanning']['content']['providers']:
                self.scanning_providers['content'].append(PhishTank())
                
    def initialize_monitoring(self):
        """Initialize monitoring system."""
        if self.config['monitoring']['enabled']:
            self.anomaly_detector = AnomalyDetector(
                threshold=self.config['monitoring']['anomaly_detection']['threshold'],
                window=self.config['monitoring']['anomaly_detection']['window']
            )
            
            self.threat_detector = ThreatDetector(
                providers=self.config['monitoring']['threat_detection']['providers'],
                update_interval=self.config['monitoring']['threat_detection']['update_interval']
            )
            
    def initialize_logging(self):
        """Initialize logging system."""
        if self.config['logging']['enabled']:
            self.logger = logging.getLogger('security')
            self.logger.setLevel(self.config['logging']['level'])
            
            # Add file handler
            file_handler = logging.FileHandler(self.config['logging']['handlers']['file']['filename'])
            file_handler.setLevel(self.config['logging']['level'])
            file_handler.setFormatter(logging.Formatter(self.config['logging']['format']))
            self.logger.addHandler(file_handler)
            
            # Add syslog handler if enabled
            if self.config['logging']['handlers']['syslog']['enabled']:
                try:
                    from logging.handlers import SysLogHandler
                    syslog_handler = SysLogHandler(address=self.config['logging']['handlers']['syslog']['address'])
                    syslog_handler.setLevel(self.config['logging']['level'])
                    syslog_handler.setFormatter(logging.Formatter(self.config['logging']['format']))
                    self.logger.addHandler(syslog_handler)
                except Exception as e:
                    self.logger.error(f"Failed to initialize syslog handler: {str(e)}")

    def _cleanup_requests(self):
        """Cleanup old request data."""
        now = time.time()
        
        # Cleanup all request types
        for request_type in ['global', 'ip', 'user', 'device']:
            if request_type in self.requests:
                for key, timestamps in list(self.requests[request_type].items()):
                    self.requests[request_type][key] = {
                        t: c for t, c in timestamps.items()
                        if now - t < self.config['rate_limit'][request_type]['window']
                    }
                    
                    # Remove empty entries
                    if not self.requests[request_type][key]:
                        del self.requests[request_type][key]
        
        # Cleanup failed attempts
        self.failed_attempts = {
            k: v for k, v in self.failed_attempts.items()
            if now - v['last_attempt'] < self.config['login_lockout_duration']
        }
        
        # Cleanup expired sessions
        self.sessions = {
            k: v for k, v in self.sessions.items()
            if now - v['created_at'] < self.config['session_timeout']
        }
        
        # Cleanup anomalies
        self.anomalies = [a for a in self.anomalies if now - a['timestamp'] < 86400]  # Keep last 24h
        
        # Cleanup threats
        self.threats = [t for t in self.threats if now - t['timestamp'] < 86400]  # Keep last 24h
        
        # Cleanup security events
        self.security_events = [e for e in self.security_events if now - e['timestamp'] < 86400]  # Keep last 24h
        
        # Cleanup scanning results
        self.scanning_results = {
            k: v for k, v in self.scanning_results.items()
            if now - v['timestamp'] < 86400  # Keep last 24h
        }
        
        # Cleanup blocked IPs
        self.blocked_ips = {
            ip for ip in self.blocked_ips
            if now - self._get_blocked_timestamp(ip) < self.config['security_response']['blocking']['duration']
        }
        
        # Cleanup blocked devices
        self.blocked_devices = {
            device for device in self.blocked_devices
            if now - self._get_blocked_timestamp(device) < self.config['security_response']['blocking']['duration']
        }
        
        # Cleanup blocked users
        self.blocked_users = {
            user for user in self.blocked_users
            if now - self._get_blocked_timestamp(user) < self.config['security_response']['blocking']['duration']
        }
        
    def _get_blocked_timestamp(self, identifier: str) -> float:
        """Get the timestamp when an identifier was blocked."""
        for event in self.security_events:
            if event['type'] == 'block' and event['identifier'] == identifier:
                return event['timestamp']
        return 0

    def _start_cleanup(self):
        """Start periodic cleanup task."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        async def cleanup():
            while True:
                self._cleanup_requests()
                await asyncio.sleep(self.config['session_cleanup_interval'])
        
        self.cleanup_task = asyncio.create_task(cleanup())

    def _check_rate_limit(self, user_id: int, ip: str, device_id: str) -> bool:
        """Check rate limits for global, IP, user, and device."""
        now = time.time()
        
        # Check if blocked
        if ip in self.blocked_ips:
            return False
        if device_id in self.blocked_devices:
            return False
        if user_id in self.blocked_users:
            return False
        
        # Check global rate limit with adaptive adjustment
        global_count = sum(
            c for t, c in self.requests['global'].items()
            if now - t < self.config['rate_limit']['global']['window']
        )
        
        # Apply adaptive rate limiting
        if self.config['rate_limit']['global']['adaptive']:
            threshold = self.config['rate_limit']['global']['requests']
            if global_count > threshold * self.config['rate_limit']['global']['threshold']:
                threshold *= self.config['rate_limit']['global']['increase_factor']
            
        if global_count >= threshold:
            return False
        
        # Check IP rate limit with device fingerprinting
        if ip in self.requests['ip']:
            ip_count = sum(
                c for t, c in self.requests['ip'][ip].items()
                if now - t < self.config['rate_limit']['ip']['window']
            )
            
            # Check device fingerprint
            if self.config['rate_limit']['ip']['device_fingerprinting']:
                device_count = sum(
                    c for t, c in self.requests['device'][device_id].items()
                    if now - t < self.config['rate_limit']['device']['window']
                )
                if device_count >= self.config['rate_limit']['device']['requests']:
                    return False
            
            if ip_count >= self.config['rate_limit']['ip']['requests']:
                return False
        
        # Check user rate limit with behavior analysis
        if user_id in self.requests['user']:
            user_count = sum(
                c for t, c in self.requests['user'][user_id].items()
                if now - t < self.config['rate_limit']['user']['window']
            )
            
            # Check behavior patterns
            if self.config['rate_limit']['user']['behavior_analysis']:
                if self._detect_behavior_anomaly(user_id):
                    return False
            
            if user_count >= self.config['rate_limit']['user']['requests']:
                return False
        
        return True
        
    def _detect_behavior_anomaly(self, user_id: int) -> bool:
        """Detect behavior anomalies for a user."""
        now = time.time()
        
        # Get user's request history
        user_requests = self.requests['user'].get(user_id, {})
        
        # Calculate request rate
        request_times = [t for t in user_requests.keys()]
        if len(request_times) < 2:
            return False
            
        time_diffs = [request_times[i+1] - request_times[i] 
                     for i in range(len(request_times)-1)]
        avg_diff = sum(time_diffs) / len(time_diffs)
        
        # Check for rapid requests
        if min(time_diffs) < 0.1:  # Less than 100ms between requests
            return True
            
        # Check for unusual patterns
        if max(time_diffs) - min(time_diffs) > 3600:  # More than 1 hour difference
            return True
            
        return False

    def _record_request(self, user_id: int, ip: str, device_id: str, message: str):
        """Record a request with all security checks."""
        now = time.time()
        
        # Record global request
        self.requests['global'][now] = 1
        
        # Record IP request
        if ip not in self.requests['ip']:
            self.requests['ip'][ip] = {}
        self.requests['ip'][ip][now] = 1
        
        # Record device request
        if device_id not in self.requests['device']:
            self.requests['device'][device_id] = {}
        self.requests['device'][device_id][now] = 1
        
        # Record user request
        if user_id not in self.requests['user']:
            self.requests['user'][user_id] = {}
        self.requests['user'][user_id][now] = 1
        
        # Create device fingerprint
        if self.config['authentication']['device_verification']['enabled']:
            self._create_device_fingerprint(device_id, ip, message)
            
        # Check location
        if self.config['authentication']['location_verification']['enabled']:
            self._verify_location(ip)
            
        # Validate input
        if not self._validate_input(message):
            raise ValueError("Invalid input detected")
            
        # Scan content
        if self.config['scanning']['enabled']:
            self._scan_content(message)
            
        # Log security event
        self._log_security_event('request', {
            'user_id': user_id,
            'ip': ip,
            'device_id': device_id,
            'timestamp': now
        })
        
    def _create_device_fingerprint(self, device_id: str, ip: str, message: str):
        """Create device fingerprint."""
        fingerprint = {
            'device_id': device_id,
            'ip': ip,
            'user_agent': message.from_user.user_agent,
            'timestamp': time.time()
        }
        self.device_fingerprints[device_id] = fingerprint
        
    def _verify_location(self, ip: str) -> bool:
        """Verify user's location."""
        if ip in self.location_cache:
            return self.location_cache[ip]
            
        # Get location from IP
        try:
            location = self._get_location_from_ip(ip)
            self.location_cache[ip] = location
            
            # Check if location is within allowed range
            max_distance = self.config['authentication']['location_verification']['max_distance']
            if location['distance'] > max_distance:
                raise ValueError(f"Location too far: {location['distance']} km")
                
            return True
        except Exception as e:
            self.logger.error(f"Location verification failed: {str(e)}")
            return False
            
    def _get_location_from_ip(self, ip: str) -> Dict[str, Any]:
        """Get location information from IP address."""
        # TODO: Implement IP geolocation lookup
        return {
            'latitude': 0.0,
            'longitude': 0.0,
            'distance': 0.0,
            'country': 'Unknown'
        }
        
    def _validate_input(self, message: str) -> bool:
        """Validate input against security patterns."""
        # Check SQL injection patterns
        if self.config['input_validation']['sql_injection']['enabled']:
            if any(p in message for p in self.config['input_validation']['sql_injection']['patterns']):
                raise ValueError("SQL injection attempt detected")
                
        # Check XSS patterns
        if self.config['input_validation']['xss']['enabled']:
            if any(p in message for p in self.config['input_validation']['xss']['patterns']):
                raise ValueError("XSS attempt detected")
                
        # Check command injection patterns
        if self.config['input_validation']['command_injection']['enabled']:
            if any(p in message for p in self.config['input_validation']['command_injection']['patterns']):
                raise ValueError("Command injection attempt detected")
                
        # Check file injection patterns
        if self.config['input_validation']['file_injection']['enabled']:
            if any(p in message for p in self.config['input_validation']['file_injection']['patterns']):
                raise ValueError("File injection attempt detected")
                
        return True
        
    def _scan_content(self, message: str):
        """Scan content for threats."""
        if self.config['scanning']['enabled']:
            # Scan for vulnerabilities
            for scanner in self.scanning_providers['vulnerability']:
                if scanner.scan(message):
                    self._log_security_event('vulnerability', {
                        'message': message,
                        'scanner': scanner.name,
                        'timestamp': time.time()
                    })
                    
            # Scan for malware
            for scanner in self.scanning_providers['malware']:
                if scanner.scan(message):
                    self._log_security_event('malware', {
                        'message': message,
                        'scanner': scanner.name,
                        'timestamp': time.time()
                    })
                    
            # Scan for malicious content
            for scanner in self.scanning_providers['content']:
                if scanner.scan(message):
                    self._log_security_event('malicious_content', {
                        'message': message,
                        'scanner': scanner.name,
                        'timestamp': time.time()
                    })
                    
    def _log_security_event(self, event_type: str, data: Dict[str, Any]):
        """Log security events."""
        if self.config['logging']['enabled']:
            event = {
                'type': event_type,
                'data': data,
                'timestamp': time.time()
            }
            self.security_events.append(event)
            
            # Log to file and syslog
            self.logger.info(f"Security event: {event_type} - {data}")
            
            # Check for anomalies
            if self.config['monitoring']['enabled']:
                self.anomaly_detector.detect_anomaly(event)
                
            # Check for threats
            if self.config['scanning']['enabled']:
                self.threat_detector.detect_threat(event)
                
    def _handle_security_event(self, event: Dict[str, Any]):
        """Handle security events."""
        if event['type'] in ['vulnerability', 'malware', 'malicious_content']:
            # Block the source
            self._block_source(event['data'])
            
            # Notify administrators
            self._notify_administrators(event)
            
            # Log the event
            self._log_security_event('blocked', {
                'reason': event['type'],
                'data': event['data'],
                'timestamp': time.time()
            })
            
    def _block_source(self, data: Dict[str, Any]):
        """Block a source based on security event."""
        if 'ip' in data:
            self.blocked_ips.add(data['ip'])
        if 'device_id' in data:
            self.blocked_devices.add(data['device_id'])
        if 'user_id' in data:
            self.blocked_users.add(data['user_id'])
            
    def _notify_administrators(self, event: Dict[str, Any]):
        """Notify administrators of security events."""
        if self.config['security_response']['notifications']['enabled']:
            # Send email notification
            if 'email' in self.config['security_response']['notifications']['providers']:
                self._send_email_notification(event)
                
            # Send SMS notification
            if 'sms' in self.config['security_response']['notifications']['providers']:
                self._send_sms_notification(event)
                
            # Send Telegram notification
            if 'telegram' in self.config['security_response']['notifications']['providers']:
                self._send_telegram_notification(event)
                
    def _send_email_notification(self, event: Dict[str, Any]):
        """Send email notification."""
        # TODO: Implement email notification
        pass
        
    def _send_sms_notification(self, event: Dict[str, Any]):
        """Send SMS notification."""
        # TODO: Implement SMS notification
        pass
        
    def _send_telegram_notification(self, event: Dict[str, Any]):
        """Send Telegram notification."""
        # TODO: Implement Telegram notification
        pass

    async def on_pre_process_message(self, message: types.Message, data: Dict[str, Any]):
        """Process message before handlers."""
        try:
            # Get user IP
            ip = message.from_user.id  # Using user ID as IP for Telegram
            
            # Check rate limits
            if not self._check_rate_limit(message.from_user.id, ip):
                raise Throttled(key='global_rate_limit')
                
            # Record request
            self._record_request(message.from_user.id, ip)
            
            # Check message length
            if len(message.text or '') > self.config['max_message_length']:
                raise ValueError(f"Message too long. Max length: {self.config['max_message_length']}")
                
            # Check file size if present
            if message.document or message.photo:
                file_size = 0
                if message.document:
                    file_size = message.document.file_size
                elif message.photo:
                    file_size = max(p.file_size for p in message.photo)
                    
                if file_size > self.config['max_file_size']:
                    raise ValueError(f"File too large. Max size: {self.config['max_file_size'] / (1024 * 1024)} MB")
                    
            # Check IP whitelist/blacklist
            if self.config['ip_whitelist'] and ip not in self.config['ip_whitelist']:
                raise PermissionError("IP not allowed")
                
            if ip in self.config['ip_blacklist']:
                raise PermissionError("IP blocked")
                
            # Check user agent blacklist
            if message.from_user.user_agent and any(
                ua in message.from_user.user_agent
                for ua in self.config['user_agent_blacklist']
            ):
                raise PermissionError("User agent blocked")
                
        except Exception as e:
            logger.error(f"Security error: {str(e)}", exc_info=True)
            raise

    async def on_post_process_message(self, message: types.Message, data: Dict[str, Any], results: list):
        """Process message after handlers."""
        try:
            # Cleanup requests periodically
            if not self.cleanup_task:
                self._start_cleanup()
                
        except Exception as e:
            logger.error(f"Post-process error: {str(e)}", exc_info=True)

# Initialize security middleware
security_middleware = SecurityMiddleware(SECURITY_CONFIG)
