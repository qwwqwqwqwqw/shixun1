from glob import glob
from setuptools import find_packages, setup

package_name = 'guide_pkg'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/srv', glob('srv/*.srv')),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
    ],
    install_requires=['setuptools', 'pyyaml'],
    zip_safe=True,
    maintainer='B组-导航核心',
    maintainer_email='teamB@icar.local',
    description='icar 教室导航核心包',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'guide_node = guide_pkg.guide_node:main',
            'arrival_fusion = guide_pkg.arrival_fusion:main',
            'joystick_ctrl = guide_pkg.joystick_ctrl:main',
        ],
    },
)
