# experiment_setup_server.py - Minimal Web Setup Server (Memory Optimized)
import socket
import time
import gc
from machine import RTC

class ExperimentSetupServer:
    def __init__(self, device_id=""):
        self.socket = None
        self.device_id = device_id
        self.experiment_started = False
        self.stress_test_started = False
        self.rtc = RTC()
        self.time_set = False
        self.config = {
            'experiment_name': f'exp_{device_id}',
            'correlation': 1.0,
            'basal_temp': 23.0,
            'heat_shock_temp': 32.0,
            'us_type': 'BOTH',
            'min_interval': 200,
            'max_interval': 400,
            'us_duration': 30,
            'heat_duration': 30,
        }
        self.stress_config = {
            'experiment_name': f'stress_{device_id}',
            'training_temp': 23.0,
            'challenge_temp': 38.0,
            'training_duration': 30,
            'challenge_duration': 150,
            'us_led_intensity': 100,
            'us_vib_intensity': 100,
            'us_type': 'BOTH',
            'notes': 'Post-training survival test'
        }
    
    def get_time_str(self):
        dt = self.rtc.datetime()
        return f"{dt[0]}-{dt[1]:02d}-{dt[2]:02d} {dt[4]:02d}:{dt[5]:02d}"
    
    def set_datetime(self, year, month, day, hour, minute):
        self.rtc.datetime((year, month, day, 0, hour, minute, 0, 0))
        self.time_set = True
    
    def get_html(self):
        gc.collect()
        c = self.config
        s = self.stress_config
        ts = "SET" if self.time_set else "NOT SET"
        
        # Pre-compute selections to avoid complex f-string expressions
        ut_both = "selected" if c['us_type']=="BOTH" else ""
        ut_led = "selected" if c['us_type']=="LED" else ""
        ut_vib = "selected" if c['us_type']=="VIB" else ""
        sut_both = "selected" if s['us_type']=="BOTH" else ""
        sut_led = "selected" if s['us_type']=="LED" else ""
        sut_vib = "selected" if s['us_type']=="VIB" else ""
        start_dis = "disabled" if not self.time_set else ""
        
        return """<!DOCTYPE html><html><head><title>Incubator """ + self.device_id + """</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:sans-serif;background:#1a1a2e;color:#fff;padding:10px}
.c{max-width:400px;margin:0 auto}
h1{color:#0df;font-size:1.2em;text-align:center;margin:10px 0}
.card{background:#222;border-radius:8px;padding:12px;margin:8px 0}
label{display:block;color:#aaa;font-size:0.85em;margin:8px 0 3px}
input,select{width:100%;padding:8px;border:1px solid #444;border-radius:4px;background:#333;color:#fff;font-size:16px}
.row{display:flex;gap:8px}
.row>div{flex:1}
button{width:100%;padding:12px;border:none;border-radius:6px;font-size:1em;cursor:pointer;margin:5px 0}
.btn-blue{background:#0af;color:#000}
.btn-green{background:#0c6;color:#000;font-size:1.1em}
.btn-orange{background:#f80;color:#000;font-size:1.1em}
.btn-gray{background:#444;color:#fff}
.status{text-align:center;padding:8px;background:#333;border-radius:4px;margin:5px 0}
.tabs{display:flex;gap:5px;margin-bottom:10px}
.tab{flex:1;padding:10px;border:none;border-radius:6px 6px 0 0;cursor:pointer;font-weight:bold}
.tab-exp{background:#0c6;color:#000}
.tab-stress{background:#f80;color:#000}
.tab.inactive{opacity:0.5}
.panel{display:none}
.panel.active{display:block}
</style></head><body><div class="c">
<h1>Incubator """ + self.device_id + """</h1>
<div class="card">
<div class="status">Time: """ + ts + """ | Temp: <span id="t">--</span>C</div>
<form method="POST" action="/time">
<div class="row">
<div><label>Date</label><input type="date" name="d" id="d"></div>
<div><label>Time</label><input type="time" name="t" id="tm"></div>
</div>
<button type="button" class="btn-gray" onclick="n()">Use Phone Time</button>
<button type="submit" class="btn-blue">Set Time</button>
</form></div>
<div class="tabs">
<button type="button" class="tab tab-exp" id="tabExp" onclick="showPanel('exp')">Experiment</button>
<button type="button" class="tab tab-stress inactive" id="tabStress" onclick="showPanel('stress')">Stress Test</button>
</div>
<div id="panelExp" class="panel active">
<div class="card"><form method="POST" action="/cfg">
<label>Experiment Name</label>
<input type="text" name="n" value=\"""" + str(c['experiment_name']) + """\">
<label>Correlation (-1 to 1)</label>
<div class="row">
<div><input type="range" name="cs" min="-1" max="1" step="0.1" value=\"""" + str(c['correlation']) + """\" oninput="document.getElementById('cv').value=this.value"></div>
<div style="flex:0 0 60px"><input type="number" name="c" id="cv" value=\"""" + str(c['correlation']) + """\" step="0.1" min="-1" max="1"></div>
</div>
<div class="row">
<div><label>Basal C</label><input type="number" name="bt" value=\"""" + str(c['basal_temp']) + """\" step="0.5"></div>
<div><label>Heat C</label><input type="number" name="ht" value=\"""" + str(c['heat_shock_temp']) + """\" step="0.5"></div>
</div>
<div class="row">
<div><label>Min Int(m)</label><input type="number" name="mi" value=\"""" + str(c['min_interval']) + """\"></div>
<div><label>Max Int(m)</label><input type="number" name="mx" value=\"""" + str(c['max_interval']) + """\"></div>
</div>
<div class="row">
<div><label>US Dur(m)</label><input type="number" name="ud" value=\"""" + str(c['us_duration']) + """\"></div>
<div><label>Heat Dur(m)</label><input type="number" name="hd" value=\"""" + str(c['heat_duration']) + """\"></div>
</div>
<label>US Type</label>
<select name="ut">
<option value="BOTH" """ + ut_both + """>LED+Vib</option>
<option value="LED" """ + ut_led + """>LED</option>
<option value="VIB" """ + ut_vib + """>Vib</option>
</select>
<button type="submit" class="btn-blue">Save Config</button>
</form></div>
<form method="POST" action="/start">
<button type="submit" class="btn-green" """ + start_dis + """>START EXPERIMENT</button>
</form>
</div>
<div id="panelStress" class="panel">
<div class="card"><form method="POST" action="/scfg">
<label>Test Name</label>
<input type="text" name="sn" value=\"""" + str(s['experiment_name']) + """\">
<div class="row">
<div><label>Training C</label><input type="number" name="tt" value=\"""" + str(s['training_temp']) + """\" step="0.5"></div>
<div><label>Challenge C</label><input type="number" name="ct" value=\"""" + str(s['challenge_temp']) + """\" step="0.5"></div>
</div>
<div class="row">
<div><label>Training(m)</label><input type="number" name="td" value=\"""" + str(s['training_duration']) + """\"></div>
<div><label>Challenge(m)</label><input type="number" name="cd" value=\"""" + str(s['challenge_duration']) + """\"></div>
</div>
<div class="row">
<div><label>LED %</label><input type="number" name="li" value=\"""" + str(s['us_led_intensity']) + """\" min="0" max="100"></div>
<div><label>Vib %</label><input type="number" name="vi" value=\"""" + str(s['us_vib_intensity']) + """\" min="0" max="100"></div>
</div>
<label>US Type</label>
<select name="sut">
<option value="BOTH" """ + sut_both + """>LED+Vib</option>
<option value="LED" """ + sut_led + """>LED</option>
<option value="VIB" """ + sut_vib + """>Vib</option>
</select>
<label>Notes</label>
<input type="text" name="nt" value=\"""" + str(s['notes']) + """\">
<button type="submit" class="btn-blue">Save Config</button>
</form></div>
<form method="POST" action="/stress">
<button type="submit" class="btn-orange" """ + start_dis + """>START STRESS TEST</button>
</form>
</div>
</div>
<script>
function n(){var d=new Date();document.getElementById('d').value=d.toISOString().slice(0,10);document.getElementById('tm').value=d.toTimeString().slice(0,5)}
function showPanel(p){document.getElementById('panelExp').className=p=='exp'?'panel active':'panel';document.getElementById('panelStress').className=p=='stress'?'panel active':'panel';document.getElementById('tabExp').className=p=='exp'?'tab tab-exp':'tab tab-exp inactive';document.getElementById('tabStress').className=p=='stress'?'tab tab-stress':'tab tab-stress inactive'}
n();setInterval(function(){fetch('/t').then(r=>r.text()).then(d=>{document.getElementById('t').textContent=d}).catch(e=>{})},3000);
</script></body></html>"""
    
    def get_done_html(self, mode='experiment'):
        if mode == 'stress':
            s = self.stress_config
            return """<!DOCTYPE html><html><head><title>Started</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:sans-serif;background:#1a1a2e;color:#fff;text-align:center;padding:40px}</style>
</head><body><h1 style="color:#f80">Stress Test Started!</h1>
<p>""" + str(s['experiment_name']) + """</p><p>Training: """ + str(s['training_temp']) + """C for """ + str(s['training_duration']) + """m</p>
<p>Challenge: """ + str(s['challenge_temp']) + """C for """ + str(s['challenge_duration']) + """m</p>
<p style="color:#888;margin-top:30px">You can disconnect WiFi now.</p></body></html>"""
        else:
            return """<!DOCTYPE html><html><head><title>Started</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:sans-serif;background:#1a1a2e;color:#fff;text-align:center;padding:40px}</style>
</head><body><h1 style="color:#0c6">Started!</h1>
<p>""" + str(self.config['experiment_name']) + """</p><p>Corr: """ + str(self.config['correlation']) + """</p>
<p style="color:#888;margin-top:30px">You can disconnect WiFi now.</p></body></html>"""
    
    def parse_form(self, body):
        params = {}
        if body:
            for pair in body.split('&'):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    params[k.replace('%20',' ')] = v.replace('%20',' ').replace('%3A',':').replace('+',' ')
        return params
    
    def handle(self, req):
        try:
            lines = req.split('\n')
            if not lines:
                return "HTTP/1.1 400 Bad Request\r\n\r\n"
            
            parts = lines[0].strip().split(' ')
            if len(parts) < 2:
                return "HTTP/1.1 400 Bad Request\r\n\r\n"
            
            method, path = parts[0], parts[1]
            
            if path == '/t':
                try:
                    from max31865 import read_temperature
                    t = read_temperature()
                    return f"HTTP/1.1 200 OK\r\nContent-Type:text/plain\r\n\r\n{t:.1f}"
                except:
                    return "HTTP/1.1 200 OK\r\nContent-Type:text/plain\r\n\r\n--"
            
            if path == '/time' and method == 'POST':
                body = req.split('\r\n\r\n')[1] if '\r\n\r\n' in req else ""
                p = self.parse_form(body)
                try:
                    d = p.get('d', '').split('-')
                    t = p.get('t', '').split(':')
                    self.set_datetime(int(d[0]), int(d[1]), int(d[2]), int(t[0]), int(t[1]))
                except:
                    pass
                return "HTTP/1.1 302 Found\r\nLocation:/\r\n\r\n"
            
            if path == '/cfg' and method == 'POST':
                body = req.split('\r\n\r\n')[1] if '\r\n\r\n' in req else ""
                p = self.parse_form(body)
                if 'n' in p: self.config['experiment_name'] = p['n']
                if 'c' in p: self.config['correlation'] = max(-1, min(1, float(p['c'])))
                if 'bt' in p: self.config['basal_temp'] = float(p['bt'])
                if 'ht' in p: self.config['heat_shock_temp'] = float(p['ht'])
                if 'mi' in p: self.config['min_interval'] = int(p['mi'])
                if 'mx' in p: self.config['max_interval'] = int(p['mx'])
                if 'ud' in p: self.config['us_duration'] = int(p['ud'])
                if 'hd' in p: self.config['heat_duration'] = int(p['hd'])
                if 'ut' in p: self.config['us_type'] = p['ut']
                return "HTTP/1.1 302 Found\r\nLocation:/\r\n\r\n"
            
            if path == '/scfg' and method == 'POST':
                body = req.split('\r\n\r\n')[1] if '\r\n\r\n' in req else ""
                p = self.parse_form(body)
                if 'sn' in p: self.stress_config['experiment_name'] = p['sn']
                if 'tt' in p: self.stress_config['training_temp'] = float(p['tt'])
                if 'ct' in p: self.stress_config['challenge_temp'] = float(p['ct'])
                if 'td' in p: self.stress_config['training_duration'] = int(p['td'])
                if 'cd' in p: self.stress_config['challenge_duration'] = int(p['cd'])
                if 'li' in p: self.stress_config['us_led_intensity'] = int(p['li'])
                if 'vi' in p: self.stress_config['us_vib_intensity'] = int(p['vi'])
                if 'sut' in p: self.stress_config['us_type'] = p['sut']
                if 'nt' in p: self.stress_config['notes'] = p['nt']
                return "HTTP/1.1 302 Found\r\nLocation:/\r\n\r\n"
            
            if path == '/stress' and method == 'POST':
                if self.time_set:
                    self.stress_test_started = True
                    gc.collect()
                    html = self.get_done_html(mode='stress')
                    return f"HTTP/1.1 200 OK\r\nContent-Type:text/html\r\n\r\n{html}"
                return "HTTP/1.1 302 Found\r\nLocation:/\r\n\r\n"
            
            if path == '/start' and method == 'POST':
                if self.time_set:
                    self.experiment_started = True
                    gc.collect()
                    html = self.get_done_html()
                    return f"HTTP/1.1 200 OK\r\nContent-Type:text/html\r\n\r\n{html}"
                return "HTTP/1.1 302 Found\r\nLocation:/\r\n\r\n"
            
            # Default: show main page
            gc.collect()
            html = self.get_html()
            return f"HTTP/1.1 200 OK\r\nContent-Type:text/html\r\n\r\n{html}"
        
        except Exception as e:
            print(f"[Srv] Err: {e}")
            return "HTTP/1.1 500 Error\r\n\r\nError"
    
    def start_server(self, port=80):
        gc.collect()
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', port))
        self.socket.listen(2)
        self.socket.settimeout(1.0)
        print(f"[Server] Port {port} ready")
    
    def stop_server(self):
        if self.socket:
            try:
                self.socket.close()
                self.socket = None
            except:
                pass
    
    def serve_until_start(self):
        print("[Server] Waiting for config...")
        while not self.experiment_started and not self.stress_test_started:
            try:
                client, _ = self.socket.accept()
                client.settimeout(5.0)
                try:
                    req = client.recv(2048).decode('utf-8')
                    if req:
                        resp = self.handle(req)
                        client.send(resp.encode('utf-8'))
                except Exception as e:
                    print(f"[Srv] {e}")
                finally:
                    client.close()
                gc.collect()
            except OSError:
                pass
            except Exception as e:
                print(f"[Srv] {e}")
                time.sleep(0.1)
        
        time.sleep(1)
        if self.stress_test_started:
            cfg = self.stress_config.copy()
            cfg['mode'] = 'stress'
            return cfg
        cfg = self.config.copy()
        cfg['mode'] = 'experiment'
        return cfg
    
    def get_config(self):
        return self.config.copy()
    
    def get_stress_config(self):
        return self.stress_config.copy()
    
    def is_started(self):
        return self.experiment_started
    
    def is_stress_test_started(self):
        return self.stress_test_started
