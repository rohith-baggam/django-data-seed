from setuptools import setup, find_packages

setup(
    name='django-data-seed',
    version='0.4.2',
    packages=find_packages(),
    include_package_data=True,
    license='MIT License',
    description='A Django app to generate and seed database models with realistic test data using Faker. '
    'Includes features for automatic backup of deleted instances and detailed log entries for '
    'instance mutations, ensuring data safety and comprehensive change tracking.',
    long_description=open('README.rst').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/rohith-baggam/django-data-seed',
    author='Rohith Baggam',
    author_email='baggamrohithraj@gmail.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.0',
        'Framework :: Django :: 4.1',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.7',
    install_requires=[
        'colorama>=0.4.6',
        'Faker>=26.0.0',
    ],
    project_urls={
        'Bug Reports': 'https://github.com/rohith-baggam/django-data-seed/issues',
        'Source': 'https://github.com/rohith-baggam/django-data-seed',
    },
)
