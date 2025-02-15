from distutils.core import setup

setup(
    name='Blackjack',
    version='2.0',
    description='Blackjack with surrrender CLI interactive game and simulator.',
    author='Ellis Andrews',
    packages=['blackjack'],
    install_requires=['matplotlib', 'pandas', 'tqdm']
)
