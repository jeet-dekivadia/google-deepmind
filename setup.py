from setuptools import setup, find_packages
import os

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# Get version from __init__.py
def get_version():
    with open("halo/__init__.py", "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "0.1.0"

setup(
    name="halo-video",
    version=get_version(),
    author="Jeet Dekivadia",
    author_email="jeet.dekivadia@gmail.com",
    description="Hierarchical Abstraction for Longform Optimization - Optimizing Gemini API Usage for Long-Context Video Analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jeetdekivadia/halo",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Multimedia :: Video",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.0.0",
        ],
        "demo": [
            "jupyter>=1.0.0",
            "ipywidgets>=8.0.0",
            "matplotlib>=3.7.0",
            "seaborn>=0.12.0",
        ],
        "full": [
            "redis>=5.0.0",
            "google-generativeai>=0.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "halo=halo.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "halo": ["config/*.yaml", "models/*.pkl"],
    },
    keywords=[
        "video-analysis",
        "gemini-api",
        "long-form-content",
        "semantic-chunking",
        "caching",
        "machine-learning",
        "artificial-intelligence",
        "multimodal",
        "nlp",
        "computer-vision",
    ],
    project_urls={
        "Bug Reports": "https://github.com/jeetdekivadia/halo/issues",
        "Source": "https://github.com/jeetdekivadia/halo",
        "Documentation": "https://github.com/jeetdekivadia/halo#readme",
    },
) 