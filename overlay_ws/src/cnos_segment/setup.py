from setuptools import find_packages, setup

package_name = 'cnos_segment'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/segment.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='abhishek',
    maintainer_email='deshmukhabhi02@gmail.com',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'segment_service = cnos_segment.segment_service:main',
        ],
    },
)
