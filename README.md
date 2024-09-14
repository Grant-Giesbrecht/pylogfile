<h1 align="center">
<img src="https://github.com/Grant-Giesbrecht/pylogfile/blob/main/docs/images/pylogfile_logo_banner.svg?raw=True" width="300">
</h1><br>

Pylogfile provides a better method for implementing logging in your Python scripts.

- **PyPI:** https://pypi.org/project/pylogfile/
- **Documentation:** https://pylogfile.readthedocs.io/en/latest/
- **Source Code:** [https://github.com/](https://github.com/Grant-Giesbrecht/pylogfile/)

Core features:

- automatically includes metadata such as timestamps.
- supports optional detail strings to supplement the main log message.
- integrated markdown makes it easy to highlight parts of log messages with color.
- easily read and write logs to binary files for better efficiency, or JSON and TXT for best readability.
- standardized format makes it easy to read previous log files, simplifying sorting and analysis.
- script `lumberjack` makes viewing, sorting and analyzing log files quick and easy.

Pylogfile is designed to be a better option than the Python standard logging module for simple to intermediate-complexity logging tasks. For professional applications in which you want to add custom logging handlers, the standard module is the better choice. However, for the majority of scripts, especially in the scientific, engineering and data analysis domains, pylogfile offers loads of capability and a much faster way of setting up proper logging than the standard module. With pylogfile, your application has access to efficient data management and display through the addition of detailed messages, integrated markdown, and log search functions through the `lumberjack` script.

## Installation

Pylogfile can be installed via pip using

```
pip install pylogfile
```

## Example usage

In this example, we create a simple program that sends two log messages and saves them to disk. Here we show how to save to both binary and plain text formats. The [HDF](https://www.hdfgroup.org/) file format is binary, allowing logs to be saved faster and while using less space on disk. We also show how to save to a JSON file, for those who prefer the simplicity of plain text files.

```python
from pylogfile.base import *

log = LogPile()
log.info("Something happened. Emphasize >this<.")
log.error("Something bad happened!")

log.save_hdf("example.log.hdf")
log.save_json("example.log.json")
```

With the corresponding output:

<img src="https://github.com/Grant-Giesbrecht/pylogfile/blob/main/docs/images/ex1_output.png?raw=True" width="600">

## Lumberjack

Lumberjack is a command line interface (CLI) script included with pylogfile that allows log files to quickly be viewed, sorted, and analyzed. A log file can be opened in lumberjack with:

```
lumber example.log.hdf
```

and the first few logs displayed with the `SHOW` command:

<img src="https://github.com/Grant-Giesbrecht/pylogfile/blob/main/docs/images/lumber_out1.png?raw=True" width="600">

Basic information about the log file can be displayed with the `INFO` command.

<img src="https://github.com/Grant-Giesbrecht/pylogfile/blob/main/docs/images/lumber_out2.png?raw=True" width="320">

Logs can also be sorted by applying flags to the `SHOW` command. Here the `--index` flag is used to search based on the index of the log entry, the `--contains` flag is used to search for the keyword or phrase 'RF' while specifying a max of 5 logs should be displayed using the `--num` flag, and the log level is filter by applying the `--min` and `--max` flags.

<img src="https://github.com/Grant-Giesbrecht/pylogfile/blob/main/docs/images/lumber_out3.png?raw=True" width="600">

Lumberjack has lots of other search functions, commands, and features. You can learn more about it from its integrated help menu which can list all available commands and provide detailed information on how to use them.

<img src="https://github.com/Grant-Giesbrecht/pylogfile/blob/main/docs/images/lumber_out4.png?raw=True" width="600">

## Documentation

Pylogfile's documentation can be found on [ReadTheDocs](https://pylogfile.readthedocs.io/en/latest/).

## Requirements

- Python >= 3.9
- numpy >= 1.0.0
- h5py >= 3.11.0
- colorama >= 0.4.6
- importlib >= 1.0.0