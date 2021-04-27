# from typing import Union
# from json import loads

# MAC address

# from flask import Flask, request
from pathlib import Path
from json import load, dump
from os import makedirs
from flask import Flask, request
from appdirs import user_data_dir


class UsageAgent:
    """
    Local agent which buffers package usage data locally and periodically sends logged data to
    an OAuth2-compatible endpoint.
    """
    def __init__(self, author: str, package_name: str, host: str = None,
                 install_route: str = None, event_route: str = None):

        self.home_path = user_data_dir(package_name, author)  # ~/.local/share/datajoint-python
        if Path(self.home_path, 'config.json').is_file():
            # prior config exists, loading
            print('loading config from file!')
            self.config = load(open(Path(self.home_path, 'config.json'), 'r'))
            print(f'loaded: {self.config}')
        else:
            print('initializing flow!')
            # https://fakeservices.datajoint.io:2000, /user/usage-survey, /api/usage-event
            self.config = dict(host=host, install_route=install_route, event_route=event_route)
            self.install()
            self.save_config()

    def save_config(self):
        print(f'dumping: {self.config}')
        makedirs(self.home_path, exist_ok=True)
        with open(Path(self.home_path, 'config.json'), 'w') as f:
            dump(self.config, f, indent=4, sort_keys=True)

    def install(self):
        if input('Would you like to participate in our usage data collection to help us '
                 'improve our product, y/n? (y)\n').lower() == 'n':
            self.config['collect'] = False
        else:
            self.config['collect'] = True
            # allocate variables for access and context
            # access_token = None
            # refresh_token = None
            # expires_at = None
            # scope = None
            # install_id = None

            # app = Flask('survey-response')

            # @app.route("/health")
            # def health():
            #     return f'''
            #     <!doctype html><html><head><script>
            #         window.onload = function load() {{
            #         window.open('', '_self', '');
            #         var win = window.opener;
            #         win.postMessage(true, '*');
            #         window.close();
            #         }};
            #     </script></head><body></body></html>
            #     '''

            # @app.route("/install-complete")
            # def install_complete():
            #     def shutdown_server():
            #         func = request.environ.get('werkzeug.server.shutdown')
            #         if func is None:
            #             raise RuntimeError('Not running with the Werkzeug Server')
            #         func()

            #     nonlocal access_token
            #     nonlocal refresh_token
            #     nonlocal expires_at
            #     nonlocal scope
            #     nonlocal submission_id
            #     access_token = request.args.get('accessToken')
            #     refresh_token = request.args.get('refreshToken')
            #     expires_at = None if request.args.get('expiresIn') is None else datetime.utcnow().timestamp() + int(request.args.get('expiresIn'))
            #     scope = request.args.get('scope')
            #     submission_id = request.args.get('submissionId')
            #     shutdown_server()
            #     return '''
            #     <!doctype html><html><head><script>
            #         window.onload = function load() {
            #         window.open('', '_self', '');
            #         window.close();
            #         };
            #     </script></head><body></body></html>
            #     '''

    def log(self, event_type):
        pass

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
