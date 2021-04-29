# from typing import Union
# from json import loads

# MAC address

from pathlib import Path
from json import load, dump, dumps, loads
from os import makedirs, getenv, system
from flask import Flask, request
from appdirs import user_data_dir
from shutil import rmtree
from datetime import datetime
import webbrowser
from logging import getLogger, ERROR as log_error
from threading import Thread
# specs
from re import findall
from uuid import getnode
from sys import version_info, platform as operating_system
from platform import system as general_system
from subprocess import Popen, PIPE, DEVNULL
from pkg_resources import get_distribution
from contextlib import closing
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from urllib.request import urlopen
from urllib.parse import urlencode
from time import tzname
# logging
from sqlite3 import connect
# sending
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from base64 import b64encode
from time import sleep

INSTALL_WINDOW = 1 * 60  # seconds


class UsageAgent:
    """
    Local agent which buffers package usage data locally and periodically sends logged data to
    an OAuth2-compatible endpoint.
    """
    def __init__(self, author: str, data_directory: str, package_name: str, host: str = None,
                 install_route: str = None, event_route: str = None, refresh_route: str = None,
                 response_timeout: int = 60, upload_frequency: str = '24h'):

        # ~/.local/share/datajoint-python/usage  # linux
        # %USERPROFILE%\AppData\Local\DataJoint\datajoint-python\usage  # windows
        # ~/Library/Application Support/datajoint-python\usage  # macos
        self.home_path = Path(user_data_dir(data_directory, author), 'usage')
        if Path(self.home_path, 'config.json').is_file():
            # prior config exists, loading
            print('loading config from file!')
            self.config = load(open(Path(self.home_path, 'config.json'), 'r'))
        else:
            print('initializing flow!')
            # https://fakeservices.datajoint.io:2000, /user/usage-survey, /api/usage-event
            self.config = dict(author=author, data_directory=data_directory,
                               package_name=package_name, host=host,
                               install_route=install_route, event_route=event_route,
                               refresh_route=refresh_route, response_timeout=response_timeout,
                               upload_frequency=upload_frequency)
            self.install()

    def save_config(self):
        with open(Path(self.home_path, 'config.json'), 'w') as f:
            dump(self.config, f, indent=4, sort_keys=True)

    def uninstall(self):
        _deactivate_startup(self.config['package_name'])
        if self.home_path.is_dir():
            rmtree(self.home_path)

    def install(self):
        if input('Would you like to participate in our usage data collection to help us '
                 'improve our product, y/n? (y)\n').lower() == 'n':
            self.config['collect'] = False
        else:
            # # allocate variables for access and context
            access_token = None
            refresh_token = None
            expires_at = None
            scope = None
            install_id = None
            client_id = None
            client_secret = None
            cancelled = True
            # Temporary HTTP server to communicate with browser
            getLogger('werkzeug').setLevel(log_error)
            app = Flask('browser-interface')

            def shutdown_server():
                func = request.environ.get('werkzeug.server.shutdown')
                if func is not None:
                    # Ensure running with the Werkzeug Server
                    func()

            @app.route("/health")
            def health():
                return '''
                <!doctype html><html><head><script>
                    window.onload = function load() {
                    window.open('', '_self', '');
                    var win = window.opener;
                    win.postMessage(true, '*');
                    window.close();
                    };
                </script></head><body></body></html>
                '''

            @app.route("/install-cancelled")
            def install_cancelled():
                shutdown_server()
                return '''
                <!doctype html><html><head><script>
                    window.onload = function load() {
                    window.open('', '_self', '');
                    var win = window.opener;
                    win.postMessage(true, '*');
                    window.close();
                    };
                </script></head><body></body></html>
                '''

            @app.route("/install-completed")
            def install_completed():
                nonlocal access_token
                nonlocal refresh_token
                nonlocal expires_at
                nonlocal scope
                nonlocal install_id
                nonlocal client_id
                nonlocal client_secret
                nonlocal cancelled
                cancelled = False
                access_token = request.args.get('accessToken')
                refresh_token = request.args.get('refreshToken')
                expires_at = (None if request.args.get('expiresIn') is None
                              else (datetime.utcnow().timestamp() +
                                    int(request.args.get('expiresIn'))))
                scope = request.args.get('scope')
                install_id = request.args.get('installId')
                client_id = request.args.get('clientId')
                client_secret = request.args.get('clientSecret')
                shutdown_server()
                return '''
                <!doctype html><html><head><script>
                    window.onload = function load() {
                    window.open('', '_self', '');
                    window.close();
                    };
                </script></head><body></body></html>
                '''

            # platform details
            mac_address = ':'.join(findall('..', f'{getnode():012x}'))
            platform = 'Python'
            platform_version = '.'.join([str(v) for v in version_info[:-2]])
            try:
                pkg_manager_version = Popen(['conda', '--version'], stdout=PIPE,
                                            stderr=PIPE).communicate()[0].decode(
                                                'utf-8').split()[1]
                pkg_manager = 'conda'
                _, package_version, package_build, pkg_manager_channel = Popen(
                    ['conda', 'list', self.config['package_name']], stdout=PIPE,
                    stderr=PIPE).communicate()[0].decode('utf-8').split('\n')[3].split()
            except FileNotFoundError:
                try:
                    pkg_manager_version = Popen(['pip', '--version'], stdout=PIPE,
                                                stderr=PIPE).communicate()[0].decode(
                                                    'utf-8').split()[1]
                except FileNotFoundError:
                    pkg_manager_version = Popen(['pip3', '--version'], stdout=PIPE,
                                                stderr=PIPE).communicate()[0].decode(
                                                    'utf-8').split()[1]
                pkg_manager = 'pip'
                package_version = get_distribution(self.config['package_name']).version
            # determine IP
            with closing(socket(AF_INET, SOCK_DGRAM)) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            # determine port
            with closing(socket(AF_INET, SOCK_STREAM)) as s:
                s.bind(('', 0))
                s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                unused_port = s.getsockname()[1]
            # location
            geo_data = load(urlopen('http://ipinfo.io/json'))
            location = ', '.join((geo_data['city'], geo_data['region'], geo_data['country']))
            timezone = ', '.join(list(tzname) + [geo_data['timezone']])
            # make the link
            initiated_timestamp = round(datetime.utcnow().timestamp())
            query_params = dict(operatingSystem=operating_system, macAddress=mac_address,
                                platform=platform, platformVersion=platform_version,
                                packageManager=pkg_manager,
                                packageManagerVersion=pkg_manager_version,
                                packageName=self.config['package_name'],
                                packageVersion=package_version, location=location,
                                timezone=timezone, timestamp=initiated_timestamp,
                                health=f'http://{local_ip}:{unused_port}/health',
                                redirect=f'http://{local_ip}:{unused_port}/install-completed')
            link = f"""{self.config['host']}{self.config['install_route']}?{
                urlencode(query_params)}"""
            # instruct on browser access
            browser_available = True
            try:
                webbrowser.get()
            except webbrowser.Error:
                browser_available = False
            if browser_available:
                print(f'Browser available. Launching the survey. Link: {link}')
                webbrowser.open(link, new=2)
            else:
                print(f'Brower unavailable. On a browser client on the same network as this machine, please navigate to the following URL to access the survey: {link}')

            # start response server
            print(f'Starting response server listening on: http://{local_ip}:{unused_port}/health')
            #app.run(host='0.0.0.0', port=3000, ssl_context=('/tmp/certs/fullchain.pem',
            #                                                '/tmp/certs/privkey.pem'))
            #app.run(host='0.0.0.0', port=3000, ssl_context='adhoc')
            print(f"now: {datetime.now()}, timeout: {self.config['response_timeout']}, cancel route: http://{local_ip}:{unused_port}/install-cancelled")
            Thread(
                target=lambda url, d: None if sleep(d) else urllib_request.urlopen(url),
                args=(f'http://{local_ip}:{unused_port}/install-cancelled',
                      self.config['response_timeout']),
                daemon=True).start()
            app.run(host='0.0.0.0', port=unused_port, debug=False)

            makedirs(self.home_path, exist_ok=True)
            if cancelled:
                print('Cancelled installation.')
                self.config['collect'] = False
            else:
                print('Completing installation.')
                self.config = dict(self.config, collect=True, access_token=access_token,
                                   refresh_token=refresh_token, expires_at=expires_at, scope=scope,
                                   install_id=install_id, client_id=client_id,
                                   client_secret=client_secret, operating_system=operating_system,
                                   mac_address=mac_address, platform=platform,
                                   platform_version=platform_version, package_manager=pkg_manager,
                                   package_manager_version=pkg_manager_version,
                                   package_version=package_version, location=location,
                                   timezone=timezone, timestamp=initiated_timestamp)
                with closing(connect(str(Path(self.home_path, 'main.db')))) as conn:
                    with conn:
                        conn.execute("""
                        CREATE TABLE IF NOT EXISTS event(
                            event_date datetime(3),
                            event_type varchar(100)
                        )
                        """)
                cmd = f"""otumat upload -a {self.config['author']} -p {
                    self.config['package_name']} -d {self.config['data_directory']} -s {
                        datetime.utcnow().isoformat()} -f {self.config['upload_frequency']}"""
                _activate_startup(cmd, self.config['package_name'])
                if general_system() == 'Windows':
                    p = Popen([str(Path(getenv('USERPROFILE'), 'AppData', 'Roaming', 'Microsoft',
                                        'Windows', 'Start Menu', 'Programs', 'Startup',
                                        f"{self.config['package_name']}_usage.vbs"))],
                              stdout=DEVNULL, stderr=DEVNULL, shell=True)
                else:
                    system(f'{cmd} &>/dev/null &')
        self.save_config()

    def show_logs(self):
        if self.config['collect']:
            with closing(connect(str(Path(self.home_path, 'main.db')))) as conn:
                with conn:
                    return [r for r in conn.execute('SELECT * FROM event')]

    def log(self, event_type):
        if self.config['collect']:
            with closing(connect(str(Path(self.home_path, 'main.db')))) as conn:
                with conn:
                    conn.execute('INSERT INTO event VALUES (?, ?)',
                                 (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), event_type))

    def send(self):
        if self.config['collect']:
            with closing(connect(str(Path(self.home_path, 'main.db')))) as conn:
                with conn:
                    self.refresh_token()
                    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                    rows = [r for r in conn.execute('SELECT * FROM event WHERE event_date < ?',
                                                    (current_time,))]
                    if len(rows) == 0:
                        print('no new logs...')
                    else:
                        body = dict(installId=self.config['install_id'],
                                    headers=['install_id', 'event_date', 'event_type'], rows=rows)
                        req = urllib_request.Request(
                            f"{self.config['host']}{self.config['event_route']}",
                            headers={'Content-Type': 'application/json',
                                     'Authorization': f"Bearer {self.config['access_token']}"},
                            data=dumps(body).encode('utf-8'))
                        try:
                            response = urllib_request.urlopen(req)
                            print(response.code)
                            print(response.read())
                        except HTTPError as e:
                            error_body = loads(e.read().decode())
                            if (e.code == 401 and isinstance(error_body, dict) and
                                    error_body['error_msg'] == 'Authorization Failed' and
                                    'TokenExpiredError' in error_body['error_desc']):
                                self.send()
                            else:
                                print(e.code)
                                print(error_body)
                                assert False, 'Unexpected...'
                        except URLError as e:
                            assert False, 'Connection refused...'
                        else:
                            conn.execute('DELETE FROM event WHERE event_date < ?', (current_time,))

    def refresh_token(self):
        if self.config['collect']:
            print('refreshing token!')
            req = urllib_request.Request(
                f"{self.config['host']}{self.config['refresh_route']}",
                headers={'Authorization': f"""Basic {b64encode(f'''{self.config['client_id']}:{
                    self.config['client_secret']}'''.encode('utf-8')).decode()}"""},
                data=urlencode(
                    dict(grant_type='refresh_token',
                         refresh_token=self.config['refresh_token'])).encode('utf-8'))
            try:
                response = urllib_request.urlopen(req)
            except HTTPError as e:
                print(e.code)
                print(e.read().decode())
                print('Usage upload connection stale, requesting to renew permission...')
                self.install()
            except URLError as e:
                assert False, 'Connection refused...'
            else:
                body = loads(response.read())
                print(response.code)
                print(f"{self.config['refresh_token']} -> {body['refresh_token']}")
                t = datetime.utcnow().timestamp() + int(body['expires_in'])
                print(f"{self.config['expires_at']} -> {t}")
                self.config['access_token'] = body['access_token']
                self.config['expires_at'] = t
                self.config['refresh_token'] = body['refresh_token']
                self.config['scope'] = body['scope']
                self.save_config()

    def recurring_send(self, start: datetime, frequency='1m'):  # 0-inf / s | m | h | d
        if self.config['collect']:
            period, unit = [int(e) if e.isdigit() else e
                            for e in findall(r'([0-9]+)([a-z]+)', frequency)[0]]
            if unit == 'm':
                period *= 60
            elif unit == 'h':
                period *= 60 * 60
            elif unit == 'd':
                period *= 24 * 60 * 60
            if datetime.utcnow() < start:
                sleep([_[0].seconds + _[0].microseconds/1e6 - 1
                       for _ in zip([start - datetime.utcnow()])][0])
            while True:
                sleep(period - datetime.utcnow().timestamp() % period)
                self.send()


