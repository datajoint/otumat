# Setuptools Certificate Metadata

This is a setuptools extension that provides new keyword arguments `privkey_path` and `pubkey_path`. 

By specifying the `privkey_path`, setuptools will generate the git hash (SHA1) of the module directory and sign the output based on the PEM key path passed in. The resulting signature will be stored as egg metadata `{{module_name}}.sig` accessible via `pkg_resources` module. 

If passing `pubkey_path`, this will simply be copied in as egg metadata `{{module_name}}.pub`. 

This provides a solution to determining the 'trust-worthiness' of plugins or extensions that may be developed by the community for a given pip package if the public key file is available for the RSA keypair. The choice of what to do for failed verification is up to you.

# Use

## Extensible Package e.g. `base`

``` python
setuptools.setup(
    ...
    setup_requires=['raphael_python_metadata'],
    pubkey_path='~/keys/pubkey.pem',
    ...
```

## Plugin Package e.g. `plugin1`

``` python
setuptools.setup(
    ...
    setup_requires=['raphael_python_metadata'],
    privkey_path='~/keys/privkey.pem',
    ...
```

 # Verifying Contents

``` python
import pkg_resources
from raphael_python_metadata import hash_pkg, verify

base = 'base'
plugin = 'plugin1'
base_module = __import__(base)
plugin_module = __import__(plugin)
base_meta = pkg_resources.get_distribution(base_module.__name__)
plugin_meta = pkg_resources.get_distribution(plugin_module.__name__)

pubkey_path = base_meta.get_metadata('{}.pub'.format(base_meta.__name__))
data = hash_pkg(plugin_module.__path__[0])
signature = plugin_meta.get_metadata('{}.sig'.format(plugin_module.__name__))

verify(pubkey_path, data, signature)
```