"""Library for package usage data management."""
import pathlib
import json
import os
import flask
import appdirs
import shutil
import datetime
import webbrowser
import logging
import multiprocessing
# client info
import re
import uuid
import sys
import platform
import subprocess
import pkg_resources
import contextlib
import socket
import urllib.parse
import time
# logging
import sqlite3
# sending
import urllib
import urllib.error
import base64
from . import DISABLE_USAGE_TRACKING_PACKAGES


class UsageAgent:
    """
    Local agent which buffers package usage data locally and periodically sends logged data to
    an OAuth2-compatible endpoint.
    """
    def __init__(self, *, author: str, data_directory: str, package_name: str,
                 host: str = None, install_route: str = None, event_route: str = None,
                 refresh_route: str = None, response_timeout: int = 60,
                 upload_frequency: str = '24h'):
        """
        Instantiates a package usage data tracking agent. If prior configuration exists, loads
        from file.

        :param author: Name of software author (for determining Windows data path)
        :type author: str
        :param data_directory: Name for package data directory
        :type data_directory: str
        :param package_name: Installed package name
        :type package_name: str
        :param host: Usage data tracking upload target
        :type host: str, optional if a configuration file already exists
        :param install_route: Route for new installations. Can be used for operations such as:
            registration, survey, consent, etc.
        :type install_route: str, optional if a configuration file already exists
        :param event_route: Route for ingesting user's cached logs
        :type event_route: str, optional if a configuration file already exists
        :param refresh_route: Route for renewing access and refresh tokens
        :type refresh_route: str, optional if a configuration file already exists
        :param response_timeout: Response timeout in seconds when installing usage agent,
            defaults to 60
        :type response_timeout: str, optional
        :param upload_frequency: Usage data upload interval for daemon, defaults to '24h'
        :type upload_frequency: str, optional
        """
        # verify `otumat` utility in PATH
        if package_name not in DISABLE_USAGE_TRACKING_PACKAGES:
            try:
                subprocess.Popen(['otumat', '-h'], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE).communicate()
            except FileNotFoundError:
                raise Exception("`otumat` console utility not available in current PATH. "
                                "Make sure that Python's bin and/or scripts directories are "
                                "properly added to the PATH. See here for more details: "
                                "https://stackoverflow.com/questions/49966547"
                                "/pip-10-0-1-warning-consider-adding-"
                                "this-directory-to-path-or") from None

        self.home_path = pathlib.Path(appdirs.user_data_dir(data_directory, author), 'usage')
        if pathlib.Path(self.home_path, 'config.json').is_file():
            # loading existing config
            self.config = json.loads(pathlib.Path(self.home_path, 'config.json').read_text())
        else:
            # initializing a new consent flow
            self.config = dict(author=author, data_directory=data_directory,
                               package_name=package_name, host=host,
                               install_route=install_route, event_route=event_route,
                               refresh_route=refresh_route, response_timeout=response_timeout,
                               upload_frequency=upload_frequency)
            self.install()

    def save_config(self):
        """
        Save usage agent's configuration to disk.
        """
        with open(pathlib.Path(self.home_path, 'config.json'), 'w') as f:
            json.dump(self.config, f, indent=4, sort_keys=True)

    def uninstall(self):
        """
        Remove configuration, logs, daemon, and active processes relating to usage agent.
        """
        _deactivate_startup(package_name=self.config['package_name'])
        if self.home_path.is_dir():
            shutil.rmtree(self.home_path)

    def install(self):
        """
        Primary installer for usage tracking data agent. Default behavior is to not collect
        usage data.
        """
        os.makedirs(self.home_path, exist_ok=True)
        if (self.config['package_name'] in DISABLE_USAGE_TRACKING_PACKAGES or
                not sys.stdin.isatty() or
                input("Would you like to participate in usage data collection to help the "
                      f"maintainers improve `{self.config['package_name']}`, y/n? (n)\n"
                      ).lower() != 'y'):
            print('User declined usage tracking. Saving selection.')
            self.config['collect'] = False
        else:
            # allocate variables for access and context
            access_token = None
            refresh_token = None
            expires_at = None
            scope = None
            install_id = None
            client_id = None
            client_secret = None
            cancelled = True
            # Prepare HTTP server to communicate with browser
            logging.getLogger('werkzeug').setLevel(logging.ERROR)
            app = flask.Flask('browser-interface')

            def shutdown_server():
                """
                Shuts down Flask HTTP server.
                """
                func = flask.request.environ.get('werkzeug.server.shutdown')
                if func is not None:
                    # Ensure running with the Werkzeug Server
                    func()

            @app.route("/health")
            def health():
                """
                Serves as a healthcheck to verify browser can communicate with Python process.
                """
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
                """
                Accepts requests which will cancel the usage tracking data agent installation.
                """
                shutdown_server()
                return '''
                <!doctype html><html><head><script>
                    window.onload = function load() {
                    window.open('', '_self', '');
                    window.close();
                    };
                </script></head><body></body></html>
                '''

            @app.route("/install-completed")
            def install_completed():
                """
                Accepts requests which will finish the usage tracking data agent installation.
                """
                nonlocal access_token
                nonlocal refresh_token
                nonlocal expires_at
                nonlocal scope
                nonlocal install_id
                nonlocal client_id
                nonlocal client_secret
                nonlocal cancelled
                cancelled = False
                access_token = flask.request.args.get('accessToken')
                refresh_token = flask.request.args.get('refreshToken')
                expires_at = (None if flask.request.args.get('expiresIn') is None
                              else (datetime.datetime.utcnow().timestamp() +
                                    int(flask.request.args.get('expiresIn'))))
                scope = flask.request.args.get('scope')
                install_id = flask.request.args.get('installId')
                client_id = flask.request.args.get('clientId')
                client_secret = flask.request.args.get('clientSecret')
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
            mac_address = ':'.join(re.findall('..', f'{uuid.getnode():012x}'))
            platform_name = 'Python'
            platform_version = '.'.join([str(v) for v in sys.version_info[:-2]])
            try:
                pkg_manager_version = subprocess.Popen(['conda', '--version'],
                                                       stdout=subprocess.PIPE,
                                                       stderr=subprocess.PIPE
                                                       ).communicate()[0].decode(
                                                        'utf-8').split()[1]
                pkg_manager = 'conda'
                _, package_version, package_build, pkg_manager_channel = subprocess.Popen(
                    ['conda', 'list', self.config['package_name']], stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE).communicate()[0].decode('utf-8').split(
                        '\n')[3].split()
            except FileNotFoundError:
                try:
                    pkg_manager_version = subprocess.Popen(['pip', '--version'],
                                                           stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE
                                                           ).communicate()[0].decode(
                                                            'utf-8').split()[1]
                except FileNotFoundError:
                    pkg_manager_version = subprocess.Popen(['pip3', '--version'],
                                                           stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE
                                                           ).communicate()[0].decode(
                                                            'utf-8').split()[1]
                pkg_manager = 'pip'
                package_version = pkg_resources.get_distribution(
                    self.config['package_name']).version
            # determine net IP
            with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            # determine available port
            with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                s.bind(('', 0))
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                unused_port = s.getsockname()[1]
            # determine location and timezone
            geo_data = json.load(urllib.request.urlopen('http://ipinfo.io/json'))
            location = ', '.join((geo_data['city'], geo_data['region'], geo_data['country']))
            timezone = ', '.join(list(time.tzname) + [geo_data['timezone']])
            # build url
            initiated_timestamp = round(datetime.datetime.utcnow().timestamp())
            query_params = dict(operatingSystem=sys.platform, macAddress=mac_address,
                                platform=platform_name, platformVersion=platform_version,
                                packageManager=pkg_manager,
                                packageManagerVersion=pkg_manager_version,
                                packageName=self.config['package_name'],
                                packageVersion=package_version, location=location,
                                timezone=timezone, timestamp=initiated_timestamp,
                                health=f'http://{local_ip}:{unused_port}/health',
                                redirect=f'http://{local_ip}:{unused_port}/install-completed',
                                cancel=f'http://{local_ip}:{unused_port}/install-cancelled')
            link = f"""{self.config['host']}{self.config['install_route']}?{
                urllib.parse.urlencode(query_params)}"""
            # attempt to launch browser or provide instructions
            browser_available = True
            try:
                webbrowser.get()
            except webbrowser.Error:
                browser_available = False
            if browser_available:
                print('Browser available. Launching usage tracking consent form using link: '
                      f'{link}')
                webbrowser.open(link, new=2)
            else:
                print('Brower unavailable. On a browser client in the same network as this '
                      'machine, please navigate to the following link to access the usage '
                      f'tracking consent form: {link}')
            # start response server
            cancel_process = multiprocessing.Process(
                target=_delayed_request,
                kwargs=dict(url=f'http://{local_ip}:{unused_port}/install-cancelled',
                            delay=self.config['response_timeout']))
            cancel_process.start()
            app.run(host='0.0.0.0', port=unused_port, debug=False)
            cancel_process.terminate()
            # received a response
            if cancelled:
                print('Cancelled usage tracking installation. Disabling any logging.')
                self.config['collect'] = False
            else:
                print('Thank you for providing consent. Creating `otumat` background startup '
                      'service to periodically upload usage data. Completing usage tracking '
                      'installation.')
                self.config = dict(self.config, collect=True, access_token=access_token,
                                   refresh_token=refresh_token, expires_at=expires_at,
                                   scope=scope, install_id=install_id, client_id=client_id,
                                   client_secret=client_secret,
                                   operating_system=sys.platform, mac_address=mac_address,
                                   platform=platform_name, platform_version=platform_version,
                                   package_manager=pkg_manager,
                                   package_manager_version=pkg_manager_version,
                                   package_version=package_version, location=location,
                                   timezone=timezone, timestamp=initiated_timestamp)
                # instantiating local cache
                with contextlib.closing(sqlite3.connect(
                        str(pathlib.Path(self.home_path, 'main.db')))) as conn:
                    with conn:
                        conn.execute("""
                        CREATE TABLE IF NOT EXISTS event(
                            event_date datetime(3),
                            event_type varchar(100)
                        )
                        """)
                # preparing command for usage data upload daemon
                cmd = ' '.join(['otumat', 'upload',
                                '-a', self.config['author'],
                                '-p', self.config['package_name'],
                                '-d', self.config['data_directory'],
                                '-s', datetime.datetime.utcnow().isoformat(),
                                '-f', self.config['upload_frequency']])
                # enabling usage data upload daemon at startup
                _activate_startup(cmd=cmd, package_name=self.config['package_name'])
                # manually starting usage data upload daemon
                if platform.system() == 'Windows':
                    p = subprocess.Popen(
                        [str(pathlib.Path(os.getenv('USERPROFILE'), 'AppData', 'Roaming',
                                          'Microsoft', 'Windows', 'Start Menu', 'Programs',
                                          'Startup',
                                          f"{self.config['package_name']}_usage.vbs"))],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                else:
                    os.system(f'{cmd} &>/dev/null &')
        self.save_config()

    def show_logs(self):
        """
        Shows current usage tracking logs in cache.

        :return: Rows of local, cached logs of user's package usage
        :rtype: list
        """
        if self.config['collect']:
            with contextlib.closing(sqlite3.connect(
                    str(pathlib.Path(self.home_path, 'main.db')))) as conn:
                with conn:
                    return [r for r in conn.execute('SELECT * FROM event')]

    def log(self, *, event_type: str):
        """
        Logs new events into the cache to be picked up by daemon.
        """
        if self.config['collect']:
            with contextlib.closing(sqlite3.connect(
                    str(pathlib.Path(self.home_path, 'main.db')))) as conn:
                with conn:
                    conn.execute('INSERT INTO event VALUES (?, ?)',
                                 (datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
                                  event_type))

    def send(self):
        """
        Unloads cached logs and uploads data to usage data tracking remote host.
        """
        if self.config['collect']:
            with contextlib.closing(sqlite3.connect(
                    str(pathlib.Path(self.home_path, 'main.db')))) as conn:
                with conn:
                    # always ensure refresh token is current
                    self.refresh_token()
                    # fetch cached data
                    current_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                    rows = [r for r in conn.execute('SELECT * FROM event WHERE event_date < ?',
                                                    (current_time,))]
                    if len(rows) == 0:
                        print('Nothing to send for this cycle.')
                    else:
                        # logs detected, build request to insert logs
                        body = dict(installId=self.config['install_id'],
                                    headers=['install_id', 'event_date', 'event_type'],
                                    rows=rows)
                        req = urllib.request.Request(
                            f"{self.config['host']}{self.config['event_route']}",
                            headers={'Content-Type': 'application/json',
                                     'Authorization': f"Bearer {self.config['access_token']}"},
                            data=json.dumps(body).encode('utf-8'))
                        try:
                            response = urllib.request.urlopen(req)
                        except urllib.error.HTTPError as e:
                            error_body = json.loads(e.read().decode())
                            if (e.code == 401 and isinstance(error_body, dict) and
                                    error_body['error_msg'] == 'Authorization Failed' and
                                    'TokenExpiredError' in error_body['error_desc']):
                                # access token expired, try again with a new refresh token
                                self.send()
                            else:
                                raise Exception('Unexpected server response...')
                        except urllib.error.URLError as e:
                            raise Exception('Connection refused when sending usage logs.')
                        else:
                            # insert successful, removing associated cached logs
                            conn.execute('DELETE FROM event WHERE event_date < ?',
                                         (current_time,))

    def refresh_token(self):
        """
        Token refresh utility.
        """
        if self.config['collect']:
            # build request to generate a new token
            req = urllib.request.Request(
                f"{self.config['host']}{self.config['refresh_route']}",
                headers={'Authorization': 'Basic {auth}'.format(
                    auth=base64.b64encode(
                        f"{self.config['client_id']}:{self.config['client_secret']}".encode(
                            'utf-8')).decode())},
                data=urllib.parse.urlencode(
                    dict(grant_type='refresh_token',
                         refresh_token=self.config['refresh_token'])).encode('utf-8'))
            try:
                response = urllib.request.urlopen(req)
            except urllib.error.HTTPError as e:
                # access denied b/c refresh token has now expired
                print('Usage upload connection has gone stale, requesting user to renew '
                      'token manually...')
                self.install()
            except urllib.error.URLError as e:
                raise Exception('Connection refused when requesting a new token.')
            else:
                # token returned successfully, update configuration
                body = json.load(response)
                self.config['access_token'] = body['access_token']
                self.config['expires_at'] = (datetime.datetime.utcnow().timestamp() +
                                             int(body['expires_in']))
                self.config['refresh_token'] = body['refresh_token']
                self.config['scope'] = body['scope']
                self.save_config()

    def recurring_send(self, *, start: datetime.datetime, frequency: str = '24h'):
        """
        Scheduler that uploads usage tracking data periodically.

        :param start: Datetime to start upload schedule, if in past will ignore
        :type start: datetime
        :param frequency: Interval which to upload logs, defaults to '24h'
        :type frequency: str, optional
        """
        # determine period in seconds
        period, unit = [int(e) if e.isdigit() else e
                        for e in re.findall(r'([0-9]+)([a-z]+)', frequency)[0]]
        if unit == 's':
            pass
        elif unit == 'm':
            period *= 60
        elif unit == 'h':
            period *= 60 * 60
        elif unit == 'd':
            period *= 24 * 60 * 60
        else:
            raise Exception(f'Unexpected unit `{unit}` specified.')
        # delay if start datetime has not happened yet
        if datetime.datetime.utcnow() < start:
            time.sleep([_[0].seconds + _[0].microseconds/1e6 - 1
                        for _ in zip([start - datetime.datetime.utcnow()])][0])
        # periodically unload cached usage data logs, checking config should user opt-out
        while json.loads(pathlib.Path(self.home_path, 'config.json').read_text())['collect']:
            time.sleep(period - datetime.datetime.utcnow().timestamp() % period)
            self.send()


def _delayed_request(*, url: str, delay: str = 0):
    time.sleep(delay)
    return urllib.request.urlopen(url)


def _activate_startup(*, cmd: str, package_name: str):
    """
    Utility that will register a daemon to run at startup.

    :param cmd: Shell command to run, space-delimited
    :type cmd: str
    :param package_name: Name of package to identify the daemon
    :type package_name: str
    """
    home_dir = os.getenv('USERPROFILE', os.getenv('HOME'))
    if platform.system() == 'Linux':
        # trigger startup by appending to user's profile script, Bourne shell compatible
        startup_file = pathlib.Path(home_dir, '.profile')
        with open(startup_file, 'a') as f:
            f.write(
                f'{cmd} &>/dev/null & export OTUMAT_PID=$! && trap "kill $OTUMAT_PID" EXIT\n')
    elif platform.system() == 'Darwin':
        # trigger startup using launchd by utiling launch agents
        startup_file = pathlib.Path(home_dir, 'Library', 'LaunchAgents',
                                    f'{package_name}_usage.startup.plist')
        os.makedirs(startup_file.parent, exist_ok=True)
        with open(startup_file, 'w') as f:
            f.write(f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC
                "-//Apple//DTD PLIST 1.0//EN"
                "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>EnvironmentVariables</key>
                <dict>
                    <key>PATH</key>
                    <string>{os.getenv('PATH')}</string>
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
    elif platform.system() == 'Windows':
        # trigger startup by utilizing user's startup directory and a VBScript to start a
        # background program
        startup_file = pathlib.Path(home_dir, 'AppData', 'Roaming', 'Microsoft', 'Windows',
                                    'Start Menu', 'Programs', 'Startup',
                                    f'{package_name}_usage.vbs')
        with open(startup_file, 'w') as f:
            f.write(f"""
            Dim WinScriptHost
            Set WinScriptHost = CreateObject("WScript.Shell")
            WinScriptHost.Run "{cmd}", 0
            Set WinScriptHost = Nothing
            """)


def _deactivate_startup(*, package_name: str):
    """
    Utility that will unregister a daemon from running at startup.

    :param package_name: Name of package to identify the daemon
    :type package_name: str
    """
    home_dir = os.getenv('USERPROFILE', os.getenv('HOME'))
    if platform.system() == 'Linux':
        # disable startup by removing daemon command from profile script
        # Bourne shell compatible
        startup_file = pathlib.Path(home_dir, '.profile')
        try:
            lines = pathlib.Path(startup_file).read_text().splitlines()
            with open(startup_file, 'w') as f:
                for line in lines:
                    if not all(t in line for t in ('otumat upload ', f' -p {package_name} ')):
                        f.write(f'{line}\n')
        except FileNotFoundError:
            pass
    elif platform.system() == 'Darwin':
        # disable startup by removing property list file spec for the launch agent
        startup_file = pathlib.Path(home_dir, 'Library', 'LaunchAgents',
                                    f'{package_name}_usage.startup.plist')
        try:
            startup_file.unlink()
        except FileNotFoundError:
            pass
    elif platform.system() == 'Windows':
        # disable startup by removing the user's startup VBScript
        startup_file = pathlib.Path(home_dir, 'AppData', 'Roaming', 'Microsoft', 'Windows',
                                    'Start Menu', 'Programs', 'Startup',
                                    f'{package_name}_usage.vbs')
        try:
            startup_file.unlink()
        except FileNotFoundError:
            pass
