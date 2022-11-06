from setuptools import setup, find_namespace_packages # , find_packages

setup(
    name='clean_folder',
    version='1.0.0',
    description='Clean folder',
    url='http://github.com/madzvb/homework-7',
    author='Volodymyr Zawatsky',
    author_email='volodymyr.zawatsky@gmail.com',
    license='MIT',
    packages=find_namespace_packages(),
    #install_requires=['markdown'],
     entry_points={'console_scripts': ['clean = clean_folder.clean:main']}
)