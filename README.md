# Setuptools Certificate Metadata

This is a setuptools extension that provides a new keyword argument `privkey_path`. By specifying it, setuptools will generate the git hash (SHA1) of the module directory and sign the output based on the PEM key path passed in. The resulting signature will be stored as egg metadata `{{module_name}}.sig` accessible via `pkg_resources` module. This provides a solution to determining the 'trust-worthiness' of plugins or extensions that may developed by the community for a given pip package if the public key file is available for the RSA keypair.

# Use

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

pkg = pkg_resources.get_distribution({{pip_module}}.__name__)

pubkey_path = '~/keys/pubkey.pem'
data = hash_pkg({{pip_module}}.__path__[0])
signature = pkg.get_metadata('{}.sig'.format({{pip_module}}.__name__))

verify(pubkey_path, data, signature)
```