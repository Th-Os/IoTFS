![](https://github.com/th-os/iotfs/workflows/IoTFS/badge.svg)

# IoT Filesystem

## Abstract

The Internet of Things (IoT) is rapidly increasing in count and covers an increasingamountofapplications.IoTplatformsareusedtoconnectthethingswitheachotherandtheuser.Theyshouldprovidetheuserwithfullandeasyaccess.Butthatisnotthecase.Thisthesissuggestsafilesystemasitisholisticallyaccessiblebyusersanddevelopers.Carried out requirements analysis leads to software developers as potential usergroup. After implementing the system with concepts such as synthetic file system,Everything is a FileandFiles as Directories,itwasevaluatedwithauser‑centeredstu‑dy (n=12) containing comparison with existing system (MQTT) and API usabilityheuristics.First‑Time‑UseofthedevelopedsystemasAPIshowedbetterresults.Explorationis faster with MQTT‑UI, but complex structures are better demonstrated with a filesystem. Future work could enhance the structure and improve visual interactionwith a file manager.

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
