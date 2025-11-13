import network
import socket
import json
import time
from machine import Pin

class IncubatorWebServer:
    def __init__(self):
        self.ap = None
        self.socket = None
        self.experiment_running = False
        self.test_mode = False
        
        # Default experiment parameters
        self.params = {
            'basal_temp': 23.0,
            'heat_shock_temp': 32.0,
            'us_type': 'BOTH',
            'min_interval': 5,
            'max_interval': 10,
            'us_duration': 1,
            'heat_duration': 2,
            'correlation': 1.0,
            'log_interval': 10
        }
        
        # Test mode parameters (shorter durations for testing)
        self.test_params = {
            'basal_temp': 23.0,
            'heat_shock_temp': 32.0,
            'us_type': 'BOTH',
            'min_interval': 1,  # 1 minute cycles
            'max_interval': 2,  # 2 minute cycles
            'us_duration': 0.2,  # 12 seconds
            'heat_duration': 0.3,  # 18 seconds
            'correlation': 1.0,
            'log_interval': 5
        }
    
    def setup_ap(self, password="incubator123"):
        """Set up Access Point"""
        self.ap = network.WLAN(network.AP_IF)
        self.ap.active(True)
        self.ap.config(essid="ESP32-Incubator", password=password, authmode=network.AUTH_WPA_WPA2_PSK)
        
        while not self.ap.active():
            time.sleep(0.1)
        
        print("Access Point created")
        print(f"SSID: ESP32-Incubator")
        print(f"Password: {password}")
        print(f"IP Address: {self.ap.ifconfig()[0]}")
        return self.ap.ifconfig()[0]
    
    def get_html_page(self):
        """Generate the main HTML page"""
        status = "Running" if self.experiment_running else "Stopped"
        mode = "Test Mode" if self.test_mode else "Normal Mode"
        current_params = self.test_params if self.test_mode else self.params
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Incubator Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f0f0f0; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
        .status {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .section {{ margin-bottom: 30px; }}
        .form-group {{ margin-bottom: 15px; }}
        label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        input, select {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
        button {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }}
        button:hover {{ background: #0056b3; }}
        .stop-btn {{ background: #dc3545; }}
        .stop-btn:hover {{ background: #c82333; }}
        .test-btn {{ background: #28a745; }}
        .test-btn:hover {{ background: #218838; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
        @media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔬 ESP32 Incubator Control</h1>
        
        <div class="status">
            <h3>Status: {status}</h3>
            <p>Mode: {mode}</p>
            <p>Current Temperature: <span id="temp">--</span>°C</p>
        </div>
        
        <div class="section">
            <h3>Experiment Parameters</h3>
            <form method="POST" action="/update_params">
                <div class="grid">
                    <div class="form-group">
                        <label>Basal Temperature (°C):</label>
                        <input type="number" name="basal_temp" value="{current_params['basal_temp']}" step="0.1" min="15" max="40">
                    </div>
                    <div class="form-group">
                        <label>Heat Shock Temperature (°C):</label>
                        <input type="number" name="heat_shock_temp" value="{current_params['heat_shock_temp']}" step="0.1" min="25" max="45">
                    </div>
                    <div class="form-group">
                        <label>US Type:</label>
                        <select name="us_type">
                            <option value="LED" {'selected' if current_params['us_type'] == 'LED' else ''}>LED Only</option>
                            <option value="VIB" {'selected' if current_params['us_type'] == 'VIB' else ''}>Vibration Only</option>
                            <option value="BOTH" {'selected' if current_params['us_type'] == 'BOTH' else ''}>Both LED & Vibration</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Correlation (-1 to 1):</label>
                        <input type="number" name="correlation" value="{current_params['correlation']}" step="0.1" min="-1" max="1">
                    </div>
                    <div class="form-group">
                        <label>Min Interval (minutes):</label>
                        <input type="number" name="min_interval" value="{current_params['min_interval']}" min="1" max="480">
                    </div>
                    <div class="form-group">
                        <label>Max Interval (minutes):</label>
                        <input type="number" name="max_interval" value="{current_params['max_interval']}" min="1" max="480">
                    </div>
                    <div class="form-group">
                        <label>US Duration (minutes):</label>
                        <input type="number" name="us_duration" value="{current_params['us_duration']}" step="0.1" min="0.1" max="60">
                    </div>
                    <div class="form-group">
                        <label>Heat Duration (minutes):</label>
                        <input type="number" name="heat_duration" value="{current_params['heat_duration']}" step="0.1" min="0.1" max="60">
                    </div>
                </div>
                <button type="submit">Update Parameters</button>
            </form>
        </div>
        
        <div class="section">
            <h3>Control</h3>
            <button onclick="location.href='/start_normal'" class="test-btn">Start Normal Experiment</button>
            <button onclick="location.href='/start_test'" class="test-btn">Start Test Mode</button>
            <button onclick="location.href='/stop'" class="stop-btn">Stop Experiment</button>
            <button onclick="location.href='/status'">Refresh Status</button>
        </div>
        
        <div class="section">
            <h3>Test Mode Info</h3>
            <p><strong>Test Mode</strong> uses shorter durations for quick testing:</p>
            <ul>
                <li>Cycle length: 1-2 minutes (vs normal 5-10 minutes)</li>
                <li>US duration: 12 seconds (vs normal 1 minute)</li>
                <li>Heat duration: 18 seconds (vs normal 2 minutes)</li>
                <li>US paired with heat shock (correlation = 1.0)</li>
            </ul>
        </div>
    </div>
    
    <script>
        // Auto-refresh temperature every 5 seconds
        setInterval(function() {{
            fetch('/api/temp')
                .then(response => response.json())
                .then(data => {{
                    document.getElementById('temp').textContent = data.temperature;
                }})
                .catch(err => console.log('Error fetching temperature'));
        }}, 5000);
    </script>
</body>
</html>
        """
        return html
    
    def handle_request(self, request):
        """Handle HTTP requests"""
        try:
            # Parse request
            lines = request.split('\n')
            if len(lines) == 0:
                return self.http_response("400 Bad Request", "Invalid request")
            
            request_line = lines[0]
            method, path, _ = request_line.split(' ')
            
            # Handle different endpoints
            if path == '/' or path == '/status':
                return self.http_response("200 OK", self.get_html_page(), "text/html")
            
            elif path == '/start_normal':
                self.test_mode = False
                self.experiment_running = True
                return self.http_response("302 Found", "", "text/html", "Location: /")
            
            elif path == '/start_test':
                self.test_mode = True
                self.experiment_running = True
                return self.http_response("302 Found", "", "text/html", "Location: /")
            
            elif path == '/stop':
                self.experiment_running = False
                return self.http_response("302 Found", "", "text/html", "Location: /")
            
            elif path == '/api/temp':
                # Return current temperature as JSON
                try:
                    from max31865 import read_temperature
                    temp = read_temperature()
                    return self.http_response("200 OK", json.dumps({"temperature": round(temp, 1)}), "application/json")
                except:
                    return self.http_response("200 OK", json.dumps({"temperature": "--"}), "application/json")
            
            elif path == '/update_params' and method == 'POST':
                # Parse form data
                body = request.split('\r\n\r\n')[1] if '\r\n\r\n' in request else ""
                params = self.parse_form_data(body)
                
                # Update parameters
                target_params = self.test_params if self.test_mode else self.params
                for key, value in params.items():
                    if key in target_params:
                        if key in ['basal_temp', 'heat_shock_temp', 'us_duration', 'heat_duration']:
                            target_params[key] = float(value)
                        elif key in ['min_interval', 'max_interval', 'log_interval']:
                            target_params[key] = int(value)
                        elif key == 'correlation':
                            try:
                                corr_val = max(-1.0, min(1.0, float(value)))
                                target_params[key] = corr_val
                            except (ValueError, TypeError):
                                print("[Web] Invalid correlation value ignored")
                        else:
                            target_params[key] = value
                
                return self.http_response("302 Found", "", "text/html", "Location: /")
            
            else:
                return self.http_response("404 Not Found", "Page not found")
        
        except Exception as e:
            print(f"Request handling error: {e}")
            return self.http_response("500 Internal Server Error", f"Error: {e}")
    
    def parse_form_data(self, body):
        """Parse URL-encoded form data"""
        params = {}
        if body:
            pairs = body.split('&')
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    # URL decode
                    key = key.replace('+', ' ').replace('%20', ' ')
                    value = value.replace('+', ' ').replace('%20', ' ')
                    params[key] = value
        return params
    
    def http_response(self, status, body, content_type="text/html", extra_headers=""):
        """Generate HTTP response"""
        headers = f"HTTP/1.1 {status}\r\n"
        headers += f"Content-Type: {content_type}\r\n"
        headers += "Connection: close\r\n"
        if extra_headers:
            headers += f"{extra_headers}\r\n"
        headers += "\r\n"
        return headers + body
    
    def start_server(self, port=80):
        """Start the web server"""
        # Clean up any existing socket
        if self.socket:
            try:
                self.socket.close()
                self.socket = None
                time.sleep(0.5)
            except:
                pass
        
        # Create new socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', port))
        self.socket.listen(5)
        print(f"Web server started on port {port}")
        return self.socket
    
    def stop_server(self):
        """Stop the web server and clean up socket"""
        if self.socket:
            try:
                self.socket.close()
                self.socket = None
                print("Web server stopped")
            except Exception as e:
                print(f"Error stopping server: {e}")
    
    def get_current_params(self):
        """Get current experiment parameters"""
        return self.test_params if self.test_mode else self.params
    
    def is_experiment_running(self):
        """Check if experiment is running"""
        return self.experiment_running
    
    def is_test_mode(self):
        """Check if in test mode"""
        return self.test_mode
    
    def stop_experiment(self):
        """Stop the experiment"""
        self.experiment_running = False 
