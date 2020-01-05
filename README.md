![](https://github.com/th-os/iotfs/workflows/IoTFS/badge.svg)

# IoT Filesystem

## Abstract

The Internet of Things (IoT) is rapidly increasing in count and covers an increasing amount of applications. IoT platforms are used to connect the things with each other and the user. They should provide the user with full and easy access. But that is not the case. This thesis suggests  a file system as it is holistically accessible by users and developers.

Carried out requirements analysis leads to software developers as potential user group. After implementing the system with concepts such as synthetic file system, \textit{Everything is a File} and \textit{Files as Directories}, it was evaluated with a user-centered study (n=12) containing comparison with existing system (MQTT) and API usability heuristics.

First-Time-Use of the developed system as API showed better results. Exploration is faster with MQTT-UI, but complex structures are better demonstrated with a file system. Future work could enhance the structure and improve visual interaction with a file manager.


## Information

This System will open possibilities for:
- including data (e.g. sensor, network, workflow data) to your filesystem.
- writing simple applications that use these data through file operations.

## Prerequisites

- Linux with Fuse3 (https://github.com/libfuse/libfuse)
- Python >=3.5
- specific libraries defined in requirements.txt

## Future Work

- Restructuring of code
- Implementing full structuring functionality
