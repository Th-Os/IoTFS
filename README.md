![](https://github.com/th-os/iotfs/workflows/IoTFS/badge.svg)

# Core Filesystem

This System will open possibilities for:
- including data (e.g. sensor, network, workflow data) to your filesystem.
- writing simple applications that use these data through file operations.

## Prerequisites

- Linux with Fuse3 (https://github.com/libfuse/libfuse)
- Python >=3.5
- specific libraries defined in requirements.txt

## What needs to be done

- Implementing Adapter (Bottom -> Up)
- Implementing Connector (Up -> Bottom)
