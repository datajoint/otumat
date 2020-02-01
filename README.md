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
from pathlib import Path
from raphael_python_metadata import hash_pkg, verify

base_name = 'base'
plugin_name = 'plugin1'
base_meta = pkg_resources.get_distribution(base_name)
plugin_meta = pkg_resources.get_distribution(plugin_name)

data = hash_pkg(str(Path(plugin_meta.module_path, plugin_name)))
signature = plugin_meta.get_metadata('{}.sig'.format(plugin_name))
pubkey_path = str(Path(base_meta.egg_info, '{}.pub'.format(base_name)))

verify(pubkey_path, data, signature)
```