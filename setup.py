from setuptools import setup, find_packages


if __name__ == '__main__':
    setup(
        name="bytepatches",
        author="martmists",
        author_email="mail@martmists.com",
        license="MIT",
        zip_safe=False,
        version="0.0.1",
        description="A high-level bytecode parser and modifier",
        long_description="TODO",
        url="https://github.com/martmists/bytepatches",
        packages=find_packages(),
        keywords=["Bytecode", "Python", "Patch"],
        classifiers=[
            "Development Status :: 2 - Pre-Alpha",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Topic :: Software Development :: Libraries :: Python Modules"
        ],
        python_requires=">=3.6")
