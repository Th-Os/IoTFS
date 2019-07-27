# Operations

## ls
Procedure:

Working.


## cd

Procedure:

Working.

## cat

Procedure:

Working.

## mkdir

Procedure: GETATTR, LOOKUP, MKDIR

Working.

## mkdir -> ls in dir

Procedure:

Not working: "Too many levels of symbolic links"
- Es darf kein data objekt enthalten sein
- Wird nicht als directory erkannt

Evtl in readdir?

## touch (create empty file)

Procedure: GETATTR, LOOKUP, CREATE

touch: setting time of "$file": No such file or directory -> setattr implementation needs refinement
-> setattr needed current time (attr.st_ctime_ns) -> working

## External Editor (e.g. nano)

Partially not working.

### read

Procedure:

Not Working:

nano file -> "Error reading lock file file.swp: Not enough data read" --> fixed by using entry.st_mode = (stat.S_IFREG | 0o666) entry.st_size = len(node["data"])

nano file -> "Error deleting lock file: Function not implemented" --> implemented unlink

nano file -> "Error writing lock file (swp file): Input/Output Error -->

After nano file, save file -> no file can be found with ls (READDIRPLUS NOT FOUND ERROR -2)

### write

Procedure:

Not Working:
filename.swp can't be opened