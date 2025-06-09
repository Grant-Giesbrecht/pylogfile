# Lumberjack

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