def _activate_startup(cmd, package_name):
    home_dir = getenv('USERPROFILE', getenv('HOME'))
    if general_system() == 'Linux':
        # Bourne shell compatible
        with open(Path(home_dir, '.profile'), 'a') as f:
            f.write(f'{cmd} &>/dev/null &\n')
    elif general_system() == 'Darwin':
        makedirs(Path(home_dir, 'Library', 'LaunchAgents'), exist_ok=True)
        with open(Path(home_dir, 'Library', 'LaunchAgents',
                  f'{package_name}_usage.startup.plist'), 'w') as f:
            f.write(f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>EnvironmentVariables</key>
                <dict>
                    <key>PATH</key>
                    <string>{getenv('PATH')}</string>
                </dict>
                <key>Label</key>
                <string>{package_name}_usage.startup</string>
                <key>RunAtLoad</key>
                <true/>
                <key>ProgramArguments</key>
                <array>
                    {''.join([f'<string>{t}</string>' for t in ('bash', '-c', cmd)])}
                </array>
            </dict>
            </plist>
            """)
    elif general_system() == 'Windows':
        with open(Path(home_dir, 'AppData', 'Roaming', 'Microsoft', 'Windows', 'Start Menu',
                       'Programs', 'Startup', f'{package_name}_usage.vbs'), 'w') as f:
            f.write(f"""
            Dim WinScriptHost
            Set WinScriptHost = CreateObject("WScript.Shell")
            WinScriptHost.Run "{cmd}", 0
            Set WinScriptHost = Nothing
            """)


def _deactivate_startup(package_name):
    home_dir = getenv('USERPROFILE', getenv('HOME'))
    if general_system() == 'Linux':
        startup_file = Path(home_dir, '.profile')
        # Bourne shell compatible
        if startup_file.exists():
            lines = open(startup_file, 'r').readlines()
            with open(startup_file, 'w') as f:
                [f.write(line) for line in lines if ('otumat' not in line and
                                                     'upload' not in line and
                                                     package_name not in line)]
    elif general_system() == 'Darwin':
        startup_file = Path(home_dir, 'Library', 'LaunchAgents',
                            f'{package_name}_usage.startup.plist')
        if startup_file.exists():
            startup_file.unlink()
    elif general_system() == 'Windows':
        startup_file = Path(home_dir, 'AppData', 'Roaming', 'Microsoft', 'Windows',
                            'Start Menu', 'Programs', 'Startup', f'{package_name}_usage.vbs')
        if startup_file.exists():
            startup_file.unlink()


# log

# send

# schedule (attached, detatched)

# activate startup

# deactive startup

# refresh token

# install_agent





#         self.installation_id = source['installation_id']



#         self.access_token = source['access_token']
#         self.refresh_token = source['refresh_token']
#         self.expires_on = source['expires_on']
#         self.scope = source['scope']



#         self.config = (loads(open(source, 'r').readlines())
#                        if (isinstance(source, str) and (file exists))
#                        else {k: v for k, v in source if k != 'config_path'})
#         self.config_path = (source
#                        if (isinstance(source, str) and (file exists))
#                        else {k: v for k, v in source if k != 'config_path'})

#         if isinstance(source, str):
#             # load from file
#             # assert file exists
#             pass
#         else:
#             # initialize the agent
#             self.config = dict(collect=True, access_token=None, refresh_token=None,
#                                expires_on=None, scope=None, installation_id=None)
