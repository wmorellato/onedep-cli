# from importlib.metadata import metadata

# print(metadata('requests'))

import pkgutil
import importlib.metadata

# Function to get the path of an installed package
def get_package_path(package_name):
    try:
        if importlib.util.find_spec(package_name):
            return importlib.util.find_spec(package_name).origin
        else:
            raise ImportError(f"Package '{package_name}' not found.")
    except Exception as e:
        return str(e)

# Replace 'package_name' with the name of the package you want to find
package_name = 'numpy'
package_path = get_package_path(package_name)

# Print the path for the given package
print(f"Path for package '{package_name}': {package_path}")
