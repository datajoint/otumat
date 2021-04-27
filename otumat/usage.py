# from typing import Union
# from json import loads

# MAC address

from pathlib import Path
from json import load, dump
from os import makedirs
from flask import Flask, request
from appdirs import user_data_dir
from shutil import rmtree
from datetime import datetime
import webbrowser
from logging import getLogger, ERROR as log_error
# specs
from re import findall
from uuid import getnode
from sys import version_info, platform as operating_system
from subprocess import Popen, PIPE
from pkg_resources import get_distribution
from contextlib import closing
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from urllib.request import urlopen
from urllib.parse import urlencode
from time import tzname
# logging
from sqlite3 import connect

INSTALL_WINDOW = 1 * 60  # seconds


class UsageAgent:
    """
    Local agent which buffers package usage data locally and periodically sends logged data to
    an OAuth2-compatible endpoint.
    """
    def __init__(self, author: str, data_directory: str, package_name: str, host: str = None,
                 install_route: str = None, event_route: str = None):

        # ~/.local/share/datajoint-python/usage
        self.home_path = Path(user_data_dir(data_directory, author), 'usage')
        if Path(self.home_path, 'config.json').is_file():
            # prior config exists, loading
            print('loading config from file!')
            self.config = load(open(Path(self.home_path, 'config.json'), 'r'))
        else:
            print('initializing flow!')
            # https://fakeservices.datajoint.io:2000, /user/usage-survey, /api/usage-event
            self.config = dict(package_name=package_name, host=host,
                               install_route=install_route, event_route=event_route)
            self.install()
            self.save_config()

    def save_config(self):
        with open(Path(self.home_path, 'config.json'), 'w') as f:
            dump(self.config, f, indent=4, sort_keys=True)

    def uninstall(self):
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
            # Temporary HTTP server to communicate with browser
            getLogger('werkzeug').setLevel(log_error)
            app = Flask('browser-interface')

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

            @app.route("/install-complete")
            def install_complete():
                def shutdown_server():
                    func = request.environ.get('werkzeug.server.shutdown')
                    if func is None:
                        raise RuntimeError('Not running with the Werkzeug Server')
                    func()

                nonlocal access_token
                nonlocal refresh_token
                nonlocal expires_at
                nonlocal scope
                nonlocal install_id
                access_token = request.args.get('accessToken')
                refresh_token = request.args.get('refreshToken')
                expires_at = (None if request.args.get('expiresIn') is None
                              else (datetime.utcnow().timestamp() +
                                    int(request.args.get('expiresIn'))))
                scope = request.args.get('scope')
                install_id = request.args.get('installId')
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
                pkg_manager_version = Popen(['pip', '--version'], stdout=PIPE,
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
                                redirect=f'http://{local_ip}:{unused_port}/install-complete')
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
            app.run(host='0.0.0.0', port=unused_port, debug=False)  # verify if localhost works

            print('Completing installation.')
            self.config = dict(self.config, collect=True, access_token=access_token,
                               refresh_token=refresh_token, expires_at=expires_at, scope=scope,
                               install_id=install_id, operating_system=operating_system,
                               mac_address=mac_address, platform=platform,
                               platform_version=platform_version, package_manager=pkg_manager,
                               package_manager_version=pkg_manager_version,
                               package_version=package_version, location=location,
                               timezone=timezone, timestamp=initiated_timestamp)
            makedirs(self.home_path, exist_ok=True)
            with closing(connect(Path(self.home_path, 'main.db'))) as conn:
                with conn:
                    conn.execute('CREATE TABLE event (event_date datetime(3), event_type)')

    def show_logs(self):
        with closing(connect(Path(self.home_path, 'main.db'))) as conn:
            with conn:
                return [r for r in conn.execute('SELECT * FROM event')]

    def log(self, event_type):
        with closing(connect(Path(self.home_path, 'main.db'))) as conn:
            with conn:
                conn.execute('INSERT INTO event VALUES (?, ?)',
                             (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'), event_type))

    def send(self):
        pass

    def refresh_token(self):
        pass

    def schedule(self, frequency='1m'):  # 0-inf / s | m | h | d
        pass

    def activate_startup(self):
        pass

    def deactivate_startup(self):
        pass


# log

# send

# schedule (attached, detatched)

# activate startup

# deactive startup

# refresh token

# install_agent





        # self.installation_id = source['installation_id']



        # self.access_token = source['access_token']
        # self.refresh_token = source['refresh_token']
        # self.expires_on = source['expires_on']
        # self.scope = source['scope']



        # self.config = (loads(open(source, 'r').readlines())
        #                if (isinstance(source, str) and (file exists))
        #                else {k: v for k, v in source if k != 'config_path'})
        # self.config_path = (source
        #                if (isinstance(source, str) and (file exists))
        #                else {k: v for k, v in source if k != 'config_path'})

        # if isinstance(source, str):
        #     # load from file
        #     # assert file exists
        #     pass
        # else:
        #     # initialize the agent
        #     self.config = dict(collect=True, access_token=None, refresh_token=None,
        #                        expires_on=None, scope=None, installation_id=None)
