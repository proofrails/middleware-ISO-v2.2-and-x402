from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="iso-middleware-sdk",
    version="0.1.0",
    author="ISO Middleware Team",
    author_email="",
    description="Python SDK for ISO 20022 Middleware Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alfre97x/Middleware-ISO-20022-v2.2",
    project_urls={
        "Bug Tracker": "https://github.com/alfre97x/Middleware-ISO-20022-v2.2/issues",
        "Documentation": "https://github.com/alfre97x/Middleware-ISO-20022-v2.2#readme",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.11",
    install_requires=[
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "black", "ruff"],
    },
    keywords="iso20022 payments middleware flare blockchain verifiable-credentials",
)
