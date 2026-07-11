from glob import glob
from setuptools import find_packages, setup

package_name = 'aiserver_pkg'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
    ],
    install_requires=['setuptools', 'websockets'],
    zip_safe=True,
    maintainer='D组-接口与前端',
    maintainer_email='teamD@icar.local',
    description='指令接口包',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'aiserver_node = aiserver_pkg.aiserver_node:main',
        ],
    },
)